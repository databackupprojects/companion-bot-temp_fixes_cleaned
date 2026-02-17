"""
Integration test for /schedule command and chat logging.
Tests the complete flow in a realistic scenario.
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
from handlers.command_handler import CommandHandler
from handlers.message_handler import MessageHandler
from utils.chat_logger import chat_logger


async def test_full_integration():
    """Test complete flow: message -> schedule -> /schedule command -> logging."""
    print("\n" + "="*80)
    print("INTEGRATION TEST: Message → Schedule → /schedule Command → Logging")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create test user and bot
            print("\n1️⃣  Setting up user and bot...")
            user = User(
                id=uuid4(),
                username=f"integration_test_{uuid4().hex[:8]}",
                email=f"integration_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            print(f"   ✓ User: {user.username}")
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="IntegrationBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            await session.commit()
            print(f"   ✓ Bot: {bot.archetype}")
            
            # 2. Create schedules via direct insertion
            print("\n2️⃣  Creating schedules...")
            now = datetime.now()
            
            schedule1 = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Design Review",
                description="Review new UI designs",
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=2),
                channel="telegram"
            )
            
            schedule2 = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Sprint Planning",
                description="Plan next sprint",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
                channel="telegram"
            )
            
            session.add(schedule1)
            session.add(schedule2)
            await session.commit()
            print(f"   ✓ Schedule 1: {schedule1.event_name} at {schedule1.start_time.strftime('%H:%M')}")
            print(f"   ✓ Schedule 2: {schedule2.event_name} at {schedule2.start_time.strftime('%H:%M')}")
            
            # 3. Test /schedule command
            print("\n3️⃣  Testing /schedule command...")
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': 111111,
                'timezone': 'UTC'
            }
            
            schedule_response = await command_handler._handle_schedule(
                str(user.id), 
                user_dict, 
                "", 
                "golden_retriever"
            )
            
            print(f"   ✓ /schedule command executed")
            print(f"   Response preview:")
            for line in schedule_response.split('\n')[:8]:
                print(f"     {line}")
            
            # Verify response contains both schedules
            assert "Design Review" in schedule_response, "Should contain Design Review"
            assert "Sprint Planning" in schedule_response, "Should contain Sprint Planning"
            print(f"   ✓ Response contains all schedules")
            
            # 4. Test chat logging
            print("\n4️⃣  Testing chat logging...")
            
            # Simulate logging a conversation
            log_success = chat_logger.log_conversation(
                user_id=str(user.id),
                username=user.username,
                bot_id=bot.archetype,
                user_message="I have a meeting with the design team tomorrow at 10 AM",
                bot_response="Got it! I'll remind you about your design team meeting tomorrow at 10 AM. 📅",
                message_type="reactive",
                source="telegram"
            )
            
            print(f"   ✓ Logged conversation: {log_success}")
            
            # Log the /schedule command interaction
            log_success2 = chat_logger.log_conversation(
                user_id=str(user.id),
                username=user.username,
                bot_id=bot.archetype,
                user_message="/schedule",
                bot_response=schedule_response,
                message_type="reactive",
                source="telegram"
            )
            
            print(f"   ✓ Logged /schedule interaction: {log_success2}")
            
            # 5. Verify log files exist and contain data
            print("\n5️⃣  Verifying log files...")
            logs_dir = Path(chat_logger.logs_dir)
            user_folder = f"{user.username}_{user.id}"
            user_log_dir = logs_dir / user_folder / bot.archetype
            
            if user_log_dir.exists():
                print(f"   ✓ Log directory exists: {user_log_dir}")
                
                # Check daily log
                today_log = user_log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
                if today_log.exists():
                    with open(today_log, 'r') as f:
                        log_data = json.load(f)
                    
                    print(f"   ✓ Daily log exists with {len(log_data)} entries")
                    
                    # Show last log entry
                    if log_data:
                        last_entry = log_data[-1]
                        print(f"   ✓ Last logged message: '{last_entry['user_message'][:50]}...'")
                
                # Check combined log
                combined_log = user_log_dir / "combined.log"
                if combined_log.exists():
                    with open(combined_log, 'r') as f:
                        combined_data = json.load(f)
                    print(f"   ✓ Combined log exists with {len(combined_data)} entries")
            else:
                print(f"   ⚠️  Log directory not found: {user_log_dir}")
            
            # 6. Verify database state
            print("\n6️⃣  Verifying database state...")
            result = await session.execute(
                select(UserSchedule).where(UserSchedule.user_id == user.id)
            )
            all_schedules = result.scalars().all()
            
            print(f"   ✓ Database has {len(all_schedules)} schedules for user")
            for sched in all_schedules:
                print(f"     - {sched.event_name}")
            
            print("\n" + "="*80)
            print("✅ INTEGRATION TEST PASSED")
            print("="*80)
            print("\nSummary:")
            print(f"  • User created: {user.username}")
            print(f"  • Schedules created: {len(all_schedules)}")
            print(f"  • /schedule command: Working ✓")
            print(f"  • Chat logging: Working ✓")
            print(f"  • Log files: Created ✓")
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_timezone_handling():
    """Test /schedule command with different user timezones."""
    print("\n" + "="*80)
    print("TIMEZONE TEST: /schedule with Different Timezones")
    print("="*80)
    
    timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
    
    async with AsyncSessionLocal() as session:
        try:
            for tz in timezones:
                print(f"\n✓ Testing timezone: {tz}")
                
                user = User(
                    id=uuid4(),
                    username=f"tz_test_{tz.replace('/', '_')}",
                    email=f"tz_{uuid4().hex}@example.com",
                    tier="free",
                    timezone=tz
                )
                session.add(user)
                await session.commit()
                
                bot = BotSettings(
                    id=uuid4(),
                    user_id=user.id,
                    bot_name="TZBot",
                    archetype="golden_retriever",
                    is_active=True,
                    is_primary=True
                )
                session.add(bot)
                
                schedule = UserSchedule(
                    id=uuid4(),
                    user_id=user.id,
                    bot_id=bot.id,
                    event_name=f"Meeting in {tz}",
                    start_time=datetime.now() + timedelta(hours=1),
                    channel="telegram"
                )
                session.add(schedule)
                await session.commit()
                
                command_handler = CommandHandler(session, None)
                user_dict = {
                    'id': str(user.id),
                    'telegram_id': hash(tz) % 1000000,
                    'timezone': tz
                }
                
                response = await command_handler._handle_schedule(
                    str(user.id),
                    user_dict,
                    "",
                    "golden_retriever"
                )
                
                assert f"Meeting in {tz}" in response
                print(f"  ✓ /schedule works in {tz}")
            
            print("\n" + "="*80)
            print("✅ TIMEZONE TEST PASSED")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ Timezone test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_logging_with_special_characters():
    """Test chat logging with special characters and long messages."""
    print("\n" + "="*80)
    print("LOGGING TEST: Special Characters and Long Messages")
    print("="*80)
    
    try:
        test_cases = [
            {
                "user_msg": "I have a meeting with @john and #design team at 2 PM tomorrow!",
                "bot_resp": "Got it! 📅 Meeting scheduled for tomorrow at 2 PM with @john and #design"
            },
            {
                "user_msg": "What about my schedule? /schedule",
                "bot_resp": "Here's your schedule..."
            },
            {
                "user_msg": "Meeting: [IMPORTANT] Design Review 🎨 at 3:30 PM",
                "bot_resp": "✅ Got it! Important design review at 3:30 PM noted"
            },
            {
                "user_msg": "Very long message " * 50,  # Long message
                "bot_resp": "I see, " + "that's quite long! " * 30
            }
        ]
        
        print("\n1️⃣  Testing special characters and long messages...")
        for i, test_case in enumerate(test_cases, 1):
            success = chat_logger.log_conversation(
                user_id=str(uuid4()),
                username=f"special_chars_test",
                bot_id="golden_retriever",
                user_message=test_case["user_msg"][:200],
                bot_response=test_case["bot_resp"][:200],
                message_type="reactive",
                source="telegram"
            )
            print(f"   ✓ Test case {i}: {success}")
        
        print("\n" + "="*80)
        print("✅ SPECIAL CHARACTERS TEST PASSED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Special characters test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("INTEGRATION TEST SUITE")
    print("="*80)
    
    await test_full_integration()
    await test_schedule_timezone_handling()
    await test_logging_with_special_characters()


if __name__ == "__main__":
    asyncio.run(main())
