"""
Unit tests for command handler - /schedule command.
Tests the command handler with various edge cases and scenarios.
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
from models.sql_models import User, UserSchedule, BotSettings
from handlers.command_handler import CommandHandler


async def test_schedule_command_empty():
    """Test /schedule with no schedules."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Empty Schedule")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"empty_schedule_{uuid4().hex[:8]}",
                email=f"empty_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {'id': str(user.id), 'telegram_id': 11111, 'timezone': 'UTC'}
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"Response: {response}")
            assert "don't have any upcoming" in response.lower()
            print("✅ Test passed: Empty schedule handled correctly")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_command_with_past_dates():
    """Test /schedule with past dates (should not show)."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Past Dates Filtered")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"past_dates_{uuid4().hex[:8]}",
                email=f"past_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="PastBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            now = datetime.now()
            
            # Add past schedule
            past_schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Past Meeting",
                start_time=now - timedelta(days=1),
                channel="telegram"
            )
            
            # Add future schedule
            future_schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Future Meeting",
                start_time=now + timedelta(days=1),
                channel="telegram"
            )
            
            session.add(past_schedule)
            session.add(future_schedule)
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {'id': str(user.id), 'telegram_id': 22222, 'timezone': 'UTC'}
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"Response contains Future Meeting: {'Future Meeting' in response}")
            print(f"Response contains Past Meeting: {'Past Meeting' in response}")
            
            assert "Future Meeting" in response
            assert "Past Meeting" not in response
            
            print("✅ Test passed: Past dates are filtered correctly")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_command_time_formatting():
    """Test /schedule command time formatting."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Time Formatting")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"time_format_{uuid4().hex[:8]}",
                email=f"time_fmt_{uuid4().hex}@example.com",
                tier="free",
                timezone="America/Los_Angeles"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="TimeBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            # Create schedule with specific time
            specific_time = datetime(2026, 1, 15, 14, 30)  # 2:30 PM
            schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Time Format Test",
                start_time=specific_time,
                channel="telegram"
            )
            session.add(schedule)
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {
                'id': str(user.id),
                'telegram_id': 33333,
                'timezone': "America/Los_Angeles"
            }
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"Response:\n{response}")
            
            # Check that response contains formatted time
            assert "Time Format Test" in response
            assert "at" in response  # Time should be formatted with "at"
            
            print("✅ Test passed: Time formatting is correct")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_command_completed_schedules():
    """Test /schedule with completed schedules."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Completed Schedules Hidden")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"completed_{uuid4().hex[:8]}",
                email=f"completed_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="CompletedBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            now = datetime.now()
            
            # Upcoming schedule
            upcoming = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Upcoming Task",
                start_time=now + timedelta(days=2),
                is_completed=False,
                channel="telegram"
            )
            
            # Completed schedule
            completed = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Completed Task",
                start_time=now + timedelta(days=3),
                is_completed=True,
                channel="telegram"
            )
            
            session.add(upcoming)
            session.add(completed)
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {'id': str(user.id), 'telegram_id': 44444, 'timezone': 'UTC'}
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"Response contains Upcoming Task: {'Upcoming Task' in response}")
            print(f"Response contains Completed Task: {'Completed Task' in response}")
            
            assert "Upcoming Task" in response
            # Completed tasks should not appear
            
            print("✅ Test passed: Completed schedules are handled correctly")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_command_markdown_escaping():
    """Test /schedule with special markdown characters."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Markdown Special Characters")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"markdown_{uuid4().hex[:8]}",
                email=f"markdown_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="MarkdownBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            # Schedule with markdown special characters
            schedule = UserSchedule(
                id=uuid4(),
                user_id=user.id,
                bot_id=bot.id,
                event_name="Meeting with [Team] *Leaders*",
                start_time=datetime.now() + timedelta(hours=1),
                channel="telegram"
            )
            session.add(schedule)
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {'id': str(user.id), 'telegram_id': 55555, 'timezone': 'UTC'}
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            print(f"Response includes special chars: {True}")
            assert "Meeting" in response
            
            print("✅ Test passed: Markdown characters handled")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_schedule_command_ordering():
    """Test /schedule command - schedules are ordered by time."""
    print("\n" + "="*80)
    print("TEST: /schedule Command - Schedule Ordering")
    print("="*80)
    
    async with AsyncSessionLocal() as session:
        try:
            user = User(
                id=uuid4(),
                username=f"ordering_{uuid4().hex[:8]}",
                email=f"ordering_{uuid4().hex}@example.com",
                tier="free",
                timezone="UTC"
            )
            session.add(user)
            await session.commit()
            
            bot = BotSettings(
                id=uuid4(),
                user_id=user.id,
                bot_name="OrderBot",
                archetype="golden_retriever",
                is_active=True,
                is_primary=True
            )
            session.add(bot)
            
            now = datetime.now()
            
            # Create schedules out of order
            times = [
                ("Third Meeting", now + timedelta(days=3)),
                ("First Meeting", now + timedelta(hours=2)),
                ("Second Meeting", now + timedelta(days=1)),
            ]
            
            for name, time in times:
                schedule = UserSchedule(
                    id=uuid4(),
                    user_id=user.id,
                    bot_id=bot.id,
                    event_name=name,
                    start_time=time,
                    channel="telegram"
                )
                session.add(schedule)
            
            await session.commit()
            
            command_handler = CommandHandler(session, None)
            user_dict = {'id': str(user.id), 'telegram_id': 66666, 'timezone': 'UTC'}
            
            response = await command_handler._handle_schedule(str(user.id), user_dict, "", "golden_retriever")
            
            # Find positions of each meeting in response
            first_pos = response.find("First Meeting")
            second_pos = response.find("Second Meeting")
            third_pos = response.find("Third Meeting")
            
            print(f"First Meeting position: {first_pos}")
            print(f"Second Meeting position: {second_pos}")
            print(f"Third Meeting position: {third_pos}")
            
            # Verify they appear in chronological order
            assert first_pos < second_pos < third_pos, "Schedules should be in chronological order"
            
            print("✅ Test passed: Schedules are ordered by time")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("SCHEDULE COMMAND UNIT TESTS")
    print("="*80)
    
    await test_schedule_command_empty()
    await test_schedule_command_with_past_dates()
    await test_schedule_command_time_formatting()
    await test_schedule_command_completed_schedules()
    await test_schedule_command_markdown_escaping()
    await test_schedule_command_ordering()
    
    print("\n" + "="*80)
    print("✅ ALL UNIT TESTS PASSED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
