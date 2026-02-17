# backend/services/analytics.py
"""Simplified analytics tracking service"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from uuid import UUID

from models.sql_models import AnalyticsEvent, User, Message

logger = logging.getLogger(__name__)


class Analytics:
    """Analytics event tracking."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track(self, event: str, user_id: Optional[str] = None, properties: Dict[str, Any] = None):
        """Track an analytics event."""
        try:
            analytics_event = AnalyticsEvent(
                user_id=UUID(user_id) if user_id else None,
                event_name=event,
                properties=properties or {}
            )
            self.db.add(analytics_event)
            await self.db.commit()
            logger.debug(f"Analytics: {event} | user={user_id}")
        except Exception as e:
            logger.warning(f"Failed to track {event}: {e}")
            await self.db.rollback()
    
    async def get_dashboard_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get basic dashboard statistics."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get counts in parallel
        total_users = (await self.db.execute(select(func.count(User.id)))).scalar() or 0
        active_today = (await self.db.execute(
            select(func.count(User.id)).where(User.last_active_at >= today_start)
        )).scalar() or 0
        new_today = (await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )).scalar() or 0
        total_messages = (await self.db.execute(select(func.count(Message.id)))).scalar() or 0
        messages_today = (await self.db.execute(
            select(func.count(Message.id)).where(Message.created_at >= today_start)
        )).scalar() or 0
        
        return {
            "total_users": total_users,
            "active_users_today": active_today,
            "new_users_today": new_today,
            "total_messages": total_messages,
            "messages_today": messages_today,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def get_user_activity(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        message_count = (await self.db.execute(
            select(func.count(Message.id)).where(
                Message.user_id == user_id, Message.created_at >= start_date
            )
        )).scalar() or 0
        
        active_days = (await self.db.execute(
            select(func.count(func.distinct(func.date(Message.created_at)))).where(
                Message.user_id == user_id, Message.created_at >= start_date
            )
        )).scalar() or 0
        
        recent_messages = (await self.db.execute(
            select(Message.role, Message.content, Message.created_at)
            .where(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
            .limit(10)
        )).fetchall()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "message_count": message_count,
            "active_days": active_days,
            "recent_messages": [
                {"role": r[0], "content": r[1][:100], "created_at": r[2].isoformat()}
                for r in recent_messages
            ]
        }