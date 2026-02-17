"""
Diagnostic test to verify the complete proactive system flow.
This test creates a message with a meeting time in the immediate future
and verifies that the proactive job correctly identifies and sends reminders.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import select
from database import AsyncSessionLocal
from models.sql_models import User, UserSchedule, BotSettings, Message, ProactiveSession
from services.proactive_meeting_handler import ProactiveMeetingHandler
from services.message_analyzer import MessageAnalyzer


async def test_immediate_meeting():
    """Test a meeting scheduled for the immediate future (5 minutes)"""
    print("\n" + "="*80)
    print("IMMEDIATE MEETING TEST - Verifying Proactive Reminders")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Get or create test user
            print("\n1️⃣  Setting up test user and bot...")
            result = await session.execute(
                select(User).where(User.email == "test_immediate@example.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    id=uuid4(),
                    username=f"test_immediate_{uuid4().hex[:8]}",
                    email="test_immediate@example.com",
                    tier="free",
                    timezone="UTC"
                )
                session.add(user)
                await session.commit()
                print(f"   ✓ New user created")
            else:
                print(f"   ✓ Using existing user")
            
            # Get or create bot
            result = await session.execute(
                select(BotSettings).where(
                    (BotSettings.user_id == user.id) &
                    (BotSettings.archetype == "golden_retriever")
                )
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                bot = BotSettings(
                    id=uuid4(),
                    user_id=user.id,
                    bot_name="ImmediateTestBot",
                    archetype="golden_retriever",
                    is_active=True,
                    is_primary=True
                )
                session.add(bot)
                await session.commit()
                print(f"   ✓ New bot created")
            else:
                print(f"   ✓ Using existing bot")
            
            # 2. Create a message mentioning a meeting starting in 5 minutes
            print("\n2️⃣  Creating message about meeting in 5 minutes...")
            now = datetime.now()
            in_5_min = (now + timedelta(minutes=5)).strftime("%H:%M")
            
            message_text = f"I have a meeting at {in_5_min} that will last 30 minutes"
            print(f"   Message: '{message_text}'")
            print(f"   Current time: {now.strftime('%H:%M:%S')}")
            print(f"   Meeting at: {in_5_min}")
            
            user_message = Message(
                user_id=user.id,
                role='user',
                content=message_text,
                message_type='reactive'
            )
            session.add(user_message)
            await session.commit()
            
            # 3. Analyze message for schedules
            print("\n3️⃣  Analyzing message for schedules...")
            analyzer = MessageAnalyzer(session)
            schedules = await analyzer.analyze_for_schedules(
                user_message,
                user,
                bot,
                channel="telegram"
            )
            
            if schedules:
                print(f"   ✓ Created {len(schedules)} schedule(s)")
                for sched in schedules:
                    time_until = (sched.start_time - datetime.now()).total_seconds() / 60
                    print(f"     - {sched.event_name}: {sched.start_time} ({time_until:.1f} min away)")
            else:
                print(f"   ⚠️  No schedules created from message")
            
            # 4. Verify schedules in database
            print("\n4️⃣  Checking schedules in database...")
            result = await session.execute(
                select(UserSchedule).where(UserSchedule.user_id == user.id)
            )
            all_schedules = result.scalars().all()
            print(f"   ✓ Found {len(all_schedules)} schedule(s)")
            
            for sched in all_schedules:
                if sched.start_time:
                    time_until = (sched.start_time - datetime.now()).total_seconds() / 60
                    print(f"     - {sched.event_name}: starts in {time_until:.1f} min")
                    print(f"       Prep reminder sent: {sched.preparation_reminder_sent}")
                    print(f"       Completion sent: {sched.event_completed_sent}")
            
            # 5. Run proactive job to check for reminders
            print("\n5️⃣  Running proactive meeting checker...")
            handler = ProactiveMeetingHandler(session)
            
            print("   • Checking preparation reminders...")
            prep_count = await handler.check_and_send_preparation_reminders()
            print(f"     ✓ Sent {prep_count} preparation reminder(s)")
            
            print("   • Checking completion messages...")
            comp_count = await handler.check_and_send_completion_messages()
            print(f"     ✓ Sent {comp_count} completion message(s)")
            
            # 6. Check proactive sessions created
            print("\n6️⃣  Checking proactive sessions...")
            result = await session.execute(
                select(ProactiveSession).where(ProactiveSession.user_id == user.id)
            )
            sessions = result.scalars().all()
            print(f"   ✓ Created {len(sessions)} proactive session(s)")
            for ps in sessions:
                print(f"     - {ps.session_type}: '{ps.message_content[:60]}...'")
            
            # 7. Summary
            print("\n" + "="*80)
            if prep_count > 0:
                print("✅ SUCCESS: Proactive reminder sent for upcoming meeting!")
            else:
                print("⚠️  No preparation reminders sent (meeting might be >30 min away)")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_immediate_meeting())
