# backend/jobs/proactive_meeting_checker.py
"""
Scheduled job to check for upcoming meetings and send proactive reminders.
This should run every 5 minutes to check:
1. Preparation reminders (30 minutes before meeting)
2. Completion messages (after meeting ends)
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from services.llm_client import OpenAILLMClient
from services.proactive_meeting_handler import ProactiveMeetingHandler

logger = logging.getLogger(__name__)


class ProactiveMeetingChecker:
    """Job to check and send proactive meeting messages."""
    
    def __init__(self):
        self.llm_client = None
        
    async def check_and_send_reminders(self):
        """Main job function - check meetings and send reminders."""
        logger.info("[ProactiveMeetingChecker] Starting meeting check cycle")
        
        async with AsyncSessionLocal() as db:
            try:
                # Initialize LLM client if not already done
                if not self.llm_client:
                    self.llm_client = OpenAILLMClient()
                
                # Create handler instance
                handler = ProactiveMeetingHandler(db, self.llm_client)
                
                # Check for preparation reminders
                logger.debug("[ProactiveMeetingChecker] Checking for preparation reminders...")
                prep_count = await handler.check_and_send_preparation_reminders()
                if prep_count > 0:
                    logger.info(f"[ProactiveMeetingChecker] Sent {prep_count} preparation reminder(s)")
                
                # Check for completion messages
                logger.debug("[ProactiveMeetingChecker] Checking for completion messages...")
                comp_count = await handler.check_and_send_completion_messages()
                if comp_count > 0:
                    logger.info(f"[ProactiveMeetingChecker] Sent {comp_count} completion message(s)")
                
                # Check for time-based greetings
                logger.debug("[ProactiveMeetingChecker] Checking for time-based greetings...")
                greeting_count = await handler.check_and_send_time_greetings()
                if greeting_count > 0:
                    logger.info(f"[ProactiveMeetingChecker] Sent {greeting_count} time-based greeting(s)")
                
                logger.info(f"[ProactiveMeetingChecker] Check complete - Prep: {prep_count}, Completion: {comp_count}, Greetings: {greeting_count}")
                
            except Exception as e:
                logger.error(f"[ProactiveMeetingChecker] Error during meeting check: {e}", exc_info=True)
                await db.rollback()


# Job execution function (called by scheduler)
async def run_proactive_meeting_checker():
    """Execute the proactive meeting checker job."""
    checker = ProactiveMeetingChecker()
    await checker.check_and_send_reminders()


# For manual testing
if __name__ == "__main__":
    asyncio.run(run_proactive_meeting_checker())
