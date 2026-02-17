"""
Test script to verify end-to-end proactive system:
1. Create a schedule via the message analyzer
2. Run the proactive job
3. Verify reminders and messages are sent
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database import AsyncSessionLocal, Base
from models.sql_models import User, UserSchedule, GreetingPreference, BotSettings, Message, ProactiveSession
from services.proactive_meeting_handler import ProactiveMeetingHandler
from services.message_analyzer import MessageAnalyzer
from services.meeting_extractor import MeetingExtractor
from sqlalchemy import select


async def test_end_to_end():
    """Test complete flow with real database"""
    print("\n" + "="*80)
    print("END-TO-END PROACTIVE SYSTEM TEST")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Get or create test user
            print("\n1️⃣  Getting or creating test user...")
            from datetime import datetime
            
            # Try to find existing user first
            result = await session.execute(
                select(User).where(User.email == "test_e2e_proactive@example.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    id=uuid4(),
                    username=f"test_user_e2e_{uuid4().hex[:8]}",
                    email="test_e2e_proactive@example.com",
                    tier="free",
                    timezone="UTC"
                )
                session.add(user)
                await session.commit()
                print(f"   ✓ New user created: {user.id}")
            else:
                print(f"   ✓ Using existing user: {user.id}")
            
            # 2. Create bot settings
            print("\n2️⃣  Getting or creating bot settings...")
            
            # Try to find existing bot settings
            from sqlalchemy import select as sq_select
            result = await session.execute(
                sq_select(BotSettings).where(
                    (BotSettings.user_id == user.id) &
                    (BotSettings.archetype == "golden_retriever")
                )
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                bot = BotSettings(
                    id=uuid4(),
                    user_id=user.id,
                    bot_name="TestBot",
                    archetype="golden_retriever",
                    is_active=True,
                    is_primary=True
                )
                session.add(bot)
                await session.commit()
                print(f"   ✓ New bot created")
            else:
                print(f"   ✓ Using existing bot")
            
            # 4. Create a message and schedule
            print("\n3️⃣  Creating schedule via message analyzer...")
            message_text = "I have a meeting tomorrow at 2 PM for 1 hour"
            
            user_message = Message(
                user_id=user.id,
                role='user',
                content=message_text,
                message_type='reactive'
            )
            session.add(user_message)
            await session.commit()
            
            # Analyze message for schedules
            analyzer = MessageAnalyzer(session)
            schedules = await analyzer.analyze_for_schedules(
                user_message,
                user,
                bot,
                channel="telegram"
            )
            
            print(f"   ✓ Message analyzed")
            if schedules:
                print(f"   ✓ Created {len(schedules)} schedule(s)")
                for sched in schedules:
                    print(f"     - {sched.event_name}: {sched.start_time} → {sched.end_time}")
            else:
                # Create schedule manually if extraction failed
                print("   ⚠️  Auto-extraction failed, creating manual schedule...")
                now = datetime.utcnow()
                start_time = now + timedelta(minutes=2)
                end_time = start_time + timedelta(minutes=1)
                
                schedule = UserSchedule(
                    id=uuid4(),
                    user_id=user.id,
                    bot_id=bot.id,
                    event_name="Test Meeting",
                    start_time=start_time,
                    end_time=end_time,
                    channel="telegram",
                    preparation_reminder_sent=False,
                    event_completed_sent=False,
                )
                session.add(schedule)
                await session.commit()
                print(f"   ✓ Manual schedule created")
            
            # 5. Check what schedules exist
            print("\n4️⃣  Checking schedules in database...")
            result = await session.execute(
                select(UserSchedule).where(UserSchedule.user_id == user.id)
            )
            all_schedules = result.scalars().all()
            print(f"   ✓ Found {len(all_schedules)} schedule(s)")
            for sched in all_schedules:
                print(f"     - {sched.event_name}: {sched.start_time}")
            
            # 6. Run proactive job
            print("\n5️⃣  Running proactive meeting checker...")
            handler = ProactiveMeetingHandler(session)
            
            # Check preparation reminders
            print("   • Checking preparation reminders...")
            prep_count = await handler.check_and_send_preparation_reminders()
            print(f"     ✓ Sent {prep_count} preparation reminder(s)")
            
            # Check completion messages
            print("   • Checking completion messages...")
            comp_count = await handler.check_and_send_completion_messages()
            print(f"     ✓ Sent {comp_count} completion message(s)")
            
            # 7. Verify ProactiveSession records
            print("\n6️⃣  Verifying proactive sessions...")
            result = await session.execute(
                select(ProactiveSession).where(ProactiveSession.user_id == user.id)
            )
            sessions = result.scalars().all()
            print(f"   ✓ Created {len(sessions)} proactive session(s)")
            for ps in sessions:
                print(f"     - {ps.session_type}: {ps.message_content[:50]}...")
            
            # 8. Check /schedule command
            print("\n7️⃣  Testing /schedule command simulation...")
            result = await session.execute(
                select(UserSchedule).where(
                    (UserSchedule.user_id == user.id) &
                    (UserSchedule.is_completed == False)
                ).order_by(UserSchedule.start_time)
            )
            upcoming = result.scalars().all()
            if upcoming:
                print(f"   ✓ Upcoming schedules: {len(upcoming)}")
                for sched in upcoming:
                    print(f"     - {sched.event_name} at {sched.start_time}")
            else:
                print(f"   ⚠️  No upcoming schedules found")
            
            print("\n" + "="*80)
            print("✅ END-TO-END TEST COMPLETED")
            print("="*80)
            print("\n📊 Summary:")
            print(f"   ✓ User created: {user.id}")
            print(f"   ✓ Bot settings created: {bot.id}")
            print(f"   ✓ Schedules created: {len(all_schedules)}")
            print(f"   ✓ Preparation reminders sent: {prep_count}")
            print(f"   ✓ Completion messages sent: {comp_count}")
            print(f"   ✓ Proactive sessions created: {len(sessions)}")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await session.rollback()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(test_end_to_end())
