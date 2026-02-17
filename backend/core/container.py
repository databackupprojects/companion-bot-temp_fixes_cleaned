import asyncio
import logging
import os
from typing import Optional, List

from database import AsyncSessionLocal
from handlers.command_handler import CommandHandler
from handlers.message_handler import MessageHandler
from jobs.daily_reset import DailyResetJob, DataCleanupJob
from jobs.memory_summarizer import MemorySummarizer
from jobs.proactive_meeting_checker import ProactiveMeetingChecker
from services.analytics import Analytics
from services.boundary_manager import BoundaryManager
from services.context_builder import ContextBuilder
from services.llm_client import OpenAILLMClient
from services.message_analyzer import MessageAnalyzer
from services.question_tracker import QuestionTracker

logger = logging.getLogger(__name__)


class JobManager:
    """Manage background jobs and lifecycle."""

    def __init__(self, llm_client: OpenAILLMClient):
        self.llm_client = llm_client
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self.daily_reset_job: Optional[DailyResetJob] = None
        self.data_cleanup_job: Optional[DataCleanupJob] = None
        self.memory_summarizer: Optional[MemorySummarizer] = None
        self.proactive_checker: Optional[ProactiveMeetingChecker] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        try:
            self.daily_reset_job = DailyResetJob(AsyncSessionLocal())
            self.data_cleanup_job = DataCleanupJob(AsyncSessionLocal())
            self.memory_summarizer = MemorySummarizer(AsyncSessionLocal(), self.llm_client)
            self.proactive_checker = ProactiveMeetingChecker()

            self._tasks.append(asyncio.create_task(self.daily_reset_job.run()))
            self._tasks.append(asyncio.create_task(self.data_cleanup_job.run()))
            self._tasks.append(asyncio.create_task(self.memory_summarizer.run()))
            self._tasks.append(asyncio.create_task(self._run_proactive_checker_loop()))

            logger.info("Background jobs started")
        except Exception:
            await self.stop()
            logger.exception("Failed to start background jobs")
            raise

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False

        for job in (self.daily_reset_job, self.data_cleanup_job, self.memory_summarizer):
            try:
                if job and hasattr(job, "stop"):
                    job.stop()
            except Exception:
                logger.exception("Error while stopping job")

        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Background jobs stopped")

    async def _run_proactive_checker_loop(self) -> None:
        interval_minutes = int(os.getenv("PROACTIVE_CHECK_INTERVAL_MINUTES", "5"))
        interval_seconds = max(60, interval_minutes * 60)

        while self._running:
            try:
                if self.proactive_checker:
                    await self.proactive_checker.check_and_send_reminders()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error("Proactive checker loop error: %s", exc, exc_info=True)
                await asyncio.sleep(60)


class ServiceContainer:
    """Centralized wiring for shared services."""

    def __init__(self):
        self.llm_client: Optional[OpenAILLMClient] = None
        self.job_manager: Optional[JobManager] = None
        self._started = False
        self._lock = asyncio.Lock()

    async def startup(self) -> None:
        if self._started:
            return
        async with self._lock:
            if self._started:
                return
            self.llm_client = OpenAILLMClient()
            self.job_manager = JobManager(self.llm_client)
            await self.job_manager.start()
            self._started = True
            logger.info("Service container initialized")

    async def shutdown(self) -> None:
        if not self._started:
            return
        if self.job_manager:
            await self.job_manager.stop()
        self._started = False
        logger.info("Service container shut down")

    def get_llm_client(self) -> OpenAILLMClient:
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")
        return self.llm_client

    def build_analytics(self, db_session) -> Analytics:
        return Analytics(db_session)

    def build_message_handler(self, db_session) -> MessageHandler:
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")
        analytics = self.build_analytics(db_session)
        boundary_manager = BoundaryManager(db_session)
        question_tracker = QuestionTracker(db_session)
        message_analyzer = MessageAnalyzer(db_session)
        return MessageHandler(
            db=db_session,
            llm_client=self.llm_client,
            context_builder_class=ContextBuilder,
            boundary_manager=boundary_manager,
            question_tracker=question_tracker,
            analytics=analytics,
            message_analyzer=message_analyzer,
        )

    def build_command_handler(self, db_session) -> CommandHandler:
        analytics = self.build_analytics(db_session)
        return CommandHandler(db_session, analytics)

    @property
    def is_ready(self) -> bool:
        return self._started


container = ServiceContainer()
