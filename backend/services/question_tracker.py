"""
Question tracking service - FIXED for SQLAlchemy
"""
import logging
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class QuestionTracker:
    """Tracks questions asked by the bot."""
    
    QUESTION_PATTERNS = [
        r"(\?[^.!?]*$)",  # Ends with question mark
        r"(what's|what is|how do|how to|why do|why does|where is|when is)",
        r"(are you|do you|can you|will you|would you|have you)",
        r"(right\?|correct\?|yes\?|no\?)",
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def on_bot_message(self, user_id: str, message: str, message_id: str):
        """Analyze bot message for questions - FIXED."""
        from models.sql_models import Message
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            msg_uuid = UUID(message_id) if isinstance(message_id, str) else message_id
            
            # Check if message contains a question
            is_question = self._contains_question(message)
            
            # Extract topic if it's a question
            topic = None
            if is_question:
                topic = self._extract_topic(message)
            
            # Update the message
            stmt = update(Message).where(
                Message.id == msg_uuid,
                Message.user_id == user_uuid
            ).values(
                is_question=is_question,
                question_topic=topic,
                question_answered=False
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            if is_question:
                logger.debug(f"Question tracked: {topic or 'general'} for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error tracking bot question: {e}")
            await self.db.rollback()
    
    async def on_user_message(self, user_id: str):
        """Mark pending questions as answered - FIXED."""
        from models.sql_models import Message
        from sqlalchemy import update
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Mark all pending questions as answered
            stmt = update(Message).where(
                Message.user_id == user_uuid,
                Message.role == 'bot',
                Message.is_question == True,
                Message.question_answered == False
            ).values(question_answered=True)
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.debug(f"Marked questions as answered for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error marking questions answered: {e}")
            await self.db.rollback()
    
    async def get_pending_questions(self, user_id: str) -> List[str]:
        """Get pending questions - FIXED."""
        from models.sql_models import Message
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            stmt = select(Message.question_topic).where(
                Message.user_id == user_uuid,
                Message.role == 'bot',
                Message.is_question == True,
                Message.question_answered == False
            ).order_by(Message.created_at.desc()).limit(5)
            
            result = await self.db.execute(stmt)
            topics = [row[0] for row in result.fetchall() if row[0]]
            
            return topics
            
        except Exception as e:
            logger.error(f"Error getting pending questions: {e}")
            return []
    
    def _contains_question(self, message: str) -> bool:
        """Check if message contains a question."""
        if not message:
            return False
        
        # Check for question mark
        if '?' in message:
            return True
        
        # Check for question patterns
        message_lower = message.lower()
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    def _extract_topic(self, message: str) -> Optional[str]:
        """Extract topic from question."""
        if not message:
            return None
        
        # Simple topic extraction
        if '?' in message:
            # Take first 5 words before question mark
            parts = message.split('?')[0].split()
            if len(parts) > 5:
                topic = ' '.join(parts[-5:])
            else:
                topic = ' '.join(parts)
        else:
            # Take first 5 words
            words = message.split()[:5]
            topic = ' '.join(words)
        
        # Clean up
        topic = topic.strip().lower()
        if len(topic) > 50:
            topic = topic[:50] + "..."
        
        return topic if topic else "general"
    
    async def has_pending_questions(self, user_id: str) -> bool:
        """Check if user has pending questions - FIXED."""
        from models.sql_models import Message
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            stmt = select(Message.id).where(
                Message.user_id == user_uuid,
                Message.role == 'bot',
                Message.is_question == True,
                Message.question_answered == False
            ).limit(1)
            
            result = await self.db.execute(stmt)
            pending = result.scalar_one_or_none() is not None
            
            return pending
            
        except Exception as e:
            logger.error(f"Error checking pending questions: {e}")
            return False
        
class QuestionDetector:
    """Detects if a message is a question."""
    
    QUESTION_PATTERNS = [
        r"(\?[^.!?]*$)",  # Ends with question mark
        r"(what's|what is|how do|how to|why do|why does|where is|when is)",
        r"(are you|do you|can you|will you|would you|have you)",
        r"(right\?|correct\?|yes\?|no\?)",
    ]
    
    @classmethod
    def is_question(cls, message: str) -> bool:
        """Determine if the message is a question."""
        if not message:
            return False
        
        # Check for question mark
        if '?' in message:
            return True
        
        # Check for question patterns
        message_lower = message.lower()
        for pattern in cls.QUESTION_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        
        return False