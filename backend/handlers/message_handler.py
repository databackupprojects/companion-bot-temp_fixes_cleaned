# handlers/message_handler.py
# Version: 3.1 MVP
# Main entry point for processing user messages

import logging
import random
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import update

from constants import MAX_MESSAGE_LENGTH, FALLBACK_RESPONSES
from handlers.user_helpers import get_or_create_user
from models.sql_models import User
from utils.rate_limiter import RateLimiter
from utils.timezone import get_utc_now
from services.mood_detector import MoodDetector, DistressDetector
from services.preference_extractor import PreferenceExtractor

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Main handler for incoming user messages.
    
    Coordinates all services:
    - Rate limiting
    - Deduplication
    - Boundary processing
    - Mood detection
    - Distress detection
    - Question tracking
    - Response generation
    """
    
    MAX_REGENERATION_ATTEMPTS = 2
    
    def __init__(
        self, 
        db, 
        llm_client, 
        context_builder_class,
        boundary_manager,
        question_tracker,
        analytics,
        message_analyzer=None
    ):
        self.db = db
        self.llm = llm_client
        self.ContextBuilder = context_builder_class
        self.boundary_manager = boundary_manager
        self.question_tracker = question_tracker
        self.analytics = analytics
        self.message_analyzer = message_analyzer
        
        self.rate_limiter = RateLimiter(db)
        self.mood_detector = MoodDetector()
        self.distress_detector = DistressDetector()
        self.preference_extractor = PreferenceExtractor(llm_client)
    
    async def handle(self, telegram_id: int, message_text: str, archetype: Optional[str] = None, source: str = "telegram") -> Optional[str]:
        """Handle incoming user message.
        
        Args:
            telegram_id: Telegram user ID
            message_text: Message content
            archetype: Optional persona archetype (golden_retriever, tsundere, etc.)
            source: Source of message (telegram or web) - default telegram
        """
        start_time = time.time()
        
        try:
            # Sanitize
            message_text = self._sanitize(message_text)
            if not message_text:
                return None
            
            # Ensure transaction is in good state before proceeding
            try:
                await self.db.rollback()
            except:
                pass
            
            # Get or create user
            user = await get_or_create_user(
                self.db,
                telegram_id,
                archetype,
                bot_defaults={
                    "bot_name": "Dot",
                    "bot_gender": "female",
                    "attachment_style": "secure",
                    "flirtiness": "subtle",
                    "toxicity": "healthy",
                },
                log_context="[Message] ",
            )
            user_id = user['id']
            
            # Track message
            await self.analytics.message_sent(user_id, len(message_text))
            
            # TEMPORARY: Skip rate limiting
            # is_limited, count = await self.rate_limiter.check_rate_limit(user_id)
            # if is_limited:
            #     return "hey, slow down a bit! I'm still processing 😅"
            
            # TEMPORARY: Skip daily limit check
            # can_send, remaining, limit = await self.rate_limiter.check_daily_limit(user_id)
            # if not can_send:
            #     await self.analytics.limit_hit(user_id, user.get('tier', 'free'))
            #     return self.rate_limiter.get_limit_warning(0, limit)
            
            # TEMPORARY: Skip dedup check
            # is_duplicate = await self.rate_limiter.check_duplicate(user_id, message_text)
            # if is_duplicate:
            #     return None
            
            # Process message
            response = await self._process(user_id, message_text, user, archetype)
            
            # Track response
            latency_ms = int((time.time() - start_time) * 1000)
            await self.analytics.message_received(user_id, len(response), latency_ms)
            
            # Log conversation to file (for telegram messages)
            try:
                from utils.chat_logger import chat_logger
                bot_archetype = archetype or "unknown"
                username = user.get('username') or user.get('name') or f"telegram_{telegram_id}"
                chat_logger.log_conversation(
                    user_id=user_id,
                    username=username,
                    bot_id=bot_archetype,
                    user_message=message_text,
                    bot_response=response,
                    message_type="reactive",
                    source=source
                )
            except Exception as log_error:
                logger.error(f"Error logging conversation: {log_error}")
            
            return response
            
        except Exception as e:
            # Rollback failed transaction
            try:
                await self.db.rollback()
            except:
                pass
            logger.error(f"[Handler] Error: {e}", exc_info=True)
            return random.choice(FALLBACK_RESPONSES)
    
    async def _process(
        self,
        user_id: str,
        message_text: str,
        user: Dict[str, Any],
        archetype: Optional[str] = None
    ) -> str:
        """Process message with all operations - FIXED for SQLAlchemy."""
        from sqlalchemy import select, update
        from models.sql_models import Message, MoodHistory
        import uuid
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Update user activity
            stmt = update(User).where(User.id == user_uuid).values(
                last_active_at=get_utc_now(),
                is_active_today=True
            )
            await self.db.execute(stmt)
            
            # Increment daily count (using SQLAlchemy model)
            user_obj = await self.db.get(User, user_uuid)
            if user_obj:
                user_obj.messages_today += 1
                await self.db.commit()
            
            # Detect mood
            detected_mood = self.mood_detector.detect(message_text)
            
            # Detect distress
            is_distressed = self.distress_detector.detect(message_text)
            
            # Save user message
            user_message = Message(
                user_id=user_uuid,
                role='user',
                content=message_text,
                detected_mood=detected_mood,
                message_type='reactive'
            )
            
            self.db.add(user_message)
            await self.db.commit()
            await self.db.refresh(user_message)
            
            # Analyze message for meeting/schedule information
            if self.message_analyzer:
                try:
                    from models.sql_models import BotSettings
                    from sqlalchemy import select
                    
                    # Get bot settings for this user and archetype
                    if archetype:
                        stmt = select(BotSettings).where(
                            (BotSettings.user_id == user_obj.id) & 
                            (BotSettings.archetype == archetype)
                        )
                    else:
                        # Get primary or first bot if no archetype specified
                        stmt = select(BotSettings).where(
                            BotSettings.user_id == user_obj.id
                        ).order_by(BotSettings.is_primary.desc()).limit(1)
                    
                    result = await self.db.execute(stmt)
                    bot_settings = result.scalar_one_or_none()
                    
                    if bot_settings:
                        channel = "telegram"  # Default channel for schedule analysis
                        created_schedules = await self.message_analyzer.analyze_for_schedules(
                            user_message,
                            user_obj,
                            bot_settings,
                            channel=channel
                        )
                        if created_schedules:
                            logger.info(f"Found {len(created_schedules)} schedule(s) in user message")
                except Exception as e:
                    logger.error(f"Error analyzing message for schedules: {e}", exc_info=True)
            
            # Extract and save DND preferences from message
            try:
                dnd_prefs = await self.preference_extractor.extract_dnd_preferences(
                    message_text,
                    user_timezone=user_obj.timezone if user_obj else "UTC"
                )
                if dnd_prefs:
                    await self._update_dnd_preferences(user_uuid, dnd_prefs)
                    logger.info(f"✓ Updated DND preferences for user {user_id}: {dnd_prefs}")
                
                # Check for proactive preference changes
                proactive_pref = await self.preference_extractor.extract_proactive_preference(message_text)
                if proactive_pref is not None:
                    await self._update_proactive_preference(user_uuid, proactive_pref)
                    logger.info(f"✓ Updated proactive preference for user {user_id}: {proactive_pref}")
            except Exception as e:
                logger.error(f"Error extracting preferences: {e}", exc_info=True)
            
            # Save mood to history
            mood_entry = MoodHistory(
                user_id=user_uuid,
                mood=detected_mood
            )
            
            self.db.add(mood_entry)
            await self.db.commit()
            
            # Process boundaries
            boundary_result = await self.boundary_manager.process_message(user_id, message_text)
            
            if boundary_result:
                await self.analytics.boundary_set(
                    user_id, 
                    boundary_result.type, 
                    boundary_result.value
                )
            
            # Mark pending questions as answered
            await self.question_tracker.on_user_message(user_id)
            
            # Build context with archetype
            context_builder = self.ContextBuilder(self.db, user_id, archetype)
            context = await context_builder.build(
                message_type="reactive",
                user_message=message_text
            )
            
            # Add boundary hint if detected
            if boundary_result:
                context["system_hint"] = boundary_result.hint
            
            # Add distress flag
            if is_distressed:
                context["distress_detected"] = True
                context["system_hint"] = "[SAFETY: User may be in distress. Drop persona and be genuinely supportive.]"
            
            # Generate response
            response = await self._generate_safe(user_id, context)
            
            # Save bot message
            bot_msg = Message(
                user_id=user_uuid,
                role='bot',
                content=response,
                message_type='reactive'
            )
            
            self.db.add(bot_msg)
            await self.db.commit()
            await self.db.refresh(bot_msg)
            
            # Track questions in response
            await self.question_tracker.on_bot_message(user_id, response, bot_msg.id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in _process: {e}", exc_info=True)
            raise
    
    async def _generate_safe(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate response with error handling and boundary checking."""
        
        logger.info(f"Generating response for user {user_id}")
        
        # Log context summary for debugging
        logger.debug(f"📋 Context summary:")
        logger.debug(f"  - Archetype: {context.get('archetype', 'unknown')}")
        logger.debug(f"  - Message type: {context.get('message_type', 'unknown')}")
        logger.debug(f"  - User message: {context.get('user_message', '')[:50]}...")
        logger.debug(f"  - Recent conversation: {'Yes' if context.get('recent_conversation') else 'No'}")
        
        for attempt in range(self.MAX_REGENERATION_ATTEMPTS + 1):
            try:
                logger.debug(f"🤖 Attempt {attempt + 1} to generate response...")
                
                # Call LLM
                response = await self.llm.generate(context)
                
                logger.debug(f"📤 LLM returned: {response[:100] if response else 'EMPTY'}")
                
                if not response:
                    logger.warning("❌ Empty response from LLM")
                    continue
                
                # Check if response is a fallback
                is_fallback = response in FALLBACK_RESPONSES or any(
                    fb in response.lower() for fb in [
                        'sorry', 'oops', 'lost my train', 'brain glitched',
                        'zoned out', 'try again', 'say that again'
                    ]
                )
                
                if is_fallback:
                    logger.warning(f"⚠️  LLM returned fallback response: {response[:50]}...")
                    # Don't retry if it's a fallback, just return it
                    return response
                
                # Validate response isn't malformed
                if not self._is_valid_response(response):
                    logger.warning(f"⚠️  Invalid response format: {response[:50]}...")
                    continue
                
                # Check for boundary violations
                violates, violated = await self.boundary_manager.check_message_violates(
                    user_id, response
                )
                
                if violates:
                    logger.warning(f"⚠️  Boundary violation detected: {violated}")
                    # Add regeneration hint and try again
                    if attempt < self.MAX_REGENERATION_ATTEMPTS:
                        # Update context with boundary hint and regenerate
                        context["system_hint"] = (
                            f"[CRITICAL BOUNDARY VIOLATION: You mentioned '{violated}'. "
                            f"This violates the user's boundary. "
                            f"Respond to them WITHOUT mentioning this topic/behavior. "
                            f"Stay in character but avoid this completely.]"
                        )
                        logger.debug(f"Regenerating due to boundary violation: {violated}")
                        continue
                    else:
                        logger.warning(f"❌ Max regeneration attempts reached after {violated} violation")
                        return "Anyway, what else is on your mind?"
                
                logger.info(f"Response generated successfully: {response[:50]}...")
                return response
                
            except Exception as e:
                logger.error(f"❌ Error in _generate_safe: {e}", exc_info=True)
                if attempt == self.MAX_REGENERATION_ATTEMPTS:
                    logger.error("Max attempts reached, using fallback")
                    return random.choice(FALLBACK_RESPONSES)
        
        logger.error("All generation attempts failed")
        return random.choice(FALLBACK_RESPONSES)
    
    def _is_valid_response(self, response: str) -> bool:
        """Check response isn't malformed."""
        if not response or len(response) < 2:
            return False
        if len(response) > 2000:
            return False
        if response.count('[') > response.count(']') + 2:
            return False
        return True
    
    def _sanitize(self, message: str) -> str:
        """Sanitize message input."""
        if not message:
            return ""
        
        message = message.replace('\x00', '').strip()
        
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH]
        
        return message
    
    async def _update_dnd_preferences(self, user_id: uuid.UUID, dnd_prefs: Dict[str, Any]) -> None:
        """
        Update user's DND (Do Not Disturb) preferences in database.
        
        Args:
            user_id: User's UUID
            dnd_prefs: Dictionary with dnd_start_hour, dnd_end_hour, confidence, reasoning
        """
        from sqlalchemy import select
        from models.sql_models import GreetingPreference
        
        try:
            # Get or create greeting preferences
            stmt = select(GreetingPreference).where(GreetingPreference.user_id == user_id)
            result = await self.db.execute(stmt)
            greeting_pref = result.scalar_one_or_none()
            
            if not greeting_pref:
                # Create new preference record
                greeting_pref = GreetingPreference(user_id=user_id)
                self.db.add(greeting_pref)
            
            # Update DND hours
            if dnd_prefs.get("dnd_start_hour") is not None:
                greeting_pref.dnd_start_hour = dnd_prefs["dnd_start_hour"]
            
            if dnd_prefs.get("dnd_end_hour") is not None:
                greeting_pref.dnd_end_hour = dnd_prefs["dnd_end_hour"]
            
            greeting_pref.updated_at = get_utc_now()
            
            await self.db.commit()
            
            logger.info(
                f"✓ DND preferences updated: user={user_id}, "
                f"start={dnd_prefs.get('dnd_start_hour')}, end={dnd_prefs.get('dnd_end_hour')}, "
                f"confidence={dnd_prefs.get('confidence')}"
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating DND preferences: {e}", exc_info=True)
            raise
    
    async def _update_proactive_preference(self, user_id: uuid.UUID, enable: bool) -> None:
        """
        Update user's proactive message preference.
        
        Args:
            user_id: User's UUID
            enable: True to enable proactive messages, False to disable
        """
        from sqlalchemy import select
        from models.sql_models import GreetingPreference
        
        try:
            # Get or create greeting preferences
            stmt = select(GreetingPreference).where(GreetingPreference.user_id == user_id)
            result = await self.db.execute(stmt)
            greeting_pref = result.scalar_one_or_none()
            
            if not greeting_pref:
                # Create new preference record
                greeting_pref = GreetingPreference(user_id=user_id)
                self.db.add(greeting_pref)
            
            greeting_pref.prefer_proactive = enable
            greeting_pref.updated_at = get_utc_now()
            
            await self.db.commit()
            
            logger.info(f"✓ Proactive preference updated: user={user_id}, enabled={enable}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating proactive preference: {e}", exc_info=True)
            raise
