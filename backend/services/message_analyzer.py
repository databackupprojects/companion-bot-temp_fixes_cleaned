# backend/services/message_analyzer.py
"""
Analyzes incoming messages for actionable information like meetings and schedules.
Integrates with meeting extraction to automatically track user's schedule.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import pytz

from models.sql_models import UserSchedule, User, Message, BotSettings
from services.meeting_extractor import MeetingExtractor, MeetingInfo
from utils.timezone import get_utc_now

logger = logging.getLogger(__name__)


class MessageAnalyzer:
    """Analyzes user messages for actionable schedule information."""
    
    def __init__(self, db: AsyncSession, meeting_extractor: Optional[MeetingExtractor] = None):
        self.db = db
        self.meeting_extractor = meeting_extractor or MeetingExtractor()
    
    async def analyze_for_schedules(
        self,
        message: Message,
        user: User,
        bot: BotSettings,
        channel: str = 'web'
    ) -> List[UserSchedule]:
        """
        Analyze a message for schedule/meeting information and create schedule entries.
        
        Args:
            message: The Message object
            user: The User object
            bot: The BotSettings object
            channel: 'web' or 'telegram'
            
        Returns:
            List of created UserSchedule objects
        """
        created_schedules = []
        
        try:
            # Extract meetings from the message
            # Use UTC as reference, but convert to user's timezone for extraction
            # This ensures relative times like "in 1 minute" are in user's timezone
            utc_now = get_utc_now()
            user_tz = pytz.timezone(user.timezone or 'UTC')
            user_now = utc_now.replace(tzinfo=pytz.UTC).astimezone(user_tz).replace(tzinfo=None)
            
            meetings = self.meeting_extractor.extract_meetings(
                message.content,
                reference_time=user_now
            )
            
            if not meetings:
                return created_schedules
            
            logger.info(f"Found {len(meetings)} meeting(s) in message from user {user.id}")
            
            # Create schedule entries for each meeting found
            for meeting in meetings:
                try:
                    # Only create if we have good confidence
                    if meeting.confidence < 0.5:
                        logger.debug(f"Skipping meeting '{meeting.event_name}' - low confidence ({meeting.confidence})")
                        continue
                    
                    # Check if schedule already exists (prevent duplicates)
                    existing = await self._check_duplicate_schedule(
                        user.id, 
                        meeting.event_name, 
                        meeting.start_time
                    )
                    
                    if existing:
                        logger.debug(f"Schedule already exists for {meeting.event_name}")
                        continue
                    
                    # Create new schedule
                    # Convert extracted times from user's timezone to UTC for storage
                    start_time_utc = None
                    end_time_utc = None
                    
                    if meeting.start_time:
                        # meeting.start_time is naive, extracted in user's timezone context
                        # Localize it to user's timezone, then convert to UTC
                        if meeting.start_time.tzinfo is None:
                            localized = user_tz.localize(meeting.start_time)
                            start_time_utc = localized.astimezone(pytz.UTC).replace(tzinfo=None)
                        else:
                            start_time_utc = meeting.start_time.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    if meeting.end_time:
                        if meeting.end_time.tzinfo is None:
                            localized = user_tz.localize(meeting.end_time)
                            end_time_utc = localized.astimezone(pytz.UTC).replace(tzinfo=None)
                        else:
                            end_time_utc = meeting.end_time.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    schedule = UserSchedule(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        bot_id=bot.id,
                        event_name=meeting.event_name,
                        description=meeting.description,
                        start_time=start_time_utc,
                        end_time=end_time_utc,
                        channel=channel,
                        message_id=message.id,
                        created_at=get_utc_now(),
                        updated_at=get_utc_now()
                    )
                    
                    self.db.add(schedule)
                    created_schedules.append(schedule)
                    
                    logger.info(
                        f"Created schedule '{meeting.event_name}' for user {user.id} "
                        f"at {meeting.start_time} (confidence: {meeting.confidence})"
                    )
                    
                except Exception as e:
                    logger.error(f"Error creating schedule from meeting data: {e}", exc_info=True)
                    continue
            
            # Commit all new schedules
            if created_schedules:
                await self.db.commit()
                logger.info(f"Committed {len(created_schedules)} new schedule(s)")
            
        except Exception as e:
            logger.error(f"Error analyzing message for schedules: {e}", exc_info=True)
            await self.db.rollback()
        
        return created_schedules
    
    async def _check_duplicate_schedule(
        self,
        user_id: str,
        event_name: str,
        start_time: Optional[datetime]
    ) -> bool:
        """
        Check if a similar schedule already exists to prevent duplicates.
        """
        from sqlalchemy import select, and_
        
        try:
            # If no start time, can't reliably check for duplicates
            if not start_time:
                return False
            
            # Check for exact match within a 5-minute window
            from datetime import timedelta
            window = timedelta(minutes=5)
            
            result = await self.db.execute(
                select(UserSchedule).where(
                    and_(
                        UserSchedule.user_id == user_id,
                        UserSchedule.event_name.ilike(f"%{event_name}%"),
                        UserSchedule.start_time >= start_time - window,
                        UserSchedule.start_time <= start_time + window,
                        UserSchedule.is_completed == False
                    )
                )
            )
            
            existing = result.scalars().first()
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate schedule: {e}")
            return False
