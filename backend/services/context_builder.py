# backend/services/context_builder.py
"""
Context builder for LLM requests
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from constants import ARCHETYPE_DEFAULTS, ARCHETYPE_INSTRUCTIONS
from utils.tone_generator import generate_tone_summary
from utils.timezone import get_utc_now, to_user_timezone, format_for_user
from models.sql_models import (
    User, BotSettings, Message, UserBoundary, 
    UserMemory, MoodHistory, ProactiveLog
)

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds complete context for LLM requests.
    """
    
    def __init__(self, db: AsyncSession, user_id: str, archetype: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.archetype = archetype or 'golden_retriever'
    
    async def build(
        self, 
        message_type: str,  # "reactive" or "proactive"
        user_message: str = "",
        attachment_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build complete context for LLM.
        """
        
        # Load all data in parallel for efficiency
        user, settings = await self._load_user_and_settings()
        
        if not user or not settings:
            logger.error(f"User {self.user_id} or settings not found")
            return self._get_default_context(message_type, user_message)
        
        # Merge settings with archetype defaults
        effective = self._merge_with_defaults(settings)
        
        # Load additional data
        recent_messages = await self._get_recent_messages()
        recent_bot_messages = await self._get_recent_bot_messages()
        pending_questions = await self._get_pending_questions()
        boundaries = await self._get_boundaries()
        mood_history = await self._get_mood_history()
        memory_context = await self._get_memory_context()
        
        # Calculate time context
        user_tz = pytz.timezone(user.timezone or 'UTC')
        user_local_time = datetime.now(user_tz)
        time_of_day = self._get_time_of_day(user_local_time.hour)
        
        # Get archetype instructions
        archetype = effective.get('archetype', 'golden_retriever')
        archetype_instructions = ARCHETYPE_INSTRUCTIONS.get(
            archetype, "Be a genuine friend with your defined personality."
        )
        
        # Get or generate tone_summary
        tone_summary = settings.tone_summary
        if not tone_summary:
            tone_summary = generate_tone_summary(effective)
        
        # Get recent mood
        recent_mood_str = mood_history[0] if mood_history else "neutral"
        
        # Build context dictionary
        context = {
            # Message info
            'message_type': message_type,
            'user_message': user_message,
            
            # Identity
            'bot_name': effective.get('bot_name', 'Dot'),
            'bot_gender': effective.get('bot_gender', 'female'),
            'archetype': archetype,
            'archetype_instructions': archetype_instructions,
            
            # Core traits
            'attachment_style': effective.get('attachment_style', 'secure'),
            'flirtiness': effective.get('flirtiness', 'subtle'),
            'toxicity': effective.get('toxicity', 'healthy'),
            'tone_summary': tone_summary,
            
            # Advanced settings
            'temperament': effective.get('temperament', 'warm'),
            'humor_type': effective.get('humor_type', 'witty'),
            'confidence': effective.get('confidence', 'confident'),
            'power_dynamic': effective.get('power_dynamic', 'equal'),
            'emoji_usage': effective.get('emoji_usage', 'moderate'),
            'message_length': effective.get('message_length', 'medium'),
            'typing_style': effective.get('typing_style', 'casual'),
            
            # User context - use 'name' from quiz, fallback to username
            'user_name': user.name or user.username or 'friend',
            'user_local_time': user_local_time.strftime('%I:%M %p'),
            'time_of_day': time_of_day,
            'recent_mood': recent_mood_str,
            
            # Conversation context
            'recent_conversation': self._format_messages(recent_messages),
            'recent_bot_messages': self._format_bot_messages(recent_bot_messages),
            'pending_questions': pending_questions,
            'user_boundaries': boundaries,
            'memory_context': memory_context,
            
            # Proactive context
            'proactive_count_today': user.proactive_count_today or 0,
        }
        
        # Add attachment hint for proactive
        if attachment_hint:
            context['attachment_hint'] = attachment_hint
        
        # Get last proactive time
        last_proactive = await self._get_last_proactive()
        context['last_proactive_time'] = (
            last_proactive.isoformat() if last_proactive else "never"
        )
        
        logger.debug(f"Built context for user {self.user_id}, type: {message_type}")
        return context
    
    async def _load_user_and_settings(self):
        """Load user and settings concurrently - FIXED."""
        from sqlalchemy import select
        
        user_stmt = select(User).where(User.id == self.user_id)
        settings_stmt = select(BotSettings).where(
            BotSettings.user_id == self.user_id,
            BotSettings.archetype == self.archetype
        )
        
        user_result = await self.db.execute(user_stmt)
        settings_result = await self.db.execute(settings_stmt)
        
        user = user_result.scalar_one_or_none()
        settings = settings_result.scalar_one_or_none()
        
        return user, settings
    
    def _merge_with_defaults(self, settings: BotSettings) -> Dict[str, Any]:
        """Merge user settings with archetype defaults."""
        archetype = settings.archetype or 'golden_retriever'
        defaults = ARCHETYPE_DEFAULTS.get(archetype, {})
        
        # Start with defaults
        merged = {**defaults}
        
        # Apply JSONB advanced_settings
        if settings.advanced_settings:
            merged.update(settings.advanced_settings)
        
        # Apply core settings (override everything)
        core_fields = {
            'bot_name': settings.bot_name,
            'bot_gender': settings.bot_gender,
            'archetype': settings.archetype,
            'attachment_style': settings.attachment_style,
            'flirtiness': settings.flirtiness,
            'toxicity': settings.toxicity,
            'tone_summary': settings.tone_summary,
        }
        
        for key, value in core_fields.items():
            if value:
                merged[key] = value
        
        return merged
    
    async def _get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent conversation messages."""
        result = await self.db.execute(
            select(Message)
            .where(Message.user_id == self.user_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))  # Return in chronological order
    
    async def _get_recent_bot_messages(self, limit: int = 5) -> List[str]:
        """Get last N bot messages for anti-repetition."""
        result = await self.db.execute(
            select(Message.content)
            .where(
                Message.user_id == self.user_id,
                Message.role == 'bot'
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return [row[0] for row in result.fetchall()]
    
    async def _get_pending_questions(self) -> List[str]:
        """Get unanswered questions."""
        result = await self.db.execute(
            select(Message.question_topic)
            .where(
                Message.user_id == self.user_id,
                Message.role == 'bot',
                Message.is_question == True,
                Message.question_answered == False
            )
            .order_by(desc(Message.created_at))
            .limit(5)
        )
        topics = [row[0] for row in result.fetchall() if row[0]]
        return topics
    
    async def _get_boundaries(self) -> List[str]:
        """Get active user boundaries."""
        result = await self.db.execute(
            select(UserBoundary.boundary_type, UserBoundary.boundary_value)
            .where(
                UserBoundary.user_id == self.user_id,
                UserBoundary.active == True
            )
        )
        return [f"{row[0]}: {row[1]}" for row in result.fetchall()]
    
    async def _get_mood_history(self, limit: int = 5) -> List[str]:
        """Get recent mood history."""
        result = await self.db.execute(
            select(MoodHistory.mood)
            .where(MoodHistory.user_id == self.user_id)
            .order_by(desc(MoodHistory.detected_at))
            .limit(limit)
        )
        return [row[0] for row in result.fetchall()]
    
    async def _get_memory_context(self) -> str:
        """Get long-term memory facts."""
        result = await self.db.execute(
            select(UserMemory.category, UserMemory.fact)
            .where(UserMemory.user_id == self.user_id)
            .order_by(desc(UserMemory.importance), desc(UserMemory.created_at))
            .limit(15)
        )
        
        memories = result.fetchall()
        if not memories:
            return "No long-term memories yet."
        
        # Group by category
        by_category = {}
        for category, fact in memories:
            cat = category or 'general'
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(fact)
        
        # Format
        lines = []
        for cat, facts in by_category.items():
            lines.append(f"[{cat}]")
            for fact in facts[:4]:  # Limit to 4 facts per category
                lines.append(f"- {fact}")
        
        return "\n".join(lines)
    
    async def _get_last_proactive(self) -> Optional[datetime]:
        """Get last proactive message time."""
        result = await self.db.execute(
            select(ProactiveLog.sent_at)
            .where(ProactiveLog.user_id == self.user_id)
            .order_by(desc(ProactiveLog.sent_at))
            .limit(1)
        )
        row = result.fetchone()
        return row[0] if row else None
    
    def _format_messages(self, messages: List[Message]) -> str:
        """Format messages for context."""
        if not messages:
            return "No recent messages."
        
        lines = []
        for msg in messages:
            role = "User" if msg.role == 'user' else "You"
            content = msg.content[:200]  # Truncate long messages
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _format_bot_messages(self, messages: List[str]) -> str:
        """Format bot messages for anti-repetition check."""
        if not messages:
            return "None"
        
        return "\n".join([f"- {msg[:100]}" for msg in messages])
    
    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day category."""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "late_night"
    
    def _get_default_context(self, message_type: str, user_message: str) -> Dict[str, Any]:
        """Get default context when user/settings not found."""
        return {
            'message_type': message_type,
            'user_message': user_message,
            'bot_name': 'Dot',
            'bot_gender': 'female',
            'archetype': 'golden_retriever',
            'archetype_instructions': ARCHETYPE_INSTRUCTIONS.get('golden_retriever', ''),
            'attachment_style': 'secure',
            'flirtiness': 'subtle',
            'toxicity': 'healthy',
            'tone_summary': 'a friendly companion',
            'temperament': 'warm',
            'humor_type': 'silly',
            'confidence': 'humble',
            'power_dynamic': 'you_dominate',
            'emoji_usage': 'heavy',
            'message_length': 'medium',
            'typing_style': 'casual',
            'user_name': 'friend',
            'user_local_time': format_for_user(get_utc_now(), user.timezone or 'UTC', '%I:%M %p'),
            'time_of_day': self._get_time_of_day(to_user_timezone(get_utc_now(), user.timezone or 'UTC').hour),
            'recent_mood': 'neutral',
            'recent_conversation': 'No recent messages.',
            'recent_bot_messages': 'None',
            'pending_questions': [],
            'user_boundaries': [],
            'memory_context': 'No long-term memories yet.',
            'proactive_count_today': 0,
            'last_proactive_time': 'never',
        }