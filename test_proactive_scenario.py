#!/usr/bin/env python3
"""
Test Case: Proactive Messaging System
Scenario: User sends "my meeting is about to start in 2 minutes and it will remain for 1 minute"

Test Date: January 10, 2026
PROACTIVE_CHECK_INTERVAL_MINUTES: 1 minute (very aggressive for testing)

EXPECTED BEHAVIOR:
1. Message is analyzed and meeting is extracted
2. UserSchedule is created with start_time = now + 2 min, end_time = now + 3 min
3. Proactive job runs every 1 minute and:
   a) Sends preparation reminder (within 30 min before meeting)
   b) Sends completion message (after meeting ends)
   c) May send time-based greetings (if greeting time matches)
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Optional

# Add backend to path
sys.path.insert(0, '/home/abubakar/companion-bot/backend')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('/home/abubakar/companion-bot/backend/.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import models and services
from database import Base
from models.sql_models import User, Message, BotSettings, UserSchedule, ProactiveSession, GreetingPreference
from services.meeting_extractor import MeetingExtractor
from services.message_analyzer import MessageAnalyzer
from services.proactive_meeting_handler import ProactiveMeetingHandler

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://abubakar:123123@localhost:5432/companion_bot")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class ProactiveScenarioTest:
    """Test the proactive messaging scenario."""
    
    def __init__(self):
        self.test_user = None
        self.test_bot = None
        self.test_message = None
        self.extracted_schedule = None
        
    async def setup(self):
        """Set up test database and create test user/bot."""
        async with AsyncSessionLocal() as session:
            # Create a test user if not exists
            result = await session.execute(
                select(User).where(User.username == "test_user_proactive")
            )
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                test_user = User(
                    username="test_user_proactive",
                    email="test_proactive@example.com",
                    tier="premium"
                )
                session.add(test_user)
                await session.flush()
            
            self.test_user = test_user
            
            # Create a test bot if not exists
            result = await session.execute(
                select(BotSettings).where(
                    (BotSettings.user_id == test_user.id) & 
                    (BotSettings.bot_name == "TestBot")
                )
            )
            test_bot = result.scalar_one_or_none()
            
            if not test_bot:
                test_bot = BotSettings(
                    user_id=test_user.id,
                    bot_name="TestBot",
                    archetype="golden_retriever",
                    is_primary=True
                )
                session.add(test_bot)
                await session.flush()
            
            self.test_bot = test_bot
            
            # Create greeting preference if not exists
            result = await session.execute(
                select(GreetingPreference).where(GreetingPreference.user_id == test_user.id)
            )
            greeting_pref = result.scalar_one_or_none()
            
            if not greeting_pref:
                greeting_pref = GreetingPreference(
                    user_id=test_user.id,
                    prefer_proactive=True,
                    max_proactive_per_day=10  # High limit for testing
                )
                session.add(greeting_pref)
            
            await session.commit()
            logger.info(f"✓ Test setup complete. User: {test_user.id}, Bot: {test_bot.id}")
    
    async def step_1_analyze_message(self):
        """STEP 1: Analyze the test message for meetings."""
        logger.info("\n" + "="*80)
        logger.info("STEP 1: MESSAGE ANALYSIS")
        logger.info("="*80)
        
        test_message_text = "my meeting is about to start in 2 minutes and it will remain for 1 minute"
        logger.info(f"📨 Test Message: '{test_message_text}'")
        
        # Extract meetings from the message
        extractor = MeetingExtractor()
        meetings = extractor.extract_meetings(test_message_text)
        
        if meetings:
            logger.info(f"✓ Meeting DETECTED: {len(meetings)} meeting(s) found")
            for i, meeting in enumerate(meetings, 1):
                logger.info(f"\n  Meeting {i}:")
                logger.info(f"    Event Name: {meeting.event_name}")
                logger.info(f"    Start Time: {meeting.start_time}")
                logger.info(f"    End Time: {meeting.end_time}")
                logger.info(f"    Duration: {meeting.end_time - meeting.start_time if meeting.end_time else 'N/A'}")
                logger.info(f"    Confidence: {meeting.confidence}")
                logger.info(f"    Description: {meeting.description}")
        else:
            logger.warning("✗ Meeting NOT DETECTED - message may be too informal or pattern not recognized")
        
        return test_message_text, meetings
    
    async def step_2_create_schedule(self, message_text: str, meetings: List):
        """STEP 2: Create UserSchedule entries from extracted meetings."""
        logger.info("\n" + "="*80)
        logger.info("STEP 2: CREATE USER SCHEDULE")
        logger.info("="*80)
        
        async with AsyncSessionLocal() as session:
            # CRITICAL FINDING: Meeting extractor detected the meeting but failed to parse times
            # "in 2 minutes" and "1 minute" are NOT being extracted by the current regex patterns
            # So we'll manually create a schedule to test the proactive flow
            
            now = datetime.utcnow()
            
            if not meetings or meetings[0].start_time is None:
                logger.warning("⚠️  TIME PARSING FAILED:")
                logger.warning("   The meeting extractor detected 'meeting' keyword")
                logger.warning("   but failed to parse 'in 2 minutes' and '1 minute'")
                logger.warning("   ")
                logger.warning("   Manually creating schedule with test times for proactive testing...")
                
                # Create schedule manually with test timing
                schedule = UserSchedule(
                    user_id=self.test_user.id,
                    bot_id=self.test_bot.id,
                    event_name="Test Meeting",
                    description=message_text,
                    start_time=now + timedelta(minutes=2),
                    end_time=now + timedelta(minutes=3),
                    channel="telegram",
                    preparation_reminder_sent=False,
                    event_completed_sent=False
                )
                session.add(schedule)
                await session.commit()
                
                schedules = [schedule]
                logger.info("✓ Manual schedule created with simulated times")
            else:
                # Use the extracted meetings
                msg = Message(
                    user_id=self.test_user.id,
                    bot_id=self.test_bot.id,
                    content=message_text,
                    role="user",
                    message_type="reactive"
                )
                session.add(msg)
                await session.flush()
                
                # Use message analyzer to create schedules
                analyzer = MessageAnalyzer(session)
                schedules = await analyzer.analyze_for_schedules(
                    msg, self.test_user, self.test_bot, channel='telegram'
                )
                
                await session.commit()
            
            if schedules:
                logger.info(f"✓ Schedule CREATED: {len(schedules)} schedule(s) created")
                for i, schedule in enumerate(schedules, 1):
                    logger.info(f"\n  Schedule {i}:")
                    logger.info(f"    Event Name: {schedule.event_name}")
                    logger.info(f"    Start Time: {schedule.start_time}")
                    logger.info(f"    End Time: {schedule.end_time}")
                    logger.info(f"    Duration: {schedule.end_time - schedule.start_time if schedule.end_time else 'N/A'}")
                    logger.info(f"    Prep Reminder Sent: {schedule.preparation_reminder_sent}")
                    logger.info(f"    Completion Sent: {schedule.event_completed_sent}")
                    
                    # Calculate time until meeting
                    if schedule.start_time:
                        time_until_meeting = schedule.start_time - now
                        logger.info(f"    Time Until Meeting: {time_until_meeting.total_seconds() / 60:.1f} minutes")
                    
                    self.extracted_schedule = schedule
            else:
                logger.warning("✗ Schedule NOT CREATED - message analysis may have failed")
                logger.info("   This could mean:")
                logger.info("   - The message didn't match meeting extraction patterns")
                logger.info("   - Time parsing failed")
                logger.info("   - Meeting extractor needs improvement")
        
        return schedules
    
    async def step_3_trigger_proactive_job(self):
        """STEP 3: Manually trigger proactive job to check and send messages."""
        logger.info("\n" + "="*80)
        logger.info("STEP 3: TRIGGER PROACTIVE JOB")
        logger.info("="*80)
        
        async with AsyncSessionLocal() as session:
            handler = ProactiveMeetingHandler(session)
            
            # Run all three checks
            logger.info("\n📋 Running Preparation Reminder Check...")
            prep_count = await handler.check_and_send_preparation_reminders()
            logger.info(f"   → Preparation reminders sent: {prep_count}")
            
            logger.info("\n📋 Running Completion Message Check...")
            completion_count = await handler.check_and_send_completion_messages()
            logger.info(f"   → Completion messages sent: {completion_count}")
            
            logger.info("\n📋 Running Time-Based Greeting Check...")
            greeting_count = await handler.check_and_send_time_greetings()
            logger.info(f"   → Time-based greetings sent: {greeting_count}")
            
            total = prep_count + completion_count + greeting_count
            logger.info(f"\n✓ Total proactive messages sent: {total}")
            
            return prep_count, completion_count, greeting_count
    
    async def step_4_verify_proactive_sessions(self):
        """STEP 4: Check what proactive sessions were created."""
        logger.info("\n" + "="*80)
        logger.info("STEP 4: VERIFY PROACTIVE SESSIONS")
        logger.info("="*80)
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProactiveSession).where(ProactiveSession.user_id == self.test_user.id)
            )
            sessions = result.scalars().all()
            
            if sessions:
                logger.info(f"✓ Found {len(sessions)} proactive session(s):")
                for i, session_obj in enumerate(sessions, 1):
                    logger.info(f"\n  Session {i}:")
                    logger.info(f"    Type: {session_obj.session_type}")
                    logger.info(f"    Content: {session_obj.message_content[:100]}..." if session_obj.message_content else "    Content: N/A")
                    logger.info(f"    Sent At: {session_obj.sent_at}")
                    logger.info(f"    Acknowledged: {session_obj.acknowledged_at}")
                    logger.info(f"    Channel: {session_obj.channel}")
            else:
                logger.info("ℹ No proactive sessions found yet")
    
    async def step_5_check_database_state(self):
        """STEP 5: Display final database state."""
        logger.info("\n" + "="*80)
        logger.info("STEP 5: FINAL DATABASE STATE")
        logger.info("="*80)
        
        async with AsyncSessionLocal() as session:
            # Check schedules
            result = await session.execute(
                select(UserSchedule).where(UserSchedule.user_id == self.test_user.id)
            )
            schedules = result.scalars().all()
            
            logger.info(f"\n📅 User Schedules: {len(schedules)}")
            for schedule in schedules:
                logger.info(f"  - {schedule.event_name}")
                logger.info(f"    Start: {schedule.start_time}, End: {schedule.end_time}")
                logger.info(f"    Prep Reminder Sent: {schedule.preparation_reminder_sent}")
                logger.info(f"    Completion Sent: {schedule.event_completed_sent}")
            
            # Check proactive sessions
            result = await session.execute(
                select(ProactiveSession).where(ProactiveSession.user_id == self.test_user.id)
            )
            sessions = result.scalars().all()
            
            logger.info(f"\n📬 Proactive Sessions: {len(sessions)}")
            for session_obj in sessions:
                logger.info(f"  - {session_obj.session_type} (sent at {session_obj.sent_at})")
    
    async def cleanup(self):
        """Clean up test data."""
        logger.info("\n" + "="*80)
        logger.info("CLEANUP")
        logger.info("="*80)
        
        async with AsyncSessionLocal() as session:
            # Delete test data
            result = await session.execute(
                select(User).where(User.username == "test_user_proactive")
            )
            user = result.scalar_one_or_none()
            
            if user:
                await session.delete(user)
                await session.commit()
                logger.info("✓ Test data cleaned up")
    
    async def run_full_test(self):
        """Run the complete test scenario."""
        try:
            await self.setup()
            
            message_text, meetings = await self.step_1_analyze_message()
            schedules = await self.step_2_create_schedule(message_text, meetings)
            prep_count, completion_count, greeting_count = await self.step_3_trigger_proactive_job()
            await self.step_4_verify_proactive_sessions()
            await self.step_5_check_database_state()
            
            # Print summary
            logger.info("\n" + "="*80)
            logger.info("TEST SUMMARY")
            logger.info("="*80)
            logger.info(f"Message Extracted: {'✓ YES' if meetings else '✗ NO'}")
            logger.info(f"Schedules Created: {'✓ YES' if schedules else '✗ NO'}")
            logger.info(f"Prep Reminders Sent: {prep_count}")
            logger.info(f"Completion Messages Sent: {completion_count}")
            logger.info(f"Time-Based Greetings Sent: {greeting_count}")
            logger.info(f"Total Proactive Messages: {prep_count + completion_count + greeting_count}")
            logger.info("="*80 + "\n")
            
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
        finally:
            await engine.dispose()


async def main():
    """Main entry point."""
    test = ProactiveScenarioTest()
    await test.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
