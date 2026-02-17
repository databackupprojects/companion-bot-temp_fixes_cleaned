# Proactive Features - Deployment Checklist

## Pre-Deployment

- [ ] Code review completed
- [ ] All tests passing
- [ ] Documentation reviewed
- [ ] Team aligned on feature behavior

## Database

- [ ] **Run migration**
  ```bash
  psql -U user -h localhost -d companion_bot \
    -f database/migrations/v3.7_proactive_features.sql
  ```
  - [ ] Verify tables created: `user_schedules`, `proactive_sessions`, `greeting_preferences`
  - [ ] Verify indexes created
  - [ ] Verify trigger for auto-creating greeting preferences

  **Verification SQL:**
  ```sql
  \dt user_schedules
  \dt proactive_sessions
  \dt greeting_preferences
  SELECT COUNT(*) FROM information_schema.indexes WHERE table_name = 'user_schedules';
  ```

## Backend Code

- [ ] **Update Message Handler initialization**
  - [ ] File: `backend/main.py` or app initialization
  - [ ] Add imports:
    ```python
    from backend.services.meeting_extractor import MeetingExtractor
    from backend.services.message_analyzer import MessageAnalyzer
    ```
  - [ ] Create analyzer instance:
    ```python
    meeting_extractor = MeetingExtractor()
    message_analyzer = MessageAnalyzer(db, meeting_extractor)
    ```
  - [ ] Pass to MessageHandler:
    ```python
    message_handler = MessageHandler(
        db, llm_client, context_builder,
        boundary_manager, question_tracker, analytics,
        message_analyzer=message_analyzer  # ← Add this
    )
    ```

- [ ] **Register Telegram /schedule command**
  - [ ] File: `backend/telegram_bot.py`
  - [ ] In command handlers list (around line 83-90):
    ```python
    self.application.add_handler(CommandHandler("schedule", self.handle_command))
    ```
  - [ ] Test: `/schedule` in Telegram should work

- [ ] **Set up scheduled jobs**
  - [ ] File: `backend/jobs/jobs.py` (or your scheduler)
  - [ ] Add periodic task:
    ```python
    @periodic_task(run_every=crontab(minute='*/5'))  # Every 5 minutes
    def check_meeting_reminders():
        asyncio.run(check_proactive_reminders())
    
    async def check_proactive_reminders():
        from backend.services.proactive_meeting_handler import ProactiveMeetingHandler
        handler = ProactiveMeetingHandler(db, llm_client)
        await handler.check_and_send_preparation_reminders()
        await handler.check_and_send_completion_messages()
    ```
  - [ ] Test job runs correctly
  - [ ] Monitor logs for execution

## Testing

### Unit Tests
- [ ] Test meeting extraction:
  ```bash
  python -m pytest backend/tests/test_meeting_extractor.py -v
  ```
  - [ ] Test time parsing (specific and relative)
  - [ ] Test event name extraction
  - [ ] Test confidence calculations

- [ ] Test message analyzer:
  ```bash
  python -m pytest backend/tests/test_message_analyzer.py -v
  ```
  - [ ] Test schedule creation
  - [ ] Test duplicate prevention
  - [ ] Test channel assignment

- [ ] Test proactive handler:
  ```bash
  python -m pytest backend/tests/test_proactive_meeting_handler.py -v
  ```
  - [ ] Test reminder sending
  - [ ] Test completion messages
  - [ ] Test followup greetings

### Integration Tests
- [ ] **Web flow:**
  - [ ] User sends message with meeting on web
  - [ ] Verify UserSchedule created
  - [ ] Wait/trigger job, verify ProactiveSession created
  - [ ] Verify reminder appears in web chat

- [ ] **Telegram flow:**
  - [ ] User sends message with meeting on Telegram
  - [ ] Verify UserSchedule created with channel='telegram'
  - [ ] Trigger job, verify reminder sent via Telegram
  - [ ] Test /schedule command returns correct meetings

- [ ] **Cross-channel:**
  - [ ] Web discussion creates reminder on web
  - [ ] Telegram discussion creates reminder on Telegram
  - [ ] Verify channels don't mix

### Manual Testing Checklist
- [ ] [ ] **Test Case 1: Specific time**
  - [ ] Web: "I have a meeting tomorrow at 2:30 PM"
  - [ ] Verify UserSchedule created
  - [ ] Verify start_time is correct
  - [ ] Trigger reminder job
  - [ ] Verify reminder sent

- [ ] **Test Case 2: Relative time**
  - [ ] Web: "Standup next Monday morning"
  - [ ] Verify start_time set to next Monday ~8 AM
  - [ ] Check Telegram /schedule shows it

- [ ] **Test Case 3: With duration**
  - [ ] Web: "Team meeting 3-4 PM Friday"
  - [ ] Verify both start_time and end_time set
  - [ ] After 4 PM, trigger job
  - [ ] Verify completion message sent

- [ ] **Test Case 4: No end time (followup)**
  - [ ] Web: "I have a 1-on-1 tomorrow at 10 AM"
  - [ ] After 10:15 AM, user sends new message
  - [ ] Verify followup asking about meeting

- [ ] **Test Case 5: Duplicate prevention**
  - [ ] Same user, same meeting twice in same message
  - [ ] Verify only ONE UserSchedule created

- [ ] **Test Case 6: Telegram /schedule command**
  - [ ] Set up 3-4 meetings on Telegram
  - [ ] Send /schedule
  - [ ] Verify all upcoming meetings shown with times
  - [ ] Verify formatting is clean for mobile

## Configuration & Monitoring

- [ ] **Enable debug logging**
  ```python
  import logging
  logging.getLogger('backend.services.meeting_extractor').setLevel(logging.DEBUG)
  logging.getLogger('backend.services.message_analyzer').setLevel(logging.DEBUG)
  logging.getLogger('backend.services.proactive_meeting_handler').setLevel(logging.DEBUG)
  ```

- [ ] **Monitor database growth**
  ```sql
  -- Check how many schedules are created
  SELECT DATE(created_at), COUNT(*) FROM user_schedules GROUP BY DATE(created_at);
  
  -- Check reminder performance
  SELECT session_type, COUNT(*) FROM proactive_sessions GROUP BY session_type;
  ```

- [ ] **Set up alerts for:**
  - [ ] Job execution failures
  - [ ] High DB query latency
  - [ ] Meeting extraction confidence < 0.5
  - [ ] Failed message sends

## Rollout Strategy

### Phase 1: Alpha (1-2 days)
- [ ] Deploy to staging environment
- [ ] Run full test suite
- [ ] Internal team testing
- [ ] Monitor logs and alerts

### Phase 2: Beta (3-7 days)
- [ ] Deploy to production
- [ ] Enable for 10-20% of users
- [ ] Monitor closely for issues
- [ ] Collect feedback

### Phase 3: Full Release
- [ ] Enable for all users
- [ ] Monitor for 1 week
- [ ] Adjust configurations based on data
- [ ] Plan enhancements

## Rollback Plan

If issues occur, rollback in this order:

1. **Disable proactive jobs** (keep database)
   - [ ] Disable scheduled reminder jobs
   - [ ] Users still see /schedule command

2. **Disable meeting extraction** (keep historical data)
   - [ ] Disable message_analyzer in handler
   - [ ] No new schedules created
   - [ ] Old schedules still visible

3. **Disable feature completely** (if critical)
   ```sql
   -- Disable all proactive_sessions
   UPDATE proactive_sessions SET sent_at = NULL WHERE sent_at > '2024-01-XX';
   
   -- Keep all data for future recovery
   ```

4. **Full rollback** (last resort)
   - [ ] Remove message_analyzer from handler
   - [ ] Drop new tables (or keep for future)
   - [ ] Redeploy previous version

## Success Metrics

Track these after deployment:

1. **Adoption**
   - [ ] % of users with detected meetings
   - [ ] Average meetings per user per week
   - [ ] % of meetings with end times

2. **Engagement**
   - [ ] % of reminders clicked/acknowledged
   - [ ] Time to first interaction after reminder
   - [ ] User satisfaction (if surveyed)

3. **Performance**
   - [ ] Average extraction time per message (< 50ms)
   - [ ] Job execution time (< 1 second)
   - [ ] Database query latency (< 100ms)
   - [ ] False positive rate (low confidence matches)

4. **Quality**
   - [ ] % of correctly detected meetings
   - [ ] % of reminders sent at right time
   - [ ] User complaints about spam/irrelevant reminders

## Post-Deployment

- [ ] Monitor logs for 24 hours
- [ ] Check success metrics daily for first week
- [ ] Respond to user feedback
- [ ] Plan next enhancements:
  - [ ] Timezone capture in onboarding
  - [ ] Time-based greetings
  - [ ] Calendar integration
  - [ ] Recurring meetings

## Contacts & Escalation

- [ ] Database issues: [DBA contact]
- [ ] Performance issues: [DevOps contact]
- [ ] User complaints: [Support contact]
- [ ] Feature issues: [Your team lead]

## Documentation

- [ ] [ ] Update API documentation
- [ ] [ ] Add to README.md
- [ ] [ ] Create user guide (if applicable)
- [ ] [ ] Update troubleshooting guide
- [ ] [ ] Add to changelog

## Sign-off

- [ ] Development team lead: _________________ Date: _____
- [ ] QA team lead: _________________ Date: _____
- [ ] Product owner: _________________ Date: _____
- [ ] DevOps/Platform: _________________ Date: _____

---

## Quick Troubleshooting During Rollout

| Issue | Check | Fix |
|-------|-------|-----|
| Meetings not detected | Logs for extraction score | Add keywords or lower confidence threshold |
| Reminders not sent | Job is running? DB records exist? | Check job logs, verify channel setting |
| Wrong timing | User timezone correct? | Verify timezone in User model |
| Too many reminders | Duplicate prevention working? | Check flags in UserSchedule |
| Performance issues | Job taking too long? | Add indexes, optimize queries |
| Errors in logs | Check stack trace | Review code changes, run tests |

---

**Deployment Date:** ___________
**Deployed By:** ___________
**Approved By:** ___________
**Notes:** 
