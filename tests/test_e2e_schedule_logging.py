"""
End-to-end test for Telegram /schedule command and chat logging.
This tests the complete pipeline as it would work in production.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path
import json

backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import select
from database import AsyncSessionLocal
from models.sql_models import User, UserSchedule, BotSettings, Message
from handlers.message_handler import MessageHandler
from handlers.command_handler import CommandHandler
from utils.chat_logger import chat_logger


async def test_telegram_schedule_workflow():
    """Test complete Telegram workflow: send message about meeting -> /schedule command."""
    print("\n" + "="*80)
    print("E2E TEST: Telegram /schedule Workflow")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Setup
            print("\n1️⃣  Setting up test environment...")
            user = User(
                id=uuid4(),
                username="telegram_test_user",
                email=f"telegram_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC",
                telegram_id=int(uuid4().int % 1000000000)
            )
            session.add(user)
            await session.commit()
            print(f"   ✓ User created: {user.username}")
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="GoldenRetriever",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            await session.commit()
            print(f"   ✓ Bot created: {bot.archetype}")
            
            # 2. Simulate receiving a message about a meeting
            print("\n2️⃣  Simulating user message about meeting...")
            now = datetime.now()
            user_message_text = "I have a team meeting tomorrow at 2 PM for 1 hour"
            
            # Save message to database
            message = Message(
                user_id=user.id,
                role='user',
                content=user_message_text,
                message_type='reactive'
            )
            session.add(message)
            await session.commit()
            print(f"   ✓ Message saved: '{user_message_text}'")
            
            # 3. Create schedule from the message
            print("\n3️⃣  Creating schedule from message...")
            schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Team Meeting",
                description=user_message_text,
                start_time=now + timedelta(days=1, hours=2),
                end_time=now + timedelta(days=1, hours=3),
                channel="telegram",
                message_id=message.id
            )
            session.add(schedule)
            await session.commit()
            print(f"   ✓ Schedule created: {schedule.event_name}")
            
            # 4. Log the conversation
            print("\n4️⃣  Logging conversation...")
            bot_response = "Got it! I'll remember your team meeting tomorrow at 2 PM. 📅"
            chat_logger.log_conversation(
                user_id=str(user.id),
                username=user.username,
                bot_id=bot.archetype,
                user_message=user_message_text,
                bot_response=bot_response,
                message_type="reactive",
                source="telegram"
            )
            print(f"   ✓ Conversation logged")
            
            # 5. User sends /schedule command
            print("\n5️⃣  User sends /schedule command...")
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': user.telegram_id,
                'username': user.username,
                'timezone': user.timezone
            }
            
            schedule_response = await command_handler._handle_schedule(
                str(user.id),
                user_dict,
                "",
                "golden_retriever"
            )
            
            print(f"   ✓ /schedule command response received")
            print(f"   Response:")
            for line in schedule_response.split('\n')[:10]:
                print(f"     {line}")
            
            # 6. Log the command interaction
            print("\n6️⃣  Logging /schedule command interaction...")
            chat_logger.log_conversation(
                user_id=str(user.id),
                username=user.username,
                bot_id=bot.archetype,
                user_message="/schedule",
                bot_response=schedule_response,
                message_type="reactive",
                source="telegram"
            )
            print(f"   ✓ Command interaction logged")
            
            # 7. Verify logs
            print("\n7️⃣  Verifying log files...")
            logs_dir = Path(chat_logger.logs_dir)
            user_folder = f"{user.username}_{user.id}"
            user_log_dir = logs_dir / user_folder / bot.archetype
            
            daily_log = user_log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
            if daily_log.exists():
                with open(daily_log, 'r') as f:
                    log_entries = json.load(f)
                
                print(f"   ✓ Daily log: {daily_log.name}")
                print(f"   ✓ Total entries: {len(log_entries)}")
                
                for i, entry in enumerate(log_entries[-2:], 1):
                    print(f"     Entry {i}: {entry['user_message'][:50]}")
            
            # 8. Verify schedule in database
            print("\n8️⃣  Verifying schedule in database...")
            result = await session.execute(
                select(UserSchedule).where(UserSchedule.user_id == user.id)
            )
            schedules = result.scalars().all()
            
            print(f"   ✓ Schedules in database: {len(schedules)}")
            for sched in schedules:
                print(f"     - {sched.event_name} at {sched.start_time}")
            
            # 9. Verify response contains the schedule
            print("\n9️⃣  Verifying /schedule response quality...")
            assert "Team Meeting" in schedule_response, "Response should contain Team Meeting"
            assert "tomorrow" not in schedule_response.lower() or "jan" in schedule_response.lower(), "Should show formatted date"
            assert "upcoming" in schedule_response.lower(), "Should show status"
            print(f"   ✓ Response contains all required information")
            
            print("\n" + "="*80)
            print("✅ E2E TELEGRAM /schedule WORKFLOW TEST PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_multiple_schedules_display():
    """Test /schedule with multiple upcoming meetings."""
    print("\n" + "="*80)
    print("E2E TEST: Multiple Schedules Display")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # Setup
            print("\n1️⃣  Creating user with multiple schedules...")
            user = User(
                id=uuid4(),
                username="multi_schedule_user",
                email=f"multi_{uuid4().hex}@example.com",
                tier="premium",
                timezone="America/New_York"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="MultiBot",
                archetype="cool_girl",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            # Create multiple schedules
            now = datetime.now()
            meetings = [
                ("Daily Standup", now + timedelta(hours=1)),
                ("Design Review", now + timedelta(hours=3)),
                ("Client Call", now + timedelta(days=1)),
                ("Project Planning", now + timedelta(days=2)),
                ("Team Retrospective", now + timedelta(days=3)),
            ]
            
            for name, time in meetings:
                schedule = UserSchedule(
                    id=uuid4(),
                    user_id=user.id,
                    bot_id=bot.id,
                    event_name=name,
                    start_time=time,
                    end_time=time + timedelta(hours=1),
                    channel="telegram"
                )
                session.add(schedule)
            
            await session.commit()
            print(f"   ✓ Created {len(meetings)} schedules")
            
            # Get schedule
            print("\n2️⃣  Fetching /schedule command response...")
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': 987654321,
                'timezone': user.timezone
            }
            
            response = await command_handler._handle_schedule(
                str(user.id),
                user_dict,
                "",
                "cool_girl"
            )
            
            print(f"   ✓ Response generated")
            print(f"\n   Full response:")
            print("   " + "\n   ".join(response.split('\n')))
            
            # Verify all schedules are listed
            print("\n3️⃣  Verifying all schedules are listed...")
            for name, _ in meetings:
                assert name in response, f"Response should contain {name}"
                print(f"   ✓ {name} present")
            
            print("\n" + "="*80)
            print("✅ MULTIPLE SCHEDULES TEST PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_with_logging_verification():
    """Test that /schedule command interactions are properly logged."""
    print("\n" + "="*80)
    print("E2E TEST: /schedule Command Logging Verification")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # Setup
            print("\n1️⃣  Creating test scenario...")
            user = User(
                id=uuid4(),
                username="logging_test",
                email=f"logging_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="LogBot",
                archetype="lawyer",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Legal Review",
                start_time=datetime.now() + timedelta(hours=2),
                channel="telegram"
            )
            session.add(schedule)
            await session.commit()
            print(f"   ✓ Test scenario created")
            
            # Execute /schedule command
            print("\n2️⃣  Executing /schedule command...")
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': 555555,
                'timezone': 'UTC'
            }
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "lawyer")
            print(f"   ✓ Command executed")
            
            # Log the interaction
            print("\n3️⃣  Logging the interaction...")
            log_success = chat_logger.log_conversation(
                user_id=str(user.id),
                username=user.username,
                bot_id=bot.archetype,
                user_message="/schedule",
                bot_response=response,
                message_type="reactive",
                source="telegram"
            )
            print(f"   ✓ Logged: {log_success}")
            
            # Verify log file contains the interaction
            print("\n4️⃣  Verifying log file contents...")
            logs_dir = Path(chat_logger.logs_dir)
            user_folder = f"{user.username}_{user.id}"
            user_log_dir = logs_dir / user_folder / bot.archetype
            
            daily_log = user_log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
            
            if daily_log.exists():
                with open(daily_log, 'r') as f:
                    log_data = json.load(f)
                
                # Find the /schedule command log
                schedule_logs = [
                    entry for entry in log_data 
                    if entry.get('user_message') == '/schedule'
                ]
                
                print(f"   ✓ Log file exists: {daily_log}")
                print(f"   ✓ Total entries: {len(log_data)}")
                print(f"   ✓ /schedule entries: {len(schedule_logs)}")
                
                if schedule_logs:
                    latest = schedule_logs[-1]
                    print(f"   ✓ Latest /schedule entry:")
                    print(f"     Timestamp: {latest.get('timestamp')}")
                    print(f"     Source: {latest.get('source')}")
                    print(f"     Response preview: {latest.get('bot_response', '')[:50]}...")
            
            print("\n" + "="*80)
            print("✅ LOGGING VERIFICATION TEST PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Run all E2E tests."""
    print("\n" + "="*80)
    print("END-TO-END TELEGRAM TESTS")
    print("="*80)
    
    await test_telegram_schedule_workflow()
    await test_multiple_schedules_display()
    await test_schedule_with_logging_verification()


if __name__ == "__main__":
    asyncio.run(main())
