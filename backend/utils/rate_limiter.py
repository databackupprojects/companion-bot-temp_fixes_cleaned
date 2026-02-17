"""
Rate limiting utilities - FIXED for SQLAlchemy
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from constants import (
    RATE_LIMIT_MESSAGES_PER_MINUTE,
    RATE_LIMIT_WINDOW_SECONDS,
    DEDUP_WINDOW_SECONDS,
    MESSAGE_LIMITS,
    PROACTIVE_LIMITS,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with SQLAlchemy syntax."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_rate_limit(self, user_id: str) -> Tuple[bool, int]:
        """Check rate limit for user - FIXED."""
        from models.sql_models import Message
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            one_minute_ago = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            
            # Count messages in last minute
            stmt = select(func.count(Message.id)).where(
                Message.user_id == user_uuid,
                Message.created_at >= one_minute_ago,
                Message.role == 'user'
            )
            
            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            
            is_limited = count >= RATE_LIMIT_MESSAGES_PER_MINUTE
            
            if is_limited:
                logger.warning(f"Rate limit hit for user {user_id}: {count}/{RATE_LIMIT_MESSAGES_PER_MINUTE}")
            
            return (is_limited, count)
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return (False, 0)
    
    async def check_daily_limit(self, user_id: str) -> Tuple[bool, int, int]:
        """Check daily message limit - FIXED."""
        from models.sql_models import User
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Get user
            stmt = select(User).where(User.id == user_uuid)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return (False, 0, MESSAGE_LIMITS['free'])
            
            tier = user.tier or 'free'
            limit = MESSAGE_LIMITS.get(tier, 20)
            remaining = max(0, limit - user.messages_today)
            can_send = user.messages_today < limit
            
            if not can_send:
                logger.warning(f"Daily limit hit for user {user_id}: {user.messages_today}/{limit}")
            
            return (can_send, remaining, limit)
            
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return (True, MESSAGE_LIMITS['free'], MESSAGE_LIMITS['free'])
    
    async def check_duplicate(self, user_id: str, message: str) -> bool:
        """Check for duplicate messages - FIXED."""
        from models.sql_models import Message
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            five_seconds_ago = datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)
            
            # Check for recent duplicate messages
            stmt = select(Message.id).where(
                Message.user_id == user_uuid,
                Message.content == message,
                Message.created_at >= five_seconds_ago,
                Message.role == 'user'
            ).limit(1)
            
            result = await self.db.execute(stmt)
            duplicate = result.scalar_one_or_none() is not None
            
            if duplicate:
                logger.debug(f"Duplicate message detected for user {user_id}")
            
            return duplicate
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    async def increment_daily_count(self, user_id: str):
        """Increment daily message count - FIXED."""
        from models.sql_models import User
        from sqlalchemy import update
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            stmt = update(User).where(User.id == user_uuid).values(
                messages_today=User.messages_today + 1
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.debug(f"Incremented daily count for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error incrementing daily count: {e}")
            await self.db.rollback()
    
    def get_limit_warning(self, remaining: int, limit: int) -> str:
        """Get warning message if approaching limit."""
        if remaining <= 3 and remaining > 0:
            return f"\n\n⚠️  You have {remaining} message{'s' if remaining > 1 else ''} left today."
        elif remaining <= 0:
            return f"\n\n🚫 Daily limit reached ({limit} messages). Try again tomorrow or upgrade!"
        return ""
    
    async def check_proactive_limit(self, user_id: str) -> Tuple[bool, int, int]:
        """Check proactive message limit - FIXED."""
        from models.sql_models import User
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Get user
            stmt = select(User).where(User.id == user_uuid)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return (False, 0, PROACTIVE_LIMITS['free'])
            
            tier = user.tier or 'free'
            limit = PROACTIVE_LIMITS.get(tier, 1)
            remaining = max(0, limit - user.proactive_count_today)
            can_send = user.proactive_count_today < limit
            
            return (can_send, remaining, limit)
            
        except Exception as e:
            logger.error(f"Error checking proactive limit: {e}")
            return (False, 0, PROACTIVE_LIMITS['free'])
    
    async def increment_proactive_count(self, user_id: str):
        """Increment proactive message count - FIXED."""
        from models.sql_models import User
        from sqlalchemy import update
        from uuid import UUID
        
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            stmt = update(User).where(User.id == user_uuid).values(
                proactive_count_today=User.proactive_count_today + 1
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.debug(f"Incremented proactive count for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error incrementing proactive count: {e}")
            await self.db.rollback()