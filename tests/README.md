# Test Suite for AI Companion Bot

## Running Tests

### Unit Tests (Pytest)
```bash
# Run all proactive meeting tests
python -m pytest tests/test_proactive_meeting.py -v

# Run specific test
python -m pytest tests/test_proactive_meeting.py::test_meeting_preparation_reminder -v

# Run with coverage
python -m pytest tests/test_proactive_meeting.py -v --cov=backend
```

### Scenario Tests
```bash
# Run the 2-minute meeting scenario
python tests/test_meeting_scenario.py
```

## Test Coverage

### test_proactive_meeting.py
- `test_meeting_preparation_reminder()` - Tests that reminders are sent for upcoming meetings
- `test_meeting_completion_message()` - Tests that completion messages are sent after meetings end
- `test_meeting_no_duplicate_reminders()` - Tests that reminders aren't sent twice
- `test_meeting_respects_dnd_hours()` - Tests DND (Do Not Disturb) functionality

### test_meeting_scenario.py
- Comprehensive scenario: "my meeting is about to start in 2 minutes and it will remain for 1 minute"
- Verifies:
  - Message is recognized as proactive (contains "meeting")
  - Schedule is created with correct times
  - Preparation reminder sent before meeting starts
  - Completion message sent after meeting ends
  - All proactive session records are created correctly

## Adding More Tests

Create new test files in the `tests/` folder following the same pattern:
- Use `@pytest_asyncio.fixture` for async fixtures
- Use `@pytest.mark.asyncio` for async test functions
- Import from `backend/` using absolute imports after adding to sys.path
