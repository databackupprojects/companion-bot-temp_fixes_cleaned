# Proactive Behavior System - Documentation

## Overview

The proactive behavior system enables the AI companion to:
1. **Detect and track meetings/events** mentioned in conversations
2. **Send preparation reminders** before important meetings
3. **Send completion messages** after meetings end
4. **Welcome users back** with context about meetings they discussed
5. **Avoid repetition** by tracking what's already been discussed
6. **Respect timezones** for time-sensitive greetings and reminders
7. **Channel awareness** - Send messages on the same platform (web/Telegram) where the discussion happened

## Architecture

### Components

#### 1. **Meeting Extractor** (`services/meeting_extractor.py`)
- Analyzes user messages for mentions of meetings, events, appointments
- Uses pattern matching to extract:
  - Event name (e.g., "Project Sync", "Team Standup")
  - Time information (specific times like "2:30 PM" or relative like "tomorrow")
  - Duration (if provided)
  - Confidence score (0-1) indicating extraction reliability

**Key class**: `MeetingExtractor`
```python
extractor = MeetingExtractor()
meetings = extractor.extract_meetings("I have a meeting tomorrow at 2:30 PM")
# Returns: [MeetingInfo(event_name='Meeting', start_time=<datetime>, confidence=0.7)]
```

#### 2. **Message Analyzer** (`services/message_analyzer.py`)
- Analyzes incoming user messages for actionable schedule information
- Creates `UserSchedule` entries automatically when meetings are detected
- Prevents duplicate schedule entries
- Maintains conversation context

**Key class**: `MessageAnalyzer`
```python
analyzer = MessageAnalyzer(db, meeting_extractor)
schedules = await analyzer.analyze_for_schedules(message, user, bot, channel='web')
```

#### 3. **Proactive Meeting Handler** (`services/proactive_meeting_handler.py`)
- Manages the timing and delivery of proactive messages
- Sends preparation reminders (30 minutes before meeting by default)
- Sends completion messages (after meeting ends)
- Sends welcome-back greetings with meeting context
- Tracks sent messages to avoid repetition

**Key class**: `ProactiveMeetingHandler`
```python
handler = ProactiveMeetingHandler(db, llm_client)

# Check for reminders
reminders = await handler.check_and_send_preparation_reminders()

# Check for completion messages
completions = await handler.check_and_send_completion_messages()

# Get user's schedule
schedule = await handler.get_upcoming_meetings(user_id, hours=24)
```

### Database Models

#### `UserSchedule`
Stores meeting and event information mentioned by users.

```python
class UserSchedule(Base):
    id: UUID
    user_id: UUID  # Link to user
    bot_id: UUID   # Which bot was chatted with
    event_name: str  # "Project Meeting", "Team Standup", etc.
    description: str  # Original context from message
    start_time: DateTime  # When meeting starts (UTC)
    end_time: DateTime    # When meeting ends (optional)
    channel: str          # 'web' or 'telegram'
    
    # Tracking proactive messages
    preparation_reminder_sent: bool
    event_completed_sent: bool
    followup_sent: bool
    
    # Status
    is_completed: bool  # User confirmed it's done
```

#### `ProactiveSession`
Tracks individual proactive interactions to prevent repetition.

```python
class ProactiveSession(Base):
    session_type: str  # 'morning_greeting', 'meeting_prep', 'meeting_completion', etc.
    reference_id: UUID  # Links to UserSchedule if related to a meeting
    message_content: str  # What was actually sent
    channel: str  # 'web' or 'telegram'
    sent_at: DateTime
    acknowledged_at: DateTime (optional)  # When user responded
```

#### `GreetingPreference`
Stores user preferences for proactive communication.

```python
class GreetingPreference(Base):
    user_id: UUID
    prefer_proactive: bool  # Opt-in/out
    preferred_greeting_time: str  # 'morning', 'afternoon', 'evening'
    dnd_start_hour: int  # Do Not Disturb start (0-23)
    dnd_end_hour: int    # Do Not Disturb end
    max_proactive_per_day: int  # Frequency cap
```

## User Flow

### 1. User Mentions a Meeting
**Web Chat:**
```
User: "I have a project review meeting tomorrow at 2:30 PM with the team"

System Flow:
- Message saved to Messages table
- MessageAnalyzer detects meeting
- MeetingExtractor creates MeetingInfo with:
  - event_name: "Project Review"
  - start_time: <tomorrow 2:30 PM in user's timezone>
  - confidence: 0.85
- UserSchedule created in database
- ProactiveSession marked that meeting was detected
```

**Telegram:**
- Same flow, but `channel='telegram'` is stored

### 2. Proactive Reminder (Before Meeting)
**Default: 30 minutes before**

```
Scheduled Job: check_and_send_preparation_reminders()
- Finds all UserSchedule.start_time between now and now+35 minutes
- For each unchecked schedule:
  - Generates friendly reminder
  - Creates ProactiveSession with type='meeting_prep_reminder'
  - Sends message on same channel discussion occurred
  - Marks UserSchedule.preparation_reminder_sent = true

Example message:
"🕐 Heads up! Your Project Review is coming up at 2:30 PM. 
Take a moment to prepare!"
```

### 3. Proactive Completion Message (After Meeting)
**If end_time was provided:**

```
Scheduled Job: check_and_send_completion_messages()
- Finds all UserSchedule where end_time <= now
- Generates completion message
- Sends on same channel
- Marks UserSchedule.event_completed_sent = true

Example message:
"✨ Your Project Review is done! How did it go?"
```

### 4. Welcome Back with Context (No End Time)
**When user returns to chat**

```
On user's next message:
ProactiveMeetingHandler.check_first_interaction_after_meeting()
- Finds recent meetings without end times
- Checks if conversation happened > 15 minutes ago
- Sends follow-up greeting with context
- Marks UserSchedule.followup_sent = true

Example message:
"Hey! 👋 Tell me about that project review you mentioned - 
how did it go?"
```

### 5. Telegram /schedule Command
```
User types: /schedule

Returns formatted list:
📅 your upcoming schedule:

• Project Review
  Tomorrow, 2:30 PM ⏳ upcoming

• Team Standup  
  Dec 13, 10:00 AM ⏳ upcoming
```

## Timezone Handling

### Current Status
- ✅ Timezone stored in User model (default: UTC)
- ⏳ Timezone capture in web onboarding (being added)
- ✅ Timezone used in proactive messages
- ✅ Timezone conversion for display

### Implementation

```python
# In proactive message generation
user_tz = user.timezone  # e.g., "Asia/Kolkata"
local_time = schedule.start_time.replace(tzinfo=pytz.UTC).astimezone(
    pytz.timezone(user_tz)
)
time_str = local_time.strftime("%I:%M %p")
# Result: "2:30 PM" in user's local time
```

## Channel Awareness

### Same Channel Delivery
```python
# If meeting discussed on Telegram
schedule.channel = 'telegram'
# → Reminder sent via Telegram /start or direct message

# If meeting discussed on web
schedule.channel = 'web'
# → Reminder shown in web dashboard chat
```

## Preventing Repetition

### Deduplication
1. **Schedule duplicates**: Check within 5-minute window
   - Prevents creating multiple schedules for same meeting

2. **ProactiveSession tracking**: Never send same type twice
   - One preparation reminder per meeting
   - One completion message per meeting
   - One welcome-back greeting per meeting

3. **Time-based flags**: Boolean columns track what's been sent
   - `preparation_reminder_sent`
   - `event_completed_sent`
   - `followup_sent`

## Integration Points

### 1. Message Handler
File: `handlers/message_handler.py`

```python
# After user message is saved:
if self.message_analyzer:
    created_schedules = await self.message_analyzer.analyze_for_schedules(
        user_message,
        user_obj,
        bot_settings,
        channel=channel  # 'web' or 'telegram'
    )
```

### 2. Scheduled Jobs
File: `backend/jobs/` or scheduled tasks

```python
# Every 5 minutes:
await meeting_handler.check_and_send_preparation_reminders()

# Every 5 minutes:
await meeting_handler.check_and_send_completion_messages()

# On user login/message:
await meeting_handler.check_first_interaction_after_meeting(user_id, channel)
```

### 3. Telegram Commands
File: `handlers/command_handler.py`

```
/schedule - View upcoming meetings
/help     - Shows all commands including /schedule
```

## Configuration

### Meeting Extractor Settings
```python
MEETING_KEYWORDS = {
    'meeting', 'call', 'standup', 'sync', 'presentation',
    'appointment', 'interview', 'demo', ...
}

PREPARATION_REMINDER_LEAD_TIME_MINUTES = 30
FOLLOWUP_DELAY_MINUTES = 5
```

### Greeting Preferences
Per-user settings stored in `GreetingPreference` table:
- Toggle proactive on/off
- Set preferred greeting time
- Set Do Not Disturb hours
- Set max messages per day

## Future Enhancements

1. **Calendar Integration**
   - Sync with Google Calendar, Outlook, iCal
   - Auto-populate UserSchedule from calendar events

2. **Smart Reminders**
   - ML-based optimal reminder time
   - Learn user's preparation habits

3. **Meeting Prep Suggestions**
   - "Do you want help preparing?" with contextual suggestions
   - Task lists for meetings

4. **Post-Meeting Analytics**
   - "How was your meeting?" followups
   - Mood check after stressful meetings
   - Success tracking

5. **Recurring Events**
   - Detect and handle weekly/monthly meetings
   - Smart defaults ("every Tuesday at 2 PM")

6. **Cross-User Meetings**
   - Track meetings with other users
   - "You both have a meeting at 3 PM on Friday"

## Testing

### Unit Tests
```python
# Test meeting extraction
extractor = MeetingExtractor()
meetings = extractor.extract_meetings("I have a meeting tomorrow at 2:30 PM")
assert len(meetings) == 1
assert meetings[0].event_name
assert meetings[0].start_time is not None
```

### Integration Tests
```python
# Test full flow
1. Create user
2. Send message with meeting
3. Verify UserSchedule created
4. Wait for reminder time
5. Verify ProactiveSession created
6. Check message sent on correct channel
```

## Logging

Enable debug logging for proactive features:
```python
# In logs, look for:
[Quiz] Auto-detected timezone: Asia/Kolkata
[MessageAnalyzer] Found X meeting(s) in message
[ProactiveMeetingHandler] Preparation reminder sent
[CommandHandler] /schedule requested by user
```
