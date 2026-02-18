"""
Integration tests for:
1. LLMMeetingExtractor – GPT-4 event extraction with regex fallback
2. MessageAnalyzer – LLM-first extraction with automatic fallback
3. JobManager – ProactiveWorker wiring (start / stop lifecycle)

All external dependencies (OpenAI API, database) are mocked so the tests
run without network or PostgreSQL.
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Path setup – make sure 'backend' is importable
# ---------------------------------------------------------------------------
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_path)


# =====================================================================
# 1. LLMMeetingExtractor tests
# =====================================================================

class TestLLMMeetingExtractor:
    """Tests for the GPT-4 meeting extractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Build a mock that looks like OpenAILLMClient."""
        client = MagicMock()
        client.client = AsyncMock()
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        from services.meeting_extractor import LLMMeetingExtractor
        return LLMMeetingExtractor(mock_llm_client)

    def _make_llm_response(self, content: str):
        """Helper: build an object matching openai ChatCompletion shape."""
        choice = SimpleNamespace(message=SimpleNamespace(content=content))
        return SimpleNamespace(choices=[choice])

    # --- happy path ---

    @pytest.mark.asyncio
    async def test_extracts_single_event(self, extractor, mock_llm_client):
        payload = json.dumps({
            "events": [{
                "name": "Dentist",
                "date": "2026-02-20",
                "time": "14:00",
                "end_time": None,
                "description": "dentist appointment",
            }]
        })
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response(payload)
        )

        ref = datetime(2026, 2, 18, 10, 0)
        meetings = await extractor.extract_meetings("dentist on Friday at 2pm", ref)

        assert len(meetings) == 1
        m = meetings[0]
        assert m.event_name == "Dentist"
        assert m.start_time == datetime(2026, 2, 20, 14, 0)
        assert m.confidence == 0.9

    @pytest.mark.asyncio
    async def test_extracts_multiple_events(self, extractor, mock_llm_client):
        payload = json.dumps({
            "events": [
                {"name": "Standup", "date": "2026-02-19", "time": "09:00",
                 "end_time": "09:15", "description": None},
                {"name": "Lunch with Sarah", "date": "2026-02-19", "time": "12:30",
                 "end_time": "13:30", "description": "at the new place"},
            ]
        })
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response(payload)
        )

        meetings = await extractor.extract_meetings("standup at 9, lunch with Sarah at 12:30")
        assert len(meetings) == 2
        assert meetings[0].event_name == "Standup"
        assert meetings[1].event_name == "Lunch with Sarah"
        assert meetings[1].end_time == datetime(2026, 2, 19, 13, 30)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_events(self, extractor, mock_llm_client):
        payload = json.dumps({"events": []})
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response(payload)
        )

        meetings = await extractor.extract_meetings("just saying hi")
        assert meetings == []

    @pytest.mark.asyncio
    async def test_handles_code_fenced_response(self, extractor, mock_llm_client):
        """LLMs sometimes wrap JSON in ```json ... ``` fences."""
        payload = '```json\n{"events": [{"name": "Call", "date": "2026-02-18", "time": "15:00", "end_time": null, "description": null}]}\n```'
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response(payload)
        )

        meetings = await extractor.extract_meetings("call at 3pm")
        assert len(meetings) == 1
        assert meetings[0].event_name == "Call"

    # --- fallback path ---

    @pytest.mark.asyncio
    async def test_falls_back_to_regex_on_llm_error(self, extractor, mock_llm_client):
        """If the LLM call raises, we should fall back to regex."""
        mock_llm_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API quota exceeded")
        )

        ref = datetime(2026, 2, 18, 10, 0)
        meetings = await extractor.extract_meetings(
            "I have a meeting at 3:00 PM tomorrow", ref
        )
        # regex extractor should still pick up the meeting keyword + time
        assert len(meetings) >= 1

    @pytest.mark.asyncio
    async def test_falls_back_on_bad_json(self, extractor, mock_llm_client):
        """If the LLM returns non-JSON, regex fallback kicks in."""
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response("Sorry, I can't do that.")
        )

        meetings = await extractor.extract_meetings(
            "I have a meeting at 3:00 PM", datetime(2026, 2, 18, 10, 0)
        )
        # regex should pick this up
        assert len(meetings) >= 1

    @pytest.mark.asyncio
    async def test_empty_message_returns_empty(self, extractor):
        assert await extractor.extract_meetings("") == []
        assert await extractor.extract_meetings("   ") == []

    @pytest.mark.asyncio
    async def test_handles_partial_time_from_llm(self, extractor, mock_llm_client):
        """Event with date but no time should still be returned (start_time=None)."""
        payload = json.dumps({
            "events": [{"name": "Vacation starts", "date": "2026-03-01",
                         "time": None, "end_time": None, "description": None}]
        })
        mock_llm_client.client.chat.completions.create = AsyncMock(
            return_value=self._make_llm_response(payload)
        )

        meetings = await extractor.extract_meetings("vacation starts March 1st")
        assert len(meetings) == 1
        assert meetings[0].start_time is None
        assert meetings[0].event_name == "Vacation starts"


# =====================================================================
# 2. MessageAnalyzer with LLM extractor tests
# =====================================================================

class TestMessageAnalyzerWithLLM:
    """Tests that MessageAnalyzer tries LLM first and falls back to regex."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        # For duplicate check query
        result = AsyncMock()
        result.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.client = AsyncMock()
        return client

    @pytest.fixture
    def user(self):
        u = MagicMock()
        u.id = uuid4()
        u.timezone = "UTC"
        return u

    @pytest.fixture
    def bot(self):
        b = MagicMock()
        b.id = uuid4()
        return b

    @pytest.fixture
    def message_obj(self):
        m = MagicMock()
        m.id = uuid4()
        m.content = "dentist on Friday at 2pm"
        return m

    @pytest.mark.asyncio
    async def test_analyzer_uses_llm_when_available(
        self, mock_db, mock_llm_client, user, bot, message_obj
    ):
        from services.message_analyzer import MessageAnalyzer

        payload = json.dumps({
            "events": [{
                "name": "Dentist",
                "date": "2026-02-20",
                "time": "14:00",
                "end_time": None,
                "description": "dentist appointment",
            }]
        })
        choice = SimpleNamespace(message=SimpleNamespace(content=payload))
        resp = SimpleNamespace(choices=[choice])
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=resp)

        analyzer = MessageAnalyzer(mock_db, llm_client=mock_llm_client)
        schedules = await analyzer.analyze_for_schedules(message_obj, user, bot)

        # Should have created a schedule
        assert len(schedules) == 1
        assert schedules[0].event_name == "Dentist"
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_analyzer_falls_back_to_regex_when_llm_fails(
        self, mock_db, mock_llm_client, user, bot
    ):
        from services.message_analyzer import MessageAnalyzer

        mock_llm_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("timeout")
        )

        msg = MagicMock()
        msg.id = uuid4()
        msg.content = "I have a meeting at 3:00 PM tomorrow"

        analyzer = MessageAnalyzer(mock_db, llm_client=mock_llm_client)
        schedules = await analyzer.analyze_for_schedules(msg, user, bot)

        # Regex should pick up "meeting" + "3:00 PM"
        assert len(schedules) >= 1

    @pytest.mark.asyncio
    async def test_analyzer_works_without_llm_client(self, mock_db, user, bot):
        """When no llm_client is passed, only regex is used (no crash)."""
        from services.message_analyzer import MessageAnalyzer

        msg = MagicMock()
        msg.id = uuid4()
        msg.content = "team sync at 10:00 AM tomorrow"

        analyzer = MessageAnalyzer(mock_db, llm_client=None)
        assert analyzer.llm_meeting_extractor is None

        schedules = await analyzer.analyze_for_schedules(msg, user, bot)
        # regex should pick up "sync" + time
        assert len(schedules) >= 1


# =====================================================================
# 3. JobManager ProactiveWorker wiring tests
# =====================================================================

class TestJobManagerWiring:
    """Verify ProactiveWorker is properly wired into JobManager lifecycle."""

    @pytest.mark.asyncio
    async def test_proactive_worker_initialised_on_start(self):
        """After start(), proactive_worker should be set and a task created."""
        from core.container import JobManager

        mock_llm = MagicMock()
        jm = JobManager(mock_llm)

        with patch("core.container.AsyncSessionLocal") as mock_session_factory, \
             patch("core.container.DailyResetJob") as MockDR, \
             patch("core.container.DataCleanupJob") as MockDC, \
             patch("core.container.MemorySummarizer") as MockMS, \
             patch("core.container.ProactiveMeetingChecker") as MockPMC, \
             patch("core.container.ProactiveWorker") as MockPW, \
             patch("core.container.BoundaryManager"), \
             patch("core.container.Analytics"), \
             patch("core.container.ContextBuilder"):

            # Make all .run() methods return a coroutine that sleeps forever
            async def forever():
                await asyncio.sleep(999999)

            MockDR.return_value.run = forever
            MockDC.return_value.run = forever
            MockMS.return_value.run = forever
            MockPW.return_value.run = forever
            mock_session_factory.return_value = AsyncMock()

            await jm.start()

            # ProactiveWorker should have been constructed
            MockPW.assert_called_once()

            # Its run() should be scheduled as a task
            # We started 5 tasks: daily_reset, data_cleanup, memory_summarizer,
            # proactive_checker_loop, proactive_worker
            assert len(jm._tasks) == 5

            # proactive_worker attribute should be set
            assert jm.proactive_worker is not None

            await jm.stop()

    @pytest.mark.asyncio
    async def test_proactive_worker_stopped_on_shutdown(self):
        """stop() should call proactive_worker.stop()."""
        from core.container import JobManager

        mock_llm = MagicMock()
        jm = JobManager(mock_llm)

        with patch("core.container.AsyncSessionLocal") as mock_session_factory, \
             patch("core.container.DailyResetJob") as MockDR, \
             patch("core.container.DataCleanupJob") as MockDC, \
             patch("core.container.MemorySummarizer") as MockMS, \
             patch("core.container.ProactiveMeetingChecker") as MockPMC, \
             patch("core.container.ProactiveWorker") as MockPW, \
             patch("core.container.BoundaryManager"), \
             patch("core.container.Analytics"), \
             patch("core.container.ContextBuilder"):

            async def forever():
                await asyncio.sleep(999999)

            MockDR.return_value.run = forever
            MockDC.return_value.run = forever
            MockMS.return_value.run = forever
            MockPW.return_value.run = forever
            mock_session_factory.return_value = AsyncMock()

            await jm.start()
            await jm.stop()

            # stop() on the worker should have been called
            MockPW.return_value.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_message_handler_passes_llm_client(self):
        """build_message_handler() should pass llm_client to MessageAnalyzer."""
        from core.container import ServiceContainer

        sc = ServiceContainer()
        sc.llm_client = MagicMock()

        with patch("core.container.Analytics"), \
             patch("core.container.BoundaryManager"), \
             patch("core.container.QuestionTracker"), \
             patch("core.container.MessageAnalyzer") as MockMA, \
             patch("core.container.MessageHandler") as MockMH:
            MockMH.return_value = MagicMock()

            sc.build_message_handler(MagicMock())

            # MessageAnalyzer should have been called with llm_client
            call_kwargs = MockMA.call_args
            assert call_kwargs.kwargs.get("llm_client") is sc.llm_client


# =====================================================================
# 4. Regex-only MeetingExtractor sanity check (still works)
# =====================================================================

class TestRegexMeetingExtractor:
    """Ensure the original regex extractor hasn't been broken."""

    @pytest.fixture
    def extractor(self):
        from services.meeting_extractor import MeetingExtractor
        return MeetingExtractor()

    def test_detects_meeting_keyword_with_time(self, extractor):
        ref = datetime(2026, 2, 18, 10, 0)
        meetings = extractor.extract_meetings("I have a meeting at 3:00 PM", ref)
        assert len(meetings) >= 1
        assert meetings[0].start_time is not None

    def test_detects_appointment(self, extractor):
        meetings = extractor.extract_meetings("appointment tomorrow at 10:00 AM",
                                               datetime(2026, 2, 18, 9, 0))
        assert len(meetings) >= 1

    def test_no_false_positive_on_casual_chat(self, extractor):
        meetings = extractor.extract_meetings("I'm feeling great today, how about you?")
        assert meetings == []

    def test_returns_empty_for_empty_string(self, extractor):
        assert extractor.extract_meetings("") == []
        assert extractor.extract_meetings("   ") == []


# =====================================================================
# Run with: pytest tests/test_proactive_worker_and_llm_extractor.py -v
# =====================================================================
