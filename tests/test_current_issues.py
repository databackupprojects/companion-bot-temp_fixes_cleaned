#!/usr/bin/env python3
"""
Test script to verify current issues:
1. Bot not showing in "My Bots" tab
2. /schedule command not returning data
3. Proactive messages not being sent
4. Chat logging not working
"""

import asyncio
import sys
sys.path.insert(0, '/home/abubakar/companion-bot/backend')

from database import AsyncSessionLocal, init_db
from sqlalchemy import select
from models.sql_models import User, BotSettings, QuizConfig, UserSchedule, Message
from datetime import datetime, timedelta
import json


async def test_bot_creation():
    """Test if bot creation from quiz is working"""
    print("\n" + "="*60)
    print("TEST 1: Bot Creation & My Bots Tab")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        # Get all users with quiz configs
        users = await session.execute(select(User).limit(3))
        users_list = users.scalars().all()
        
        for user in users_list:
            print(f"\nUser: {user.username} ({user.id})")
            
            # Get their bot settings
            bot_settings_stmt = select(BotSettings).where(BotSettings.user_id == user.id)
            bot_result = await session.execute(bot_settings_stmt)
            bot_settings = bot_result.scalars().all()
            print(f"  BotSettings in database: {len(bot_settings)}")
            for bot in bot_settings:
                print(f"    - {bot.bot_name} ({bot.archetype}) - quiz_token: {bot.quiz_token}")
            
            # Get their quiz configs
            quiz_stmt = select(QuizConfig).where(QuizConfig.user_id == user.id)
            quiz_result = await session.execute(quiz_stmt)
            quiz_configs = quiz_result.scalars().all()
            print(f"  QuizConfigs: {len(quiz_configs)}")
            for quiz in quiz_configs:
                config_data = quiz.config_data if isinstance(quiz.config_data, dict) else {}
                used_status = "✓ USED" if quiz.used_at else "❌ NOT USED"
                print(f"    - {config_data.get('bot_name')} ({config_data.get('archetype')}) - {used_status}")
                print(f"      Token: {quiz.token[:10]}...")
                print(f"      Expires: {quiz.expires_at}")
                print(f"      Used at: {quiz.used_at}")


async def test_schedule_command():
    """Test if /schedule has data to return"""
    print("\n" + "="*60)
    print("TEST 2: /schedule Command Data")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        # Get all users with schedules
        schedules = await session.execute(select(UserSchedule))
        all_schedules = schedules.scalars().all()
        
        print(f"\nTotal schedules in database: {len(all_schedules)}")
        
        # Group by user
        from collections import defaultdict
        user_schedules = defaultdict(list)
        
        for schedule in all_schedules:
            user_schedules[schedule.user_id].append(schedule)
        
        for user_id, scheds in list(user_schedules.items())[:3]:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            print(f"\nUser: {user.username if user else 'Unknown'} ({user_id})")
            print(f"  Schedules: {len(scheds)}")
            
            # Check upcoming schedules
            now = datetime.now()
            upcoming = [s for s in scheds if s.start_time >= now and not s.is_completed]
            print(f"  Upcoming (7 days): {len(upcoming)}")
            
            for sched in upcoming[:3]:
                print(f"    - {sched.title} at {sched.start_time}")


async def test_proactive_messages():
    """Test if proactive messages are being sent"""
    print("\n" + "="*60)
    print("TEST 3: Proactive Messages")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        # Check for recent proactive logs
        from models.sql_models import ProactiveLog
        
        logs = await session.execute(
            select(ProactiveLog)
            .order_by(ProactiveLog.created_at.desc())
            .limit(10)
        )
        proactive_logs = logs.scalars().all()
        
        print(f"\nRecent proactive messages: {len(proactive_logs)}")
        for log in proactive_logs:
            print(f"  - {log.message_type}: {log.created_at}")


async def test_chat_logging():
    """Test if chat logging is working"""
    print("\n" + "="*60)
    print("TEST 4: Chat Logging")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        # Check messages
        messages = await session.execute(
            select(Message)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        recent_messages = messages.scalars().all()
        
        print(f"\nRecent messages: {len(recent_messages)}")
        for msg in recent_messages:
            user_stmt = select(User).where(User.id == msg.user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            print(f"  - {user.username if user else 'Unknown'}: '{msg.user_message[:30]}...'")
            
            # Check if chat logs exist
            import os
            user_id = str(msg.user_id)
            telegram_id = user.telegram_id if user else None
            
            if user and user.telegram_id:
                log_dir = f"/home/abubakar/companion-bot/logs/chats/{user.username}_{user.telegram_id}"
                exists = os.path.exists(log_dir)
                print(f"    Log dir exists: {exists} ({log_dir})")


async def main():
    """Run all tests"""
    print("\n🔍 DIAGNOSING CURRENT ISSUES\n")
    
    try:
        # Initialize database
        await init_db()
        
        await test_bot_creation()
        await test_schedule_command()
        await test_proactive_messages()
        await test_chat_logging()
        
        print("\n" + "="*60)
        print("DIAGNOSIS COMPLETE")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
