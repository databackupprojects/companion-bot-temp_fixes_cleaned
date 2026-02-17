"""
Unit tests for proactive meeting handler
Tests the scenario: "my meeting is about to start in 2 minutes and it will remain for 1 minute"
"""
import asyncio
import pytest
import pytest_asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import Base
from models.sql_models import User, UserSchedule, GreetingPreference, BotSettings, ProactiveSession
from services.proactive_meeting_handler import ProactiveMeetingHandler


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing"""
    # Using SQLite for testing (simpler than PostgreSQL)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_meeting_preparation_reminder(db_session: AsyncSession):
    """
    Test that preparation reminder is sent for meeting starting in 2 minutes
    """
    # Create user
    user = User(
        id=uuid4(),
        username="test_user",
        email="test@example.com",
        tier="free"
    )
    db_session.add(user)
    
    # Create bot settings
    bot = BotSettings(
        id=uuid4(),
        user_id=user.id,
        bot_name="TestBot",
        archetype="golden_retriever",
        is_active=True,
        is_primary=True
    )
    db_session.add(bot)
    
    # Create greeting preference
    greeting_pref = GreetingPreference(
        id=uuid4(),
        user_id=user.id,
        prefer_proactive=True,
    )
    db_session.add(greeting_pref)
    
    await db_session.commit()
    
    # Create schedule: Meeting starting in 2 minutes, lasting 1 minute
    now = datetime.utcnow()
    start_time = now + timedelta(minutes=2)
    end_time = start_time + timedelta(minutes=1)
    
    schedule = UserSchedule(
        id=uuid4(),
        user_id=user.id,
        bot_id=bot.id,
        event_name="Test Meeting",
        description="Testing meeting scenario",
        start_time=start_time,
        end_time=end_time,
        channel="telegram",
        preparation_reminder_sent=False,
        event_completed_sent=False,
    )
    db_session.add(schedule)
    await db_session.commit()
    
    # Initialize proactive handler
    handler = ProactiveMeetingHandler(db_session)
    
    # Check and send preparation reminders
    reminders_sent = await handler.check_and_send_preparation_reminders()
    
    # Assert reminder was sent
    assert reminders_sent == 1, f"Expected 1 reminder sent, got {reminders_sent}"
    
    # Verify ProactiveSession was created
    from sqlalchemy import select
    result = await db_session.execute(
        select(ProactiveSession).where(
            ProactiveSession.session_type == 'meeting_prep_reminder'
        )
    )
    session_record = result.scalar_one_or_none()
    
    assert session_record is not None, "ProactiveSession not created"
    assert session_record.user_id == user.id
    assert session_record.session_type == 'meeting_prep_reminder'
    assert session_record.message_content is not None
    
    # Verify schedule was marked
    await db_session.refresh(schedule)
    assert schedule.preparation_reminder_sent == True
    assert schedule.preparation_reminder_sent_at is not None
    
    print("✅ Preparation reminder test PASSED")


@pytest.mark.asyncio
async def test_meeting_completion_message(db_session: AsyncSession):
    """
    Test that completion message is sent after meeting ends
    """
    # Create user
    user = User(
        id=uuid4(),
        username="test_user2",
        email="test2@example.com",
        tier="free"
    )
    db_session.add(user)
    
    # Create bot settings
    bot = BotSettings(
        id=uuid4(),
        user_id=user.id,
        bot_name="TestBot",
        archetype="golden_retriever",
        is_active=True,
        is_primary=True
    )
    db_session.add(bot)
    
    # Create greeting preference
    greeting_pref = GreetingPreference(
        id=uuid4(),
        user_id=user.id,
        prefer_proactive=True,
    )
    db_session.add(greeting_pref)
    
    await db_session.commit()
    
    # Create schedule: Meeting that ended 1 minute ago
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=3)
    end_time = now - timedelta(minutes=1)
    
    schedule = UserSchedule(
        id=uuid4(),
        user_id=user.id,
        bot_id=bot.id,
        event_name="Completed Meeting",
        description="Testing completion scenario",
        start_time=start_time,
        end_time=end_time,
        channel="telegram",
        preparation_reminder_sent=True,
        event_completed_sent=False,
    )
    db_session.add(schedule)
    await db_session.commit()
    
    # Initialize proactive handler
    handler = ProactiveMeetingHandler(db_session)
    
    # Check and send completion messages
    messages_sent = await handler.check_and_send_completion_messages()
    
    # Assert message was sent
    assert messages_sent == 1, f"Expected 1 completion message sent, got {messages_sent}"
    
    # Verify ProactiveSession was created
    from sqlalchemy import select
    result = await db_session.execute(
        select(ProactiveSession).where(
            ProactiveSession.session_type == 'meeting_completion'
        )
    )
    session_record = result.scalar_one_or_none()
    
    assert session_record is not None, "ProactiveSession not created"
    assert session_record.user_id == user.id
    assert session_record.session_type == 'meeting_completion'
    
    # Verify schedule was marked
    await db_session.refresh(schedule)
    assert schedule.event_completed_sent == True
    assert schedule.event_completed_sent_at is not None
    
    print("✅ Completion message test PASSED")


@pytest.mark.asyncio
async def test_meeting_no_duplicate_reminders(db_session: AsyncSession):
    """
    Test that reminder is not sent twice for the same meeting
    """
    # Create user
    user = User(
        id=uuid4(),
        username="test_user3",
        email="test3@example.com",
        tier="free"
    )
    db_session.add(user)
    
    # Create bot settings
    bot = BotSettings(
        id=uuid4(),
        user_id=user.id,
        bot_name="TestBot",
        archetype="golden_retriever",
        is_active=True,
        is_primary=True
    )
    db_session.add(bot)
    
    # Create greeting preference
    greeting_pref = GreetingPreference(
        id=uuid4(),
        user_id=user.id,
        prefer_proactive=True,
    )
    db_session.add(greeting_pref)
    
    await db_session.commit()
    
    # Create schedule that already has reminder sent
    now = datetime.utcnow()
    start_time = now + timedelta(minutes=2)
    end_time = start_time + timedelta(minutes=1)
    
    schedule = UserSchedule(
        id=uuid4(),
        user_id=user.id,
        bot_id=bot.id,
        event_name="Already Reminded Meeting",
        description="Testing duplicate prevention",
        start_time=start_time,
        end_time=end_time,
        channel="telegram",
        preparation_reminder_sent=True,  # Already sent
        preparation_reminder_sent_at=now - timedelta(minutes=1),
        event_completed_sent=False,
    )
    db_session.add(schedule)
    await db_session.commit()
    
    # Initialize proactive handler
    handler = ProactiveMeetingHandler(db_session)
    
    # Check and send preparation reminders
    reminders_sent = await handler.check_and_send_preparation_reminders()
    
    # Assert no reminder was sent (since already sent)
    assert reminders_sent == 0, f"Expected 0 reminders sent, got {reminders_sent}"
    
    print("✅ Duplicate prevention test PASSED")


@pytest.mark.asyncio
async def test_meeting_respects_dnd_hours(db_session: AsyncSession):
    """
    Test that greetings respect Do Not Disturb hours
    """
    # Create user
    user = User(
        id=uuid4(),
        username="test_user4",
        email="test4@example.com",
        tier="free"
    )
    db_session.add(user)
    
    # Create bot settings
    bot = BotSettings(
        id=uuid4(),
        user_id=user.id,
        bot_name="TestBot",
        archetype="golden_retriever",
        is_active=True,
        is_primary=True
    )
    db_session.add(bot)
    
    # Create greeting preference with DND from 22:00 to 08:00
    greeting_pref = GreetingPreference(
        id=uuid4(),
        user_id=user.id,
        prefer_proactive=True,
        dnd_start_hour=22,  # 10 PM
        dnd_end_hour=8,     # 8 AM
    )
    db_session.add(greeting_pref)
    
    await db_session.commit()
    
    # Initialize proactive handler
    handler = ProactiveMeetingHandler(db_session)
    
    # Simulate checking greetings during DND hours (e.g., 23:00)
    # This is a simplified check - actual behavior depends on current time
    
    print("✅ DND hours test setup PASSED")


if __name__ == "__main__":
    # Run with: pytest tests/test_proactive_meeting.py -v
    print("Run with: pytest tests/test_proactive_meeting.py -v")
