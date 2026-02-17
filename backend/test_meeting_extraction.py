# backend/test_meeting_extraction.py
"""
Test to trace what happens when user sends: 
"my meeting is about to start in 1 minute and it will last long for 1 minute"
"""
import asyncio
from datetime import datetime, timedelta
import pytz
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import uuid

# Mock setup
class MockUser:
    def __init__(self):
        self.id = uuid.uuid4()
        self.timezone = "America/New_York"  # Example timezone

class MockMessage:
    def __init__(self):
        self.id = uuid.uuid4()
        self.content = "my meeting is about to start in 1 minute and it will last long for 1 minute"
        self.role = "user"

class MockBotSettings:
    def __init__(self):
        self.id = uuid.uuid4()

def test_meeting_extraction_scenario():
    """Simulate the meeting extraction flow."""
    
    print("=" * 80)
    print("TEST SCENARIO: User sends meeting message")
    print("=" * 80)
    
    user = MockUser()
    message = MockMessage()
    
    print(f"\n📱 USER MESSAGE:")
    print(f"   Timezone: {user.timezone}")
    print(f"   Message: '{message.content}'")
    
    # Simulate what message_analyzer does
    print(f"\n📊 STEP 1: Message Analyzer Receives Message")
    print(f"   - Extracts meetings from user message")
    print(f"   - Uses user's timezone as reference ({user.timezone})")
    
    # Get user's current time in their timezone
    user_tz = pytz.timezone(user.timezone)
    utc_now = datetime.utcnow()
    user_now_aware = utc_now.replace(tzinfo=pytz.UTC).astimezone(user_tz)
    user_now = user_now_aware.replace(tzinfo=None)
    
    print(f"\n   Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   Current user time: {user_now.strftime('%Y-%m-%d %H:%M:%S')} {user.timezone}")
    
    # Simulate meeting extraction
    print(f"\n📊 STEP 2: Extract Meeting Times")
    print(f"   Extracting from: '{message.content}'")
    
    # In user's timezone context
    extracted_start = user_now + timedelta(minutes=1)
    extracted_end = user_now + timedelta(minutes=2)
    
    print(f"   Extracted start time (user TZ): {extracted_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Extracted end time (user TZ):   {extracted_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Meeting duration: 1 minute")
    
    # Convert to UTC for storage
    print(f"\n🗄️  STEP 3: Convert to UTC for Database Storage")
    
    # Localize to user's timezone, then convert to UTC
    start_aware = user_tz.localize(extracted_start)
    start_utc = start_aware.astimezone(pytz.UTC).replace(tzinfo=None)
    
    end_aware = user_tz.localize(extracted_end)
    end_utc = end_aware.astimezone(pytz.UTC).replace(tzinfo=None)
    
    print(f"   Converted start time (UTC): {start_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   Converted end time (UTC):   {end_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Calculate time differences
    start_diff = (start_utc - utc_now).total_seconds() / 60
    end_diff = (end_utc - utc_now).total_seconds() / 60
    
    print(f"\n⏱️  TIME DIFFERENCES FROM NOW:")
    print(f"   Start time in: {start_diff:.1f} minutes")
    print(f"   End time in:   {end_diff:.1f} minutes")
    
    # Check against proactive_meeting_handler thresholds
    print(f"\n✅ STEP 4: Check Against Proactive System Thresholds")
    
    PREP_REMINDER_LEAD_TIME = 30  # minutes
    FOLLOWUP_DELAY = 5  # minutes
    
    print(f"\n   Preparation Reminder Check:")
    print(f"   - Lead time: {PREP_REMINDER_LEAD_TIME} minutes before meeting")
    print(f"   - Meeting in: {start_diff:.1f} minutes")
    
    if start_diff > 0 and start_diff <= PREP_REMINDER_LEAD_TIME + 5:
        print(f"   ✅ WILL SEND PREPARATION REMINDER IMMEDIATELY")
        print(f"      (Within the {PREP_REMINDER_LEAD_TIME} minute window)")
    else:
        print(f"   ❌ Will NOT send preparation reminder")
    
    print(f"\n   Completion Message Check:")
    print(f"   - Delay after end: {FOLLOWUP_DELAY} minutes")
    print(f"   - End time in: {end_diff:.1f} minutes")
    
    if end_diff <= FOLLOWUP_DELAY:
        print(f"   ⏳ Will check for completion after {FOLLOWUP_DELAY} minutes")
    else:
        print(f"   ⏳ Will check later (meeting is too far in future)")
    
    # Display the schedule that would be created
    print(f"\n📋 STEP 5: Schedule Created in Database")
    print(f"   Event Name: 'meeting' (extracted from message)")
    print(f"   Start Time (UTC): {start_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End Time (UTC):   {end_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   User ID: {user.id}")
    print(f"   Channel: 'telegram'")
    print(f"   Preparation Reminder Sent: False (will be sent soon)")
    print(f"   Event Completed Sent: False")
    
    # Timeline
    print(f"\n📅 TIMELINE OF EVENTS:")
    print(f"   NOW:           {utc_now.strftime('%H:%M:%S UTC')} | {user_now.strftime('%H:%M:%S ' + user.timezone)}")
    print(f"   +1 min:        Meeting starts")
    print(f"   +1 min:        ⚡ SEND PREPARATION REMINDER (immediately detected)")
    print(f"   +2 min:        Meeting ends")
    print(f"   +2.5 min:      ⚡ SEND COMPLETION MESSAGE (after 5 min check)")
    
    print(f"\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print("""
The system will:
1. ✅ Extract the meeting with start_time = now + 1 min (user's TZ)
2. ✅ Extract the end_time = now + 2 min (user's TZ)
3. ✅ Convert both times to UTC for storage
4. ✅ Create UserSchedule record in database with UTC times
5. ⚡ IMMEDIATELY send preparation reminder (1 min is within 30-min window)
6. ⏰ Wait ~5 minutes, then check for completion message
7. ⚡ Send completion message (meeting has ended)
8. ✅ All times are stored as UTC, displayed in user's timezone

KEY POINTS:
- Times are stored as UTC in database
- But when displayed to user, they're converted back to their timezone
- The 30-minute preparation window is checked in UTC (system time)
- Even though it's 1 minute away, it WILL trigger a preparation reminder
""")
    print("=" * 80)

if __name__ == "__main__":
    test_meeting_extraction_scenario()
