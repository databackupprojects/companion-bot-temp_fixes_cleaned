# Proactive Features - Quick Reference Guide

## Quick Start

### Enable Proactive Features in Your App

**1. In your initialization code:**
```python
from backend.services.message_analyzer import MessageAnalyzer
from backend.services.meeting_extractor import MeetingExtractor
from backend.services.proactive_meeting_handler import ProactiveMeetingHandler
from backend.handlers.message_handler import MessageHandler

# Create services
meeting_extractor = MeetingExtractor()
message_analyzer = MessageAnalyzer(db, meeting_extractor)
meeting_handler = ProactiveMeetingHandler(db, llm_client)

# Pass to message handler
message_handler = MessageHandler(
    db, llm_client, context_builder,
    boundary_manager, question_tracker, analytics,
    message_analyzer=message_analyzer  # ← Important!
)
```

**2. Add scheduled jobs (Celery task):**
```python
from celery import shared_task
from backend.services.proactive_meeting_handler import ProactiveMeetingHandler

@shared_task
def check_proactive_reminders():
    """Run every 5 minutes"""
    handler = ProactiveMeetingHandler(db, llm_client)
    await handler.check_and_send_preparation_reminders()
    await handler.check_and_send_completion_messages()
```

**3. Telegram /schedule command** - Already integrated! ✅

## What Happens Automatically

### When User Sends a Message
```
User: "I have a meeting tomorrow at 2 PM"
         ↓
    Message saved
         ↓
    MeetingExtractor analyzes
         ↓
    UserSchedule created
         ↓
    Proactive messages queued
```

### Timeline of Proactive Messages

```
T-0:00   User mentions meeting "tomorrow at 2 PM"
         → UserSchedule created
         → ProactiveSession marked (detected)

T+23:30  Automatic job runs
         → Finds schedules with start_time in next 35 min
         → Sends preparation reminder
         → ProactiveSession created (type='meeting_prep_reminder')

T+24:00  Meeting ends
         → If end_time provided: sends completion message
         → ProactiveSession created (type='meeting_completion')

T+24:15  User returns to chat
         → If no end_time: asks "How did it go?"
         → ProactiveSession created (type='meeting_followup_greeting')
```

## Database Schema Quick View

### user_schedules
| Field | Type | Purpose |
|-------|------|---------|
| id | UUID | Primary key |
| user_id | UUID | Which user |
| event_name | String | "Project Sync", "Team Standup" |
| start_time | DateTime | When meeting happens (UTC) |
| end_time | DateTime | When meeting ends (optional) |
| channel | String | 'web' or 'telegram' |
| preparation_reminder_sent | Boolean | Was reminder sent? |
| event_completed_sent | Boolean | Was completion sent? |
| followup_sent | Boolean | Was followup sent? |
| is_completed | Boolean | User confirmed done? |

### proactive_sessions
| Field | Type | Purpose |
|-------|------|---------|
| session_type | String | 'meeting_prep_reminder', 'meeting_completion', etc. |
| reference_id | UUID | Links to UserSchedule (if meeting-related) |
| message_content | Text | Actual message sent |
| channel | String | 'web' or 'telegram' |
| sent_at | DateTime | When was it sent |

## Meeting Extraction Examples

```python
from backend.services.meeting_extractor import MeetingExtractor

extractor = MeetingExtractor()

# Example 1: Specific time
meetings = extractor.extract_meetings("I have a meeting tomorrow at 2:30 PM")
# → event_name: "Meeting", start_time: <tomorrow 2:30 PM>, confidence: 0.7

# Example 2: With name and duration
meetings = extractor.extract_meetings(
    "Project sync with team from 3-4 PM next Tuesday"
)
# → event_name: "Project Sync", start_time: <next Tuesday 3 PM>, 
#   end_time: <next Tuesday 4 PM>, confidence: 0.8

# Example 3: Relative time
meetings = extractor.extract_meetings("Interview next Monday morning")
# → event_name: "Interview", start_time: <next Monday 8 AM>, confidence: 0.6

# Example 4: Low confidence (no time)
meetings = extractor.extract_meetings("I might have a meeting soon")
# → confidence: 0.4 (might be skipped due to low confidence)
```

## API Reference

### MeetingExtractor
```python
extractor = MeetingExtractor()

# Main method
meetings: List[MeetingInfo] = extractor.extract_meetings(
    message: str,
    reference_time: datetime = None  # defaults to now
)

# Returns: List of MeetingInfo objects
# MeetingInfo has: event_name, start_time, end_time, description, confidence
```

### MessageAnalyzer
```python
analyzer = MessageAnalyzer(db, meeting_extractor)

# Analyze and create schedules
schedules: List[UserSchedule] = await analyzer.analyze_for_schedules(
    message: Message,        # Message object
    user: User,              # User object
    bot: BotSettings,        # BotSettings object
    channel: str = 'web'     # 'web' or 'telegram'
)
```

### ProactiveMeetingHandler
```python
handler = ProactiveMeetingHandler(db, llm_client)

# Check and send reminders
reminders = await handler.check_and_send_preparation_reminders()
# Returns: List of sent reminders with timestamps

# Check and send completion messages
completions = await handler.check_and_send_completion_messages()
# Returns: List of sent completions with timestamps

# Get user's upcoming schedule
schedule = await handler.get_upcoming_meetings(
    user_id: str,
    hours: int = 24  # Look ahead N hours
)

# Check for first interaction after meeting
followup = await handler.check_first_interaction_after_meeting(
    user_id: str,
    channel: str  # 'web' or 'telegram'
)
```

## Telegram Commands

### /schedule
Shows upcoming meetings for the user.

**Example:**
```
User: /schedule

Bot responds:
📅 your upcoming schedule:

• Project Review
  Thu, Dec 12 at 02:30 PM ⏳ upcoming

• Team Standup  
  Fri, Dec 13 at 10:00 AM ⏳ upcoming

_use /support if you need to change something_
```

### /help
Lists all available commands (now includes /schedule).

## Customization

### Change Reminder Timing
```python
# In proactive_meeting_handler.py
class ProactiveMeetingHandler:
    PREPARATION_REMINDER_LEAD_TIME_MINUTES = 30  # ← Change this
    FOLLOWUP_DELAY_MINUTES = 5                    # ← Or this
```

### Add More Meeting Keywords
```python
# In meeting_extractor.py
MEETING_KEYWORDS = {
    'meeting', 'call', 'standup', 'sync',
    'your_new_keyword_here',  # ← Add here
}
```

### Customize Reminder Messages
```python
# In proactive_meeting_handler.py, _generate_preparation_message()
messages = [
    f"Custom message format for {meeting_name}",
    f"Another variant for {time_str}",
]
```

## Testing

### Unit Test - Meeting Extraction
```python
from backend.services.meeting_extractor import MeetingExtractor

def test_meeting_extraction():
    extractor = MeetingExtractor()
    meetings = extractor.extract_meetings("Meeting tomorrow at 2 PM")
    
    assert len(meetings) > 0
    assert meetings[0].event_name is not None
    assert meetings[0].start_time is not None
    assert meetings[0].confidence > 0.5
```

### Integration Test - Full Flow
```python
async def test_proactive_flow():
    # 1. Create user and send message with meeting
    user = await create_test_user(db)
    message_text = "I have a project meeting tomorrow at 3 PM"
    
    # 2. Process message (triggers analysis)
    handler = MessageHandler(db, llm, ...)
    response = await handler.handle(user.telegram_id, message_text)
    
    # 3. Verify schedule was created
    schedules = await db.execute(
        select(UserSchedule).where(UserSchedule.user_id == user.id)
    )
    assert len(schedules.scalars().all()) > 0
    
    # 4. Manually trigger reminder job
    meeting_handler = ProactiveMeetingHandler(db)
    reminders = await meeting_handler.check_and_send_preparation_reminders()
    
    # 5. Verify reminder was sent
    assert len(reminders) > 0
```

## Debugging

### Check if Meeting Was Detected
```sql
-- See all user's schedules
SELECT user_id, event_name, start_time, channel, preparation_reminder_sent
FROM user_schedules
WHERE user_id = 'YOUR_USER_ID'
ORDER BY start_time DESC;
```

### Check Proactive Messages Sent
```sql
-- See all proactive interactions
SELECT session_type, reference_id, channel, sent_at
FROM proactive_sessions
WHERE user_id = 'YOUR_USER_ID'
ORDER BY sent_at DESC
LIMIT 20;
```

### Enable Debug Logging
```python
import logging

# Get loggers
meeting_log = logging.getLogger('backend.services.meeting_extractor')
analyzer_log = logging.getLogger('backend.services.message_analyzer')
handler_log = logging.getLogger('backend.services.proactive_meeting_handler')

# Set debug level
for logger in [meeting_log, analyzer_log, handler_log]:
    logger.setLevel(logging.DEBUG)

# Now run your code and watch for detailed logs
```

## Common Issues & Solutions

### Issue: Meetings not being detected
**Causes:**
- Message analyzer not passed to message handler
- Meeting keywords don't match user's language
- Confidence score too low

**Solution:**
```python
# Check logs for extraction confidence
logging.getLogger('backend.services.meeting_extractor').setLevel(logging.DEBUG)

# Add more keywords if needed
MEETING_KEYWORDS.add('your_missing_keyword')
```

### Issue: Reminders not being sent
**Causes:**
- Scheduled job not running
- Message sent with no time information
- Timezone conversion issue

**Solution:**
```python
# Test manually
handler = ProactiveMeetingHandler(db, llm)
reminders = await handler.check_and_send_preparation_reminders()
print(f"Reminders sent: {len(reminders)}")

# Check database
SELECT * FROM user_schedules WHERE preparation_reminder_sent = false;
```

### Issue: Wrong messages on Telegram vs Web
**Causes:**
- Channel not set correctly when creating schedule
- Message picked wrong channel

**Solution:**
```python
# When analyzing message, ensure you pass correct channel
await analyzer.analyze_for_schedules(
    message, user, bot,
    channel='telegram'  # ← Make sure this is correct
)
```

## Performance Considerations

- **Meeting extraction**: ~10-50ms per message (depends on message length)
- **Schedule creation**: ~5-20ms per schedule
- **Reminder checking**: ~100-500ms (scales with number of users)
- **Database queries**: Indexed on user_id, start_time, is_completed

### Optimization Tips
1. Run reminder checks as background job (Celery), not in request
2. Use database indexes on frequently queried columns
3. Cache user timezone preferences
4. Batch API calls for sending reminders

---

**For more details, see**: `PROACTIVE_FEATURES.md` and `PROACTIVE_IMPLEMENTATION_SUMMARY.md`
