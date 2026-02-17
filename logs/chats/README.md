# Chat Logs Directory

This directory stores conversation logs for analysis and improvement.

## Structure

```
logs/chats/
├── {username}_{user_id}/
│   ├── {bot_id}/
│   │   ├── 2026-01-07.log      ← Day 1 conversations only
│   │   ├── 2026-01-08.log      ← Day 2 conversations only
│   │   ├── combined.log        ← ALL conversations (all days)
│   │   └── ...
│   └── {another_bot_id}/
│       ├── 2026-01-07.log
│       ├── combined.log
│       └── ...
└── ...
```

## Log Files

### Daily Log Files
Each daily log file (e.g., `2026-01-07.log`) contains only that day's conversations.

### Combined Log File
The `combined.log` file contains **all conversations** from all days for that specific user-bot pair.
This allows you to:
- View entire conversation history at a glance
- Analyze long-term interaction patterns
- Track bot improvement over time
- Export complete conversation dataset

## Log Format

Each log file contains a JSON array of conversation entries:

```json
[
  {
    "timestamp": "2026-01-07T12:34:56.789Z",
    "user_message": "Hello!",
    "bot_response": "Hey! So good to see you!",
    "message_type": "reactive",
    "source": "web"
  },
  {
    "timestamp": "2026-01-07T13:00:00.000Z",
    "bot_message": "Good morning! How are you feeling today?",
    "message_type": "proactive",
    "source": "telegram"
  }
]
```

## Field Descriptions

- **timestamp**: ISO 8601 timestamp of the message
- **user_message**: User's message (for reactive conversations)
- **bot_response**: Bot's response (for reactive conversations)
- **bot_message**: Bot's message (for proactive messages)
- **message_type**: Either "reactive" or "proactive"
- **source**: Origin of the message - "web" or "telegram"

## Notes

- **user_id** and **bot_id** are stored in the folder path, not in each entry
- **username** is included in the folder name for easy identification
- All entries for a single day are stored in one JSON array
- This format makes it easy to load and analyze entire conversation days

## Configuration

Set in `.env`:
- `ENABLE_CHAT_LOGGING=true` - Enable/disable logging
- `CHAT_LOGS_DIR=logs/chats` - Directory path

## Privacy & Retention

- Logs contain sensitive user data
- Should be secured appropriately
- Consider implementing retention policies
- Exclude from version control (see .gitignore)

