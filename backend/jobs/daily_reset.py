# backend/jobs/daily_reset.py
# Version: 3.1 MVP - Fixed for SQLAlchemy AsyncSession
# Per-user timezone daily reset job

import asyncio
import logging
from datetime import datetime, date
from typing import List
import pytz
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DailyResetJob:
    """
    Per-user timezone daily reset job.
    
    Resets:
    - messages_today
    - proactive_count_today
    - is_active_today
    
    Runs continuously, checking each user's local midnight.
    """
    
    CHECK_INTERVAL_SECONDS = 300  # 5 minutes
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.running = False
    
    async def run(self):
        """Main loop."""
        self.running = True
        
        logger.info("[DailyReset] Starting per-timezone reset job")
        
        while self.running:
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"[DailyReset] Cycle error: {e}", exc_info=True)
            
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
    
    async def _process_cycle(self):
        """Process one reset cycle."""
        
        # Get users who need reset
        users = await self._get_users_needing_reset()
        
        if users:
            logger.info(f"[DailyReset] Resetting {len(users)} users")
        
        for user in users:
            try:
                await self._reset_user(user['id'], user['timezone'])
            except Exception as e:
                logger.error(f"[DailyReset] Error resetting user {user.get('id')}: {e}")
    
    async def _get_users_needing_reset(self) -> List[dict]:
        """
        Get users whose local date has changed since last reset.
        
        Logic:
        - last_daily_reset is the DATE (not datetime) of last reset
        - Compare to current DATE in user's timezone
        - If different, user needs reset
        """
        from sqlalchemy import select, func
        
        # Get all distinct timezones we have
        from models.sql_models import User
        timezones_result = await self.db.execute(
            select(func.coalesce(User.timezone, 'UTC').distinct().label('tz'))
        )
        timezones = timezones_result.scalars().all()
        
        users_to_reset = []
        
        for tz_str in timezones:
            try:
                tz = pytz.timezone(tz_str)
                local_date = datetime.now(tz).date()
            except Exception:
                local_date = datetime.utcnow().date()
            
            # Find users in this timezone whose last_daily_reset < local_date
            users_result = await self.db.execute(
                select(User.id, User.timezone)
                .where(
                    func.coalesce(User.timezone, 'UTC') == tz_str,
                    (User.last_daily_reset.is_(None) | (User.last_daily_reset < local_date))
                )
            )
            users = users_result.fetchall()
            
            for user in users:
                users_to_reset.append({
                    'id': user.id,
                    'timezone': user.timezone
                })
        
        return users_to_reset
    
    async def _reset_user(self, user_id: str, timezone: str):
        """Reset counters for a single user."""
        
        try:
            tz = pytz.timezone(timezone or 'UTC')
            local_date = datetime.now(tz).date()
        except Exception:
            local_date = datetime.utcnow().date()
        
        from models.sql_models import User
        
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                messages_today=0,
                proactive_count_today=0,
                is_active_today=False,
                last_daily_reset=local_date
            )
        )
        await self.db.commit()
        
        logger.debug(f"[DailyReset] Reset user {user_id} for {local_date}")
    
    def stop(self):
        """Stop the job."""
        self.running = False


class DataCleanupJob:
    """
    Periodic data cleanup job.
    
    Cleans:
    - Old mood history (30 days)
    - Old proactive logs (30 days)
    - Old analytics events (90 days)
    - Expired quiz configs (24 hours)
    """
    
    CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
    
    MOOD_RETENTION_DAYS = 30
    PROACTIVE_LOG_RETENTION_DAYS = 30
    ANALYTICS_RETENTION_DAYS = 90
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.running = False
    
    async def run(self):
        """Main loop."""
        self.running = True
        
        logger.info("[DataCleanup] Starting cleanup job")
        
        while self.running:
            try:
                await self._cleanup()
            except Exception as e:
                logger.error(f"[DataCleanup] Error: {e}", exc_info=True)
            
            await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
    
    async def _cleanup(self):
        """Run all cleanup tasks."""
        from sqlalchemy import delete, text
        from datetime import datetime, timedelta
        
        # Calculate cutoff dates
        mood_cutoff = datetime.utcnow() - timedelta(days=self.MOOD_RETENTION_DAYS)
        proactive_cutoff = datetime.utcnow() - timedelta(days=self.PROACTIVE_LOG_RETENTION_DAYS)
        analytics_cutoff = datetime.utcnow() - timedelta(days=self.ANALYTICS_RETENTION_DAYS)
        
        # Cleanup old mood history
        from models.sql_models import MoodHistory
        result = await self.db.execute(
            delete(MoodHistory)
            .where(MoodHistory.detected_at < mood_cutoff)
        )
        logger.debug(f"[DataCleanup] Mood history deleted: {result.rowcount} rows")
        
        # Cleanup old proactive logs
        from models.sql_models import ProactiveLog
        result = await self.db.execute(
            delete(ProactiveLog)
            .where(ProactiveLog.sent_at < proactive_cutoff)
        )
        logger.debug(f"[DataCleanup] Proactive logs deleted: {result.rowcount} rows")
        
        # Cleanup old analytics
        from models.sql_models import AnalyticsEvent
        result = await self.db.execute(
            delete(AnalyticsEvent)
            .where(AnalyticsEvent.created_at < analytics_cutoff)
        )
        logger.debug(f"[DataCleanup] Analytics deleted: {result.rowcount} rows")
        
        # Cleanup expired quiz configs
        from models.sql_models import QuizConfig
        result = await self.db.execute(
            delete(QuizConfig)
            .where(QuizConfig.expires_at < datetime.utcnow())
        )
        logger.debug(f"[DataCleanup] Quiz configs deleted: {result.rowcount} rows")
        
        await self.db.commit()
    
    def stop(self):
        """Stop the job."""
        self.running = False