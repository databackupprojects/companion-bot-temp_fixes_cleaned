# backend/services/proactive_meeting_handler.py
"""
Handles proactive behavior for meetings and scheduled events.
Sends preparation reminders before meetings and followup messages after.
Also handles time-based greetings (morning, afternoon, evening, night).
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from models.sql_models import UserSchedule, User, ProactiveSession, GreetingPreference, BotSettings, Message
import pytz

logger = logging.getLogger(__name__)


class ProactiveMeetingHandler:
    """Manages proactive reminders and followups for scheduled meetings and time-based greetings."""
    
    # How many minutes before a meeting to send a preparation reminder
    PREPARATION_REMINDER_LEAD_TIME_MINUTES = 30

    # How long after a meeting to wait before sending a followup
    FOLLOWUP_DELAY_MINUTES = 1

    # Assumed meeting duration (minutes) when no end_time is provided
    DEFAULT_MEETING_DURATION_MINUTES = 60
    
    def __init__(self, db: AsyncSession, llm_client=None):
        self.db = db
        self.llm = llm_client
    
    async def check_and_send_preparation_reminders(self) -> int:
        """
        Check for upcoming meetings and send preparation reminders.
        Returns count of reminders sent.
        """
        reminders_sent = 0
        try:
            # Use UTC for all internal comparisons
            now = datetime.utcnow()
            reminder_window_start = now
            reminder_window_end = now + timedelta(minutes=self.PREPARATION_REMINDER_LEAD_TIME_MINUTES + 5)
            
            # Find upcoming meetings that haven't had reminders sent
            result = await self.db.execute(
                select(UserSchedule).where(
                    and_(
                        UserSchedule.start_time >= reminder_window_start,
                        UserSchedule.start_time <= reminder_window_end,
                        UserSchedule.preparation_reminder_sent == False,
                        UserSchedule.is_completed == False
                    )
                )
            )
            upcoming_meetings = result.scalars().all()
            
            for schedule in upcoming_meetings:
                try:
                    sent = await self._send_preparation_reminder(schedule)
                    if sent:
                        reminders_sent += 1
                        logger.info(f"Sent preparation reminder for {schedule.event_name} to user {schedule.user_id}")
                except Exception as e:
                    logger.error(f"Error sending preparation reminder for {schedule.id}: {e}", exc_info=True)
                    try:
                        await self.db.rollback()
                    except:
                        pass
                    continue
            
            return reminders_sent
        except Exception as e:
            logger.error(f"Error in check_and_send_preparation_reminders: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return reminders_sent
    
    async def check_and_send_completion_messages(self) -> int:
        """
        Check for meetings that have completed and send followup messages.
        Returns count of completion messages sent.
        """
        messages_sent = 0
        try:
            now = datetime.utcnow()
            followup_window = now - timedelta(minutes=self.FOLLOWUP_DELAY_MINUTES)

            # --- Case 1: meetings WITH an explicit end_time ---
            result = await self.db.execute(
                select(UserSchedule).where(
                    and_(
                        UserSchedule.end_time.isnot(None),
                        UserSchedule.end_time <= followup_window,
                        UserSchedule.event_completed_sent == False,
                        UserSchedule.is_completed == False
                    )
                )
            )
            completed_meetings = result.scalars().all()

            # --- Case 2: meetings WITHOUT end_time — assume DEFAULT_MEETING_DURATION_MINUTES ---
            assumed_end_cutoff = now - timedelta(minutes=self.DEFAULT_MEETING_DURATION_MINUTES + self.FOLLOWUP_DELAY_MINUTES)
            result2 = await self.db.execute(
                select(UserSchedule).where(
                    and_(
                        UserSchedule.end_time.is_(None),
                        UserSchedule.start_time <= assumed_end_cutoff,
                        UserSchedule.event_completed_sent == False,
                        UserSchedule.is_completed == False
                    )
                )
            )
            completed_meetings = list(completed_meetings) + list(result2.scalars().all())

            for schedule in completed_meetings:
                try:
                    sent = await self._send_completion_message(schedule)
                    if sent:
                        messages_sent += 1
                        logger.info(f"Sent completion message for {schedule.event_name} to user {schedule.user_id}")
                except Exception as e:
                    logger.error(f"Error sending completion message for {schedule.id}: {e}", exc_info=True)
                    try:
                        await self.db.rollback()
                    except:
                        pass
                    continue

            return messages_sent
        except Exception as e:
            logger.error(f"Error in check_and_send_completion_messages: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return messages_sent
    
    async def check_first_interaction_after_meeting(self, user_id: str, channel: str) -> Optional[Dict[str, Any]]:
        """
        When user interacts with the bot after a meeting (if end_time not provided),
        send a greeting asking about the meeting.
        """
        now = datetime.utcnow()
        
        # Find recent meetings without end times that haven't had followup
        result = await self.db.execute(
            select(UserSchedule).where(
                and_(
                    UserSchedule.user_id == user_id,
                    UserSchedule.end_time.is_(None),
                    UserSchedule.followup_sent == False,
                    UserSchedule.start_time < now,
                    # Meeting started at least 15 minutes ago (rough estimate for duration)
                    UserSchedule.start_time > now - timedelta(hours=8),
                    UserSchedule.channel == channel
                )
            )
        )
        meetings = result.scalars().all()
        
        if meetings:
            meeting = meetings[0]  # Get most recent
            try:
                sent = await self._send_followup_greeting(meeting, channel)
                if sent:
                    return {
                        'schedule_id': str(meeting.id),
                        'event_name': meeting.event_name,
                        'message': sent,
                        'channel': channel
                    }
            except Exception as e:
                logger.error(f"Error sending followup greeting: {e}")
        
        return None
    
    async def get_upcoming_meetings(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming meetings for a user in the next N hours."""
        now = datetime.utcnow()
        future = now + timedelta(hours=hours)
        
        result = await self.db.execute(
            select(UserSchedule).where(
                and_(
                    UserSchedule.user_id == user_id,
                    UserSchedule.start_time >= now,
                    UserSchedule.start_time <= future,
                    UserSchedule.is_completed == False
                )
            ).order_by(UserSchedule.start_time)
        )
        meetings = result.scalars().all()
        
        return [
            {
                'id': str(m.id),
                'name': m.event_name,
                'start': m.start_time.isoformat(),
                'end': m.end_time.isoformat() if m.end_time else None,
                'channel': m.channel
            }
            for m in meetings
        ]
    
    async def _send_preparation_reminder(self, schedule: UserSchedule) -> bool:
        """Send preparation reminder before a meeting."""
        try:
            user = await self.db.get(User, schedule.user_id)
            if not user:
                return False
            
            # Get archetype from bot settings
            from models.sql_models import BotSettings
            bot = await self.db.get(BotSettings, schedule.bot_id)
            archetype = bot.archetype if bot else 'golden_retriever'
            
            # Generate message
            time_str = self._format_time(schedule.start_time, user.timezone)
            message = self._generate_preparation_message(schedule.event_name, time_str)
            
            # Actually send to Telegram if user has telegram_id
            if user.telegram_id and schedule.channel == 'telegram':
                await self._send_to_telegram(user.telegram_id, message, archetype)
            
            # Store in proactive session
            session = ProactiveSession(
                user_id=schedule.user_id,
                bot_id=schedule.bot_id,
                session_type='meeting_prep_reminder',
                reference_id=schedule.id,
                message_content=message,
                channel=schedule.channel,
                sent_at=datetime.utcnow(),
                context_metadata={
                    'meeting_id': str(schedule.id),
                    'event_name': schedule.event_name
                }
            )
            self.db.add(session)
            
            # Update schedule
            schedule.preparation_reminder_sent = True
            schedule.preparation_reminder_sent_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Preparation reminder sent for {schedule.event_name} on {schedule.channel}")
            return True
            
        except Exception as e:
            logger.error(f"Error in _send_preparation_reminder: {e}")
            await self.db.rollback()
            return False
    
    async def _send_completion_message(self, schedule: UserSchedule) -> bool:
        """Send a message after a meeting has completed."""
        try:
            user = await self.db.get(User, schedule.user_id)
            if not user:
                return False
            
            # Get archetype from bot settings
            from models.sql_models import BotSettings
            bot = await self.db.get(BotSettings, schedule.bot_id)
            archetype = bot.archetype if bot else 'golden_retriever'
            
            # Generate completion message
            message = self._generate_completion_message(schedule.event_name)
            
            # Actually send to Telegram if user has telegram_id
            if user.telegram_id and schedule.channel == 'telegram':
                await self._send_to_telegram(user.telegram_id, message, archetype)
            
            # Store in proactive session
            session = ProactiveSession(
                user_id=schedule.user_id,
                bot_id=schedule.bot_id,
                session_type='meeting_completion',
                reference_id=schedule.id,
                message_content=message,
                channel=schedule.channel,
                sent_at=datetime.utcnow(),
                context_metadata={
                    'meeting_id': str(schedule.id),
                    'event_name': schedule.event_name,
                    'completed_at': datetime.utcnow().isoformat()
                }
            )
            self.db.add(session)
            
            # Update schedule
            schedule.event_completed_sent = True
            schedule.event_completed_sent_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Completion message sent for {schedule.event_name} on {schedule.channel}")
            return True
            
        except Exception as e:
            logger.error(f"Error in _send_completion_message: {e}")
            await self.db.rollback()
            return False
    
    async def _send_followup_greeting(self, schedule: UserSchedule, channel: str) -> Optional[str]:
        """Send a followup greeting when user returns to chat after a meeting."""
        try:
            user = await self.db.get(User, schedule.user_id)
            if not user:
                return None
            
            # Generate followup message
            message = self._generate_followup_greeting(schedule.event_name)
            
            # Store in proactive session
            session = ProactiveSession(
                user_id=schedule.user_id,
                bot_id=schedule.bot_id,
                session_type='meeting_followup_greeting',
                reference_id=schedule.id,
                message_content=message,
                channel=channel,
                context_metadata={
                    'meeting_id': str(schedule.id),
                    'event_name': schedule.event_name
                }
            )
            self.db.add(session)
            
            # Update schedule
            schedule.followup_sent = True
            schedule.followup_sent_at = datetime.utcnow()
            
            await self.db.commit()
            
            return message
            
        except Exception as e:
            logger.error(f"Error in _send_followup_greeting: {e}")
            await self.db.rollback()
            return None
    
    def _format_time(self, dt: datetime, timezone: str) -> str:
        """Format datetime in user's timezone."""
        try:
            tz = pytz.timezone(timezone)
            local_dt = dt.replace(tzinfo=pytz.UTC).astimezone(tz)
            return local_dt.strftime("%I:%M %p")
        except:
            return dt.strftime("%I:%M %p")
    
    def _generate_preparation_message(self, meeting_name: str, time_str: str) -> str:
        """Generate a preparation reminder message."""
        messages = [
            f"🕐 Heads up! Your {meeting_name} is coming up at {time_str}. Take a moment to prepare!",
            f"⏰ {meeting_name} starts at {time_str}. Getting ready?",
            f"📅 Just a reminder - {meeting_name} at {time_str}. Make sure you're all set!",
            f"🎯 {meeting_name} in 30 minutes ({time_str}). Deep breath, you got this!",
        ]
        import random
        return random.choice(messages)
    
    def _generate_completion_message(self, meeting_name: str) -> str:
        """Generate a message after a meeting is completed."""
        messages = [
            f"✨ Your {meeting_name} is done! How did it go?",
            f"🎉 {meeting_name} wrapped up! Anything you'd like to talk about?",
            f"👏 All done with {meeting_name}. How are you feeling?",
            f"📊 {meeting_name} is complete! Want to debrief?",
        ]
        import random
        return random.choice(messages)
    
    def _generate_followup_greeting(self, meeting_name: str) -> str:
        """Generate a greeting when user returns after a meeting."""
        messages = [
            f"Hey! 👋 How did your {meeting_name} go?",
            f"Welcome back! 😊 Tell me about your {meeting_name}.",
            f"How are you doing after {meeting_name}?",
            f"That {meeting_name} you mentioned - how did it turn out?",
        ]
        import random
        return random.choice(messages)    
    # ============================================
    # TIME-BASED GREETING METHODS
    # ============================================
    
    async def check_and_send_time_greetings(self) -> int:
        """
        Check for users who should receive time-based greetings.
        Returns count of greetings sent.
        """
        greetings_sent = 0
        
        try:
            # Get all active users who prefer proactive greetings
            result = await self.db.execute(
                select(User, GreetingPreference)
                .join(GreetingPreference, User.id == GreetingPreference.user_id, isouter=True)
                .where(
                    or_(
                        GreetingPreference.prefer_proactive == True,
                        GreetingPreference.prefer_proactive.is_(None)  # Default to True
                    )
                )
            )
            users_with_prefs = result.all()
            
            for user, pref in users_with_prefs:
                try:
                    # Check if user should receive greeting
                    should_send = await self._should_send_time_greeting(user, pref)
                    if should_send:
                        greeting_sent = await self._send_time_based_greeting(user)
                        if greeting_sent:
                            greetings_sent += 1
                except Exception as e:
                    # Log error and rollback transaction for this user's attempt
                    logger.error(f"Error checking greeting for user {user.id}: {e}", exc_info=True)
                    try:
                        await self.db.rollback()
                    except:
                        pass
                    # Continue to next user
                    continue
            
            return greetings_sent
            
        except Exception as e:
            logger.error(f"Error in check_and_send_time_greetings: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return greetings_sent
    
    async def _should_send_time_greeting(self, user: User, pref: Optional[GreetingPreference]) -> bool:
        """Check if user should receive a time-based greeting right now."""

        # Get user's current time
        user_tz = pytz.timezone(user.timezone or 'UTC')
        user_time = datetime.now(user_tz)
        current_hour = user_time.hour

        # Don't interrupt active conversations: skip if user sent a message in the last 30 minutes
        active_window = datetime.utcnow() - timedelta(minutes=30)
        recent_msg_result = await self.db.execute(
            select(User.id)
            .join(Message, Message.user_id == User.id)
            .where(
                User.id == user.id,
                Message.role == 'user',
                Message.created_at >= active_window
            )
            .limit(1)
        )
        if recent_msg_result.scalar_one_or_none():
            return False

        # Check DND (Do Not Disturb) hours
        if pref:
            dnd_start = pref.dnd_start_hour or 22
            dnd_end = pref.dnd_end_hour or 6

            # Handle DND wrapping around midnight
            if dnd_start > dnd_end:  # e.g., 22 to 6
                if current_hour >= dnd_start or current_hour < dnd_end:
                    return False
            else:  # e.g., 1 to 5
                if dnd_start <= current_hour < dnd_end:
                    return False

            # Check max greetings per day
            max_per_day = pref.max_proactive_per_day or 3
            today_count = await self._get_todays_greeting_count(user.id)
            if today_count >= max_per_day:
                return False

        # Check if greeting already sent in this time period today
        greeting_type = self._get_greeting_type(current_hour)
        already_sent = await self._check_greeting_sent_today(user.id, greeting_type)

        return not already_sent
    
    async def _send_time_based_greeting(self, user: User) -> bool:
        """Send a time-based greeting to the user."""
        try:
            # Get user's timezone and current time
            user_tz = pytz.timezone(user.timezone or 'UTC')
            user_time = datetime.now(user_tz)
            current_hour = user_time.hour
            
            # Check if this greeting type was already sent today
            greeting_type = self._get_greeting_type(current_hour)
            if await self._check_greeting_sent_today(user.id, greeting_type):
                logger.debug(f"Already sent {greeting_type} greeting to user {user.id} today")
                return False
            
            # Get user's primary bot (fall back to first bot if none marked primary)
            result = await self.db.execute(
                select(BotSettings)
                .where(BotSettings.user_id == user.id, BotSettings.is_active == True)
                .order_by(BotSettings.is_primary.desc())
                .limit(1)
            )
            bot_settings = result.scalar_one_or_none()

            if not bot_settings:
                logger.debug(f"No bot found for user {user.id}")
                return False
            
            # Generate greeting message
            message = self._generate_time_greeting(greeting_type, bot_settings.bot_name or user.name)
            
            # Determine channel (prefer telegram if available, else web)
            channel = "telegram" if user.telegram_id else "web"

            # Actually send to Telegram if user has telegram_id
            if user.telegram_id:
                await self._send_to_telegram(user.telegram_id, message, bot_settings.archetype or 'golden_retriever')

            # Create proactive session with sent_at timestamp
            session = ProactiveSession(
                user_id=user.id,
                bot_id=bot_settings.id,
                session_type=f'{greeting_type}_greeting',
                message_content=message,
                channel=channel,
                sent_at=datetime.utcnow(),  # Set sent_at for tracking
                context_metadata={
                    'greeting_type': greeting_type,
                    'user_hour': current_hour
                }
            )
            self.db.add(session)
            await self.db.commit()
            
            logger.info(f"Sent {greeting_type} greeting to user {user.id} via {channel}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending time greeting for user {user.id}: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return False
    
    def _get_greeting_type(self, hour: int) -> str:
        """Determine greeting type based on hour of day (using env config)."""
        morning_start = int(os.getenv("GREETING_MORNING_START_HOUR", "6"))
        morning_end = int(os.getenv("GREETING_MORNING_END_HOUR", "12"))
        afternoon_start = int(os.getenv("GREETING_AFTERNOON_START_HOUR", "12"))
        afternoon_end = int(os.getenv("GREETING_AFTERNOON_END_HOUR", "17"))
        evening_start = int(os.getenv("GREETING_EVENING_START_HOUR", "17"))
        evening_end = int(os.getenv("GREETING_EVENING_END_HOUR", "22"))
        
        if morning_start <= hour < morning_end:
            return "morning"
        elif afternoon_start <= hour < afternoon_end:
            return "afternoon"
        elif evening_start <= hour < evening_end:
            return "evening"
        else:
            return "night"
    
    def _generate_time_greeting(self, greeting_type: str, user_name: str) -> str:
        """Generate a greeting message based on time of day."""
        import random
        
        greetings = {
            "morning": [
                f"Good morning, {user_name}! ☀️ How are you starting your day?",
                f"Morning! 🌅 Hope you slept well. What's on your agenda today?",
                f"Hey {user_name}! 🌞 Ready to tackle the day?",
                f"Good morning! ☕ How's your day looking so far?",
            ],
            "afternoon": [
                f"Hey {user_name}! 👋 How's your afternoon going?",
                f"Good afternoon! ☀️ Getting through the day okay?",
                f"Afternoon! 🌤️ Need a break or want to chat?",
                f"Hey! How's your day been so far?",
            ],
            "evening": [
                f"Good evening, {user_name}! 🌆 How was your day?",
                f"Hey! 🌙 Winding down for the evening?",
                f"Evening! ✨ Tell me about your day.",
                f"Hey {user_name}! How did today go?",
            ],
            "night": [
                f"Hey {user_name}! 🌙 Still up?",
                f"Late night? 🌃 What's keeping you awake?",
                f"Night owl, huh? 🦉 What are you up to?",
                f"Hey! 💫 Everything okay?",
            ]
        }
        
        return random.choice(greetings.get(greeting_type, greetings["morning"]))
    
    async def _get_todays_greeting_count(self, user_id: str) -> int:
        """Get count of greetings sent to user today (in UTC)."""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            result = await self.db.execute(
                select(ProactiveSession)
                .where(
                    and_(
                        ProactiveSession.user_id == user_id,
                        ProactiveSession.session_type.like('%_greeting'),
                        ProactiveSession.sent_at >= today_start
                    )
                )
            )
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting greeting count for user {user_id}: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return 0
    
    async def _check_greeting_sent_today(self, user_id: str, greeting_type: str) -> bool:
        """Check if this type of greeting was already sent today (in UTC)."""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            result = await self.db.execute(
                select(ProactiveSession)
                .where(
                    and_(
                        ProactiveSession.user_id == user_id,
                        ProactiveSession.session_type == f'{greeting_type}_greeting',
                        ProactiveSession.sent_at >= today_start
                    )
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking greeting sent: {e}")
            return False
    
    async def _send_to_telegram(self, telegram_id: int, message: str, archetype: str = 'golden_retriever') -> bool:
        """Send a message to a Telegram user using the correct bot."""
        try:
            from telegram import Bot
            from telegram.request import HTTPXRequest
            from constants import get_telegram_bot_token

            # Get the bot token for this archetype
            token = get_telegram_bot_token(archetype)
            if not token:
                logger.error(f"No token found for archetype {archetype}")
                return False

            # Send the message with extended timeout
            request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0, write_timeout=20.0)
            bot = Bot(token=token, request=request)
            await bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Sent Telegram message to {telegram_id} via {archetype} bot")
            return True
            
        except Exception as e:
            logger.error(f"Error sending to Telegram {telegram_id}: {e}", exc_info=True)
            return False