"""
Test suite for Telegram /schedule command and chat logging.
Tests the complete flow of schedule creation, retrieval, and logging.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import select
from database import AsyncSessionLocal
from models.sql_models import User, UserSchedule, BotSettings, Message
from handlers.command_handler import CommandHandler
from utils.chat_logger import chat_logger
from services.message_analyzer import MessageAnalyzer


async def test_schedule_command():
    """Test /schedule command with various schedule scenarios."""
    print("\n" + "="*80)
    print("TEST: /schedule Command Functionality")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Setup test user and bot
            print("\n1️⃣  Setting up test user and bot...")
            result = await session.execute(
                select(User).where(User.email == "test_schedule_cmd@example.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    id=uuid4(),
                    username=f"test_schedule_{uuid4().hex[:8]}",
                    email="test_schedule_cmd@example.com",
                    tier="free",
                    timezone="UTC"
                )
                session.add(user)
                await session.commit()
                print(f"   ✓ New user created: {user.id}")
            else:
                print(f"   ✓ Using existing user: {user.id}")
            
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
            
            # 2. Create multiple schedules for testing
            print("\n2️⃣  Creating test schedules...")
            now = datetime.now()
            
            schedules_to_create = [
                {
                    "name": "Team Standup",
                    "start": now + timedelta(hours=1),
                    "end": now + timedelta(hours=1, minutes=30)
                },
                {
                    "name": "Project Review",
                    "start": now + timedelta(days=1, hours=2),
                    "end": now + timedelta(days=1, hours=3)
                },
                {
                    "name": "Client Call",
                    "start": now + timedelta(days=3),
                    "end": now + timedelta(days=3, hours=1)
                },
            ]
            
            created_schedules = []
            for schedule_info in schedules_to_create:
                schedule = UserSchedule(
                    id=uuid4(),
                    user_id=user.id,
                    bot_id=bot.id,
                    event_name=schedule_info["name"],
                    start_time=schedule_info["start"],
                    end_time=schedule_info["end"],
                    channel="telegram",
                    is_completed=False
                )
                session.add(schedule)
                created_schedules.append(schedule)
                print(f"   ✓ Created: {schedule_info['name']} at {schedule_info['start'].strftime('%Y-%m-%d %H:%M')}")
            
            await session.commit()
            
            # 3. Test /schedule command handler
            print("\n3️⃣  Testing /schedule command handler...")
            command_handler = CommandHandler(session, None)
            
            user_dict = {
                'id': str(user.id),
                'telegram_id': 12345,
                'timezone': 'UTC'
            }
            
            # Fix: Use naive datetime for comparison
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"   ✓ Command response:")
            for line in response.split('\n'):
                print(f"     {line}")
            
            # 4. Verify response contains schedules
            print("\n4️⃣  Verifying command output...")
            assert "upcoming schedule" in response.lower() or "team standup" in response.lower(), "Response should contain schedule info"
            assert "Team Standup" in response, "Response should include Team Standup"
            print(f"   ✓ Response contains schedule information")
            
            # 5. Test with no schedules (completed user)
            print("\n5️⃣  Testing /schedule with completed events...")
            result = await session.execute(
                select(User).where(User.email == "test_completed@example.com")
            )
            completed_user = result.scalar_one_or_none()
            
            if not completed_user:
                completed_user = User(
                    id=uuid4(),
                    username=f"test_completed_{uuid4().hex[:8]}",
                    email="test_completed@example.com",
                    tier="free",
                    timezone="UTC"
                )
                session.add(completed_user)
                await session.commit()
            
            completed_user_dict = {
                'id': str(completed_user.id),
                'telegram_id': 54321,
                'timezone': 'UTC'
            }
            
            response_no_schedules = await command_handler._handle_schedule(
                str(completed_user.id), 
                completed_user_dict, 
                "", 
                "golden_retriever"
            )
            
            print(f"   ✓ No schedules response: {response_no_schedules}")
            assert "don't have any upcoming" in response_no_schedules.lower(), "Should indicate no upcoming events"
            
            # 6. Test database query directly
            print("\n6️⃣  Testing direct database query...")
            result = await session.execute(
                select(UserSchedule).where(
                    (UserSchedule.user_id == user.id) &
                    (UserSchedule.is_completed == False)
                ).order_by(UserSchedule.start_time)
            )
            db_schedules = result.scalars().all()
            
            print(f"   ✓ Found {len(db_schedules)} upcoming schedules in database")
            for sched in db_schedules:
                print(f"     - {sched.event_name} at {sched.start_time}")
            
            assert len(db_schedules) >= 3, "Should have at least 3 schedules"
            
            print("\n" + "="*80)
            print("✅ ALL /schedule COMMAND TESTS PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_chat_logging():
    """Test chat logging functionality."""
    print("\n" + "="*80)
    print("TEST: Chat Logging Functionality")
    print("="*80)
    
    try:
        # 1. Check if chat logging is enabled
        print("\n1️⃣  Checking chat logging status...")
        is_enabled = chat_logger.enabled
        print(f"   Chat logging enabled: {is_enabled}")
        
        if not is_enabled:
            print("   ⚠️  Chat logging is disabled in settings")
            print("   To enable: set enable_chat_logging=True in .env")
            return
        
        # 2. Log a test conversation
        print("\n2️⃣  Logging test conversation...")
        test_user_id = str(uuid4())
        test_username = "test_user_logging"
        test_bot_id = "golden_retriever"
        
        success = chat_logger.log_conversation(
            user_id=test_user_id,
            username=test_username,
            bot_id=test_bot_id,
            user_message="Hello, this is a test message",
            bot_response="This is a test response from the bot",
            message_type="reactive",
            source="telegram"
        )
        
        print(f"   ✓ Logged: {success}")
        
        if not success and not chat_logger.enabled:
            print("   ℹ️  Chat logging is disabled in settings")
            return
        
        # 3. Verify log file was created
        print("\n3️⃣  Verifying log files...")
        logs_dir = Path(chat_logger.logs_dir)
        
        if logs_dir.exists():
            user_folder = f"{test_username}_{test_user_id}"
            user_path = logs_dir / user_folder
            
            print(f"   Logs directory: {logs_dir}")
            print(f"   User folder: {user_path}")
            
            if user_path.exists():
                print(f"   ✓ User folder created")
                
                # Check for log files
                log_files = list(user_path.glob("**/*.log"))
                print(f"   ✓ Found {len(log_files)} log file(s)")
                
                for log_file in log_files:
                    print(f"     - {log_file.name} ({log_file.stat().st_size} bytes)")
            else:
                print(f"   ⚠️  User folder not found")
        else:
            print(f"   ⚠️  Logs directory not found: {logs_dir}")
        
        # 4. Test multiple log entries
        print("\n4️⃣  Testing multiple log entries...")
        for i in range(3):
            success = chat_logger.log_conversation(
                user_id=test_user_id,
                username=test_username,
                bot_id=test_bot_id,
                user_message=f"Test message {i+1}",
                bot_response=f"Bot response {i+1}",
                message_type="reactive",
                source="telegram"
            )
            print(f"   ✓ Entry {i+1} logged: {success}")
        
        print("\n" + "="*80)
        print("✅ CHAT LOGGING TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Chat logging test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_schedule_command_with_naive_datetime():
    """Test that /schedule command works with naive datetimes."""
    print("\n" + "="*80)
    print("TEST: /schedule Command with Naive DateTime Fix")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create test user
            print("\n1️⃣  Creating test user...")
            user = User(
                id=uuid4(),
                username=f"test_naive_{uuid4().hex[:8]}",
                email=f"test_naive_{uuid4().hex}@example.com",
                tier="free",
                timezone="America/New_York"
            )
            session.add(user)
            await session.commit()
            print(f"   ✓ User created with timezone: {user.timezone}")
            
            # 2. Create bot
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
            print(f"   ✓ Bot created")
            
            # 3. Create schedule with naive datetime
            print("\n2️⃣  Creating schedule with naive datetime...")
            now = datetime.now()
            schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Timezone Test Meeting",
                start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=3),
                channel="telegram"
            )
            session.add(schedule)
            await session.commit()
            print(f"   ✓ Schedule created with naive datetime")
            print(f"     Start time: {schedule.start_time}")
            print(f"     Type: {type(schedule.start_time)}")
            
            # 4. Query with naive datetime (like /schedule command does)
            print("\n3️⃣  Querying schedules with naive datetime...")
            # This is what the /schedule command should do
            query_now = datetime.now()
            query_week = query_now + timedelta(days=7)
            
            result = await session.execute(
                select(UserSchedule).where(
                    (UserSchedule.user_id == user.id) &
                    (UserSchedule.start_time >= query_now) &
                    (UserSchedule.start_time <= query_week) &
                    (UserSchedule.is_completed == False)
                ).order_by(UserSchedule.start_time)
            )
            schedules = result.scalars().all()
            
            print(f"   ✓ Query successful")
            print(f"   ✓ Found {len(schedules)} schedule(s)")
            
            assert len(schedules) >= 1, "Should find the created schedule"
            
            # 5. Test command handler
            print("\n4️⃣  Testing /schedule command handler...")
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': 99999,
                'timezone': user.timezone
            }
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"   ✓ Command executed successfully")
            print(f"   Response preview: {response[:100]}...")
            
            assert "Timezone Test Meeting" in response, "Response should contain the meeting name"
            
            print("\n" + "="*80)
            print("✅ NAIVE DATETIME TEST PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TELEGRAM COMMAND & LOGGING TEST SUITE")
    print("="*80)
    
    await test_schedule_command()
    await test_schedule_command_with_naive_datetime()
    await test_chat_logging()


if __name__ == "__main__":
    asyncio.run(main())
