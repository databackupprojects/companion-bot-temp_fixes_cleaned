# backend/jobs/memory_summarizer.py
# Version: 3.1 MVP - Fixed for SQLAlchemy AsyncSession
# Weekly job to extract facts from old conversations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from constants import MEMORY_SUMMARY_THRESHOLD_DAYS, MEMORY_MAX_MESSAGES_TO_SUMMARIZE

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """
    Weekly job to summarize old conversations into memory facts.
    
    Process:
    1. Find users with unsummarized messages > 7 days old
    2. Batch messages and send to LLM for fact extraction
    3. Save facts to user_memory table
    4. Mark messages as summarized
    """
    
    RUN_INTERVAL_SECONDS = 3600 * 6  # 6 hours
    BATCH_SIZE = 100  # Users per cycle
    MIN_MESSAGES_TO_SUMMARIZE = 10
    
    def __init__(self, db: AsyncSession, llm_client):
        self.db = db
        self.llm = llm_client
        self.running = False
    
    async def run(self):
        """Main loop."""
        self.running = True
        
        logger.info("[MemorySummarizer] Starting memory summarization job")
        
        while self.running:
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"[MemorySummarizer] Cycle error: {e}", exc_info=True)
            
            await asyncio.sleep(self.RUN_INTERVAL_SECONDS)
    
    async def _process_cycle(self):
        """Process one summarization cycle."""
        
        users = await self._get_users_with_old_messages()
        
        if users:
            logger.info(f"[MemorySummarizer] Processing {len(users)} users")
        
        for user_id in users:
            try:
                await self._summarize_user(user_id)
            except Exception as e:
                logger.error(f"[MemorySummarizer] Error for {user_id}: {e}")
    
    async def _get_users_with_old_messages(self) -> List[str]:
        """Get users who have unsummarized messages older than threshold."""
        from models.sql_models import Message
        
        threshold = datetime.utcnow() - timedelta(days=MEMORY_SUMMARY_THRESHOLD_DAYS)
        
        result = await self.db.execute(
            select(Message.user_id.distinct())
            .where(
                Message.created_at < threshold,
                Message.summarized == False,
                Message.role == 'user',
                Message.deleted_at.is_(None)
            )
            .limit(self.BATCH_SIZE)
        )
        users = result.scalars().all()
        
        return list(users)
    
    async def _summarize_user(self, user_id: str):
        """Summarize old messages for a single user."""
        from models.sql_models import Message, UserMemory
        
        threshold = datetime.utcnow() - timedelta(days=MEMORY_SUMMARY_THRESHOLD_DAYS)
        
        # Get old unsummarized messages
        result = await self.db.execute(
            select(Message.role, Message.content, Message.created_at)
            .where(
                Message.user_id == user_id,
                Message.created_at < threshold,
                Message.summarized == False,
                Message.deleted_at.is_(None)
            )
            .order_by(Message.created_at.asc())
            .limit(MEMORY_MAX_MESSAGES_TO_SUMMARIZE)
        )
        messages = result.fetchall()
        
        if len(messages) < self.MIN_MESSAGES_TO_SUMMARIZE:
            return
        
        # Format messages for LLM
        formatted = self._format_messages(messages)
        
        # Extract facts
        facts = await self._extract_facts(formatted)
        
        if not facts:
            # Still mark as summarized to avoid re-processing
            await self._mark_summarized(user_id, threshold)
            return
        
        # Save facts
        saved = 0
        for fact in facts:
            try:
                # Check if fact already exists
                existing = await self.db.execute(
                    select(UserMemory.id)
                    .where(
                        UserMemory.user_id == user_id,
                        UserMemory.fact == fact.get('fact')
                    )
                )
                
                if not existing.scalar_one_or_none():
                    memory = UserMemory(
                        user_id=user_id,
                        category=fact.get('category', 'general'),
                        fact=fact.get('fact'),
                        importance=fact.get('importance', 1)
                    )
                    self.db.add(memory)
                    saved += 1
            except Exception as e:
                logger.warning(f"[MemorySummarizer] Failed to save fact: {e}")
        
        # Mark messages as summarized
        await self._mark_summarized(user_id, threshold)
        
        await self.db.commit()
        
        logger.info(f"[MemorySummarizer] User {user_id}: {saved} facts from {len(messages)} messages")
    
    def _format_messages(self, messages: List) -> str:
        """Format messages for LLM input."""
        
        lines = []
        for msg in messages:
            role = "User" if msg.role == 'user' else "Bot"
            date = msg.created_at.strftime('%Y-%m-%d') if hasattr(msg.created_at, 'strftime') else str(msg.created_at)
            content = msg.content[:300] if msg.content else ""  # Truncate long messages
            lines.append(f"[{date}] {role}: {content}")
        
        return "\n".join(lines)
    
    async def _extract_facts(self, conversation: str) -> List[Dict]:
        """Use LLM to extract facts from conversation."""
        
        prompt = f"""Extract 3-7 important facts about this user from their conversation history.

Focus on:
- Preferences (likes, dislikes, interests)
- Life events (job changes, relationships, milestones)  
- Recurring topics they bring up
- Emotional patterns
- Personal details (location, work, relationships)

Return ONLY a JSON array, no other text:
[
  {{"category": "preferences", "fact": "...", "importance": 1-5}},
  {{"category": "life_events", "fact": "...", "importance": 1-5}}
]

Categories: preferences, life_events, relationships, work, interests, emotional_patterns, personal_details

Importance scale:
1 = Minor detail
3 = Notable information
5 = Core identity/major event

Conversation:
{conversation}

JSON array only:"""

        try:
            response = await self.llm.extract_facts_from_conversation(conversation)
            
            if not response:
                # Fall back to direct generation
                response = await self.llm.generate({"prompt": prompt})
            
            # Parse JSON from response
            if isinstance(response, str):
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('```')[1]
                    if response.startswith('json'):
                        response = response[4:]
                
                facts = json.loads(response)
            else:
                facts = response
            
            # Validate structure
            validated = []
            for fact in facts:
                if isinstance(fact, dict) and 'fact' in fact:
                    validated.append({
                        'category': fact.get('category', 'general'),
                        'fact': str(fact['fact'])[:500],
                        'importance': min(5, max(1, int(fact.get('importance', 1))))
                    })
            
            return validated
            
        except json.JSONDecodeError as e:
            logger.warning(f"[MemorySummarizer] JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"[MemorySummarizer] Extraction error: {e}")
            return []
    
    async def _mark_summarized(self, user_id: str, threshold: datetime):
        """Mark old messages as summarized."""
        from models.sql_models import Message
        
        await self.db.execute(
            update(Message)
            .where(
                Message.user_id == user_id,
                Message.created_at < threshold,
                Message.summarized == False,
                Message.deleted_at.is_(None)
            )
            .values(summarized=True)
        )
    
    def stop(self):
        """Stop the job."""
        self.running = False


class MemoryManager:
    """Utility class for memory operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_memory(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user's memory facts, sorted by importance."""
        from models.sql_models import UserMemory
        
        result = await self.db.execute(
            select(UserMemory.category, UserMemory.fact, UserMemory.importance, UserMemory.created_at)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.importance.desc(), UserMemory.created_at.desc())
            .limit(limit)
        )
        
        memories = result.fetchall()
        return [
            {
                'category': mem.category,
                'fact': mem.fact,
                'importance': mem.importance,
                'created_at': mem.created_at
            }
            for mem in memories
        ]
    
    async def add_memory(
        self, 
        user_id: str, 
        fact: str, 
        category: str = 'general',
        importance: int = 1
    ) -> bool:
        """Manually add a memory fact."""
        from models.sql_models import UserMemory
        
        try:
            # Check if exists
            existing = await self.db.execute(
                select(UserMemory.id)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.fact == fact
                )
            )
            
            if existing.scalar_one_or_none():
                # Update importance if higher
                await self.db.execute(
                    update(UserMemory)
                    .where(
                        UserMemory.user_id == user_id,
                        UserMemory.fact == fact
                    )
                    .values(importance=func.greatest(UserMemory.importance, importance))
                )
            else:
                memory = UserMemory(
                    user_id=user_id,
                    category=category,
                    fact=fact,
                    importance=importance
                )
                self.db.add(memory)
            
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"[MemoryManager] Add failed: {e}")
            await self.db.rollback()
            return False
    
    async def forget_topic(self, user_id: str, topic: str) -> int:
        """Remove memories containing a topic."""
        from models.sql_models import UserMemory
        from sqlalchemy import delete
        
        result = await self.db.execute(
            delete(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.fact.ilike(f"%{topic}%")
            )
        )
        
        await self.db.commit()
        return result.rowcount
    
    async def get_memory_stats(self, user_id: str) -> Dict:
        """Get memory statistics for a user."""
        from models.sql_models import UserMemory
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(
                func.count(UserMemory.id).label('total'),
                func.count(UserMemory.category.distinct()).label('categories'),
                func.avg(UserMemory.importance).label('avg_importance')
            )
            .where(UserMemory.user_id == user_id)
        )
        
        stats = result.fetchone()
        return {
            'total': stats.total or 0,
            'categories': stats.categories or 0,
            'avg_importance': float(stats.avg_importance or 0)
        }