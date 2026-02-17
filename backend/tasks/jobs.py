# backend/tasks/jobs.py - Background Jobs
from celery import shared_task
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@shared_task
def run_daily_reset():
    """Run daily reset for all users."""
    from backend_services_v31.jobs.daily_reset import DailyResetJob
    # Implementation here
    logger.info("Running daily reset job")

@shared_task
def run_memory_summarization():
    """Run memory summarization job."""
    from backend_services_v31.jobs.memory_summarizer import MemorySummarizer
    # Implementation here
    logger.info("Running memory summarization job")

@shared_task
def run_data_cleanup():
    """Run data cleanup job."""
    from backend_services_v31.jobs.daily_reset import DataCleanupJob
    # Implementation here
    logger.info("Running data cleanup job")

@shared_task
def run_proactive_scheduler():
    """Run proactive message scheduler."""
    from backend_services_v31.services.proactive_scheduler import ProactiveWorker
    # Implementation here
    logger.info("Running proactive scheduler job")