# backend/services/proactive_scheduler.py
"""
Proactive message scheduling system - COMPLETE VERSION
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import or_
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from constants import (
    ATTACHMENT_MODIFIERS,
    PROACTIVE_TEMPLATES,
    PROACTIVE_WORKER_INTERVAL_SECONDS,
    LATE_NIGHT_START_HOUR,
    LATE_NIGHT_END_HOUR,
    PROACTIVE_LIMITS,
    FEATURE_FLAGS,
)
from models.models import ProactiveMessageType, BlockReason
from models.sql_models import User, BotSettings, Message, ProactiveLog
from utils.chat_logger import chat_logger

logger = logging.getLogger(__name__)


class ProactiveScheduler:
    """
    7-gate proactive message system.
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        context_builder_class,
        llm_client,
        boundary_manager,
        analytics=None
    ):
        self.db = db
        self.ContextBuilder = context_builder_class
        self.llm = llm_client
        self.boundary_manager = boundary_manager
        self.analytics = analytics
    
    async def can_send(
        self, 
        user_id: str
    ) -> Tuple[bool, Optional[BlockReason], Optional[str]]:
        """
        7-GATE VALIDATION: All gates must pass.
        """
        
        # KILL SWITCH: Check if proactive is enabled
        if not FEATURE_FLAGS.get('proactive_enabled', True):
            return (False, BlockReason.LLM_ERROR, "proactive_disabled")
        
        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return (False, BlockReason.LLM_ERROR, "user_not_found")
        
        # Get settings - prefer primary bot if multiple bots exist
        settings_result = await self.db.execute(
            select(BotSettings)
            .where(BotSettings.user_id == user_id)
            .order_by(BotSettings.is_primary.desc(), BotSettings.created_at.asc())
        )
        settings = settings_result.scalars().first()
        
        attachment = settings.attachment_style if settings else 'secure'
        archetype = settings.archetype if settings else 'golden_retriever'
        
        # KILL SWITCH: Check if toxic_ex is disabled
        if archetype == 'toxic_ex' and not FEATURE_FLAGS.get('toxic_ex_enabled', True):
            return (False, BlockReason.LLM_ERROR, "toxic_ex_disabled")
        
        modifier = ATTACHMENT_MODIFIERS.get(
            attachment, 
            ATTACHMENT_MODIFIERS['secure']
        )
        
        # ==========================================
        # GATE 1: COOLDOWN (attachment-based)
        # ==========================================
        cooldown_hours = modifier['cooldown_hours']
        
        last_proactive_result = await self.db.execute(
            select(ProactiveLog.sent_at)
            .where(ProactiveLog.user_id == user_id)
            .order_by(ProactiveLog.sent_at.desc())
            .limit(1)
        )
        last_proactive = last_proactive_result.scalar_one_or_none()
        
        if last_proactive:
            hours_since = (datetime.utcnow() - last_proactive).total_seconds() / 3600
            if hours_since < cooldown_hours:
                return (
                    False, 
                    BlockReason.COOLDOWN_NOT_MET, 
                    f"{hours_since:.1f}h < {cooldown_hours}h"
                )
        
        # ==========================================
        # GATE 2: DAILY LIMIT (attachment + tier)
        # ==========================================
        tier = user.tier or 'free'
        tier_limit = PROACTIVE_LIMITS.get(tier, 1)
        attachment_limit = modifier['daily_max']
        daily_max = min(tier_limit, attachment_limit)
        
        if user.proactive_count_today >= daily_max:
            return (
                False, 
                BlockReason.DAILY_LIMIT_REACHED, 
                f"{user.proactive_count_today}/{daily_max}"
            )
        
        # ==========================================
        # GATE 3: PENDING QUESTIONS
        # ==========================================
        pending_result = await self.db.execute(
            select(Message.id)
            .where(
                Message.user_id == user_id,
                Message.role == 'bot',
                Message.is_question == True,
                Message.question_answered == False
            )
            .limit(1)
        )
        
        if pending_result.scalar_one_or_none():
            return (False, BlockReason.PENDING_QUESTIONS, "unanswered_questions")
        
        # ==========================================
        # GATE 4: SPACE BOUNDARY (24-hour hard stop)
        # ==========================================
        space_allowed, space_reason = await self.boundary_manager.check_space_allows_proactive(user_id)
        
        if not space_allowed:
            return (False, BlockReason.SPACE_BOUNDARY_HARD_STOP, space_reason)
        
        # ==========================================
        # GATE 5: TIME OF DAY
        # ==========================================
        user_tz = pytz.timezone(user.timezone or 'UTC')
        user_local_time = datetime.now(user_tz)
        hour = user_local_time.hour
        
        if hour >= LATE_NIGHT_START_HOUR or hour < LATE_NIGHT_END_HOUR:
            return (False, BlockReason.LATE_NIGHT, f"hour={hour}")
        
        # ==========================================
        # GATE 6: TIMING BOUNDARIES
        # ==========================================
        timing_boundaries = await self.boundary_manager.get_timing_boundaries(user_id)
        
        if "no_morning_messages" in timing_boundaries and 6 <= hour < 12:
            return (False, BlockReason.TIMING_BOUNDARY, "no_morning_messages")
        
        if "no_late_messages" in timing_boundaries and hour >= 20:
            return (False, BlockReason.TIMING_BOUNDARY, "no_late_messages")
        
        # ==========================================
        # GATE 7: ATTACHMENT PROBABILITY
        # ==========================================
        skip_prob = modifier['skip_probability']
        
        if skip_prob > 0 and random.random() < skip_prob:
            return (False, BlockReason.ATTACHMENT_SKIPPED, f"skipped_{attachment}")
        
        # All gates passed
        return (True, None, None)
    
    async def generate(self, user_id: str) -> Dict[str, Any]:
        """Generate a proactive message if all gates pass."""
        
        # Pre-check gates
        can_send, block_reason, details = await self.can_send(user_id)
        
        if not can_send:
            logger.debug(f"Proactive BLOCKED {user_id}: {block_reason}")
            
            # Track blocked event
            if self.analytics:
                await self.analytics.track(
                    event="proactive_blocked",
                    user_id=user_id,
                    properties={
                        "gate_failed": block_reason.value if block_reason else "unknown",
                        "reason": details or ""
                    }
                )
            
            return {
                "success": False,
                "block_reason": block_reason,
                "details": details
            }
        
        # Get settings for context - prefer primary bot if multiple bots exist
        settings_result = await self.db.execute(
            select(BotSettings)
            .where(BotSettings.user_id == user_id)
            .order_by(BotSettings.is_primary.desc(), BotSettings.created_at.asc())
        )
        settings = settings_result.scalars().first()
        
        attachment = settings.attachment_style if settings else 'secure'
        archetype = settings.archetype if settings else 'golden_retriever'
        modifier = ATTACHMENT_MODIFIERS.get(
            attachment, 
            ATTACHMENT_MODIFIERS['secure']
        )
        
        # Determine message type
        user_result = await self.db.execute(
            select(User.timezone).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        user_tz = pytz.timezone(user.timezone or 'UTC')
        hour = datetime.now(user_tz).hour
        msg_type = self._get_message_type(hour)
        
        # Try to use template first
        message = self._get_template_message(archetype, msg_type.value)
        
        if not message:
            # Fall back to LLM generation
            try:
                context_builder = self.ContextBuilder(self.db, user_id, archetype)
                context = await context_builder.build(
                    message_type="proactive",
                    attachment_hint=modifier['message_hint']
                )
                
                message = await self.llm.generate(context)
            except Exception as e:
                logger.error(f"LLM error: {e}")
                if self.analytics:
                    await self.analytics.track(
                        event="proactive_blocked",
                        user_id=user_id,
                        properties={
                            "gate_failed": "llm_error",
                            "reason": str(e)
                        }
                    )
                return {
                    "success": False,
                    "block_reason": BlockReason.LLM_ERROR,
                    "details": str(e)
                }
        
        # Check for NO_SEND
        if self._is_no_send(message):
            if self.analytics:
                await self.analytics.track(
                    event="proactive_blocked",
                    user_id=user_id,
                    properties={
                        "gate_failed": "llm_no_send",
                        "reason": "llm_decided_not_to_send"
                    }
                )
            return {
                "success": False,
                "block_reason": BlockReason.LLM_NO_SEND,
                "details": "llm_decided_not_to_send"
            }
        
        # Check for boundary violations
        violates, violated = await self.boundary_manager.check_message_violates(user_id, message)
        if violates:
            if self.analytics:
                await self.analytics.track(
                    event="proactive_blocked",
                    user_id=user_id,
                    properties={
                        "gate_failed": "boundary_violation",
                        "reason": f"violates: {violated}"
                    }
                )
            return {
                "success": False,
                "block_reason": BlockReason.BOUNDARY_VIOLATION,
                "details": f"violates: {violated}"
            }
        
        # Check if empty
        if not message or len(message.strip()) < 2:
            if self.analytics:
                await self.analytics.track(
                    event="proactive_blocked",
                    user_id=user_id,
                    properties={
                        "gate_failed": "empty_response",
                        "reason": "message_too_short"
                    }
                )
            return {
                "success": False,
                "block_reason": BlockReason.EMPTY_RESPONSE,
                "details": "message_too_short"
            }
        
        return {
            "success": True,
            "message": message,
            "message_type": msg_type.value,
            "archetype": archetype,
            "attachment_style": attachment
        }
    
    def _get_message_type(self, hour: int) -> ProactiveMessageType:
        """Determine message type based on hour."""
        if 6 <= hour < 12:
            return ProactiveMessageType.MORNING
        elif 12 <= hour < 18:
            return ProactiveMessageType.RANDOM
        else:
            return ProactiveMessageType.EVENING
    
    def _get_template_message(self, archetype: str, msg_type: str) -> Optional[str]:
        """Get template message for archetype and time."""
        templates = PROACTIVE_TEMPLATES.get(archetype, {})
        msgs = templates.get(msg_type, [])
        return random.choice(msgs) if msgs else None
    
    def _is_no_send(self, message: str) -> bool:
        """Check if LLM returned NO_SEND signal."""
        if not message:
            return True
        
        message_lower = message.lower().strip()
        return any(marker in message_lower for marker in ['[no_send]', 'no_send', 'dont send', "don't send"])
    
    async def send_proactive_message(
        self, 
        user_id: str, 
        message: str,
        message_type: str,
        archetype: str
    ) -> bool:
        """Send proactive message and log."""
        try:
            # Get user
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {user_id} not found for proactive")
                return False
            
            # Log the message to database
            log = ProactiveLog(
                user_id=user_id,
                message_content=message,
                message_category=f"{message_type}_{archetype}"
            )
            
            self.db.add(log)
            
            # Update user count
            user.proactive_count_today += 1
            
            await self.db.commit()
            
            # Send to Telegram if user has telegram_id
            if user.telegram_id:
                await self._send_to_telegram(user.telegram_id, message, archetype)

            # Log to chat log file
            chat_logger.log_proactive_message(
                user_id=str(user_id),
                username=user.username or user.email or "user",
                bot_id=archetype,
                bot_message=message,
                source="telegram"
            )

            # Track analytics
            if self.analytics:
                await self.analytics.proactive_sent(
                    user_id,
                    archetype,
                    message_type
                )

            logger.info(f"Proactive sent to {user_id}: {message[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to send proactive: {e}")
            await self.db.rollback()
            return False

    async def _send_to_telegram(self, telegram_id: int, message: str, archetype: str = 'golden_retriever') -> bool:
        """Send a message to a Telegram user using the correct bot."""
        try:
            from telegram import Bot
            from telegram.request import HTTPXRequest
            from constants import get_telegram_bot_token

            token = get_telegram_bot_token(archetype)
            if not token:
                logger.error(f"No token found for archetype {archetype}")
                return False

            request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0, write_timeout=20.0)
            bot = Bot(token=token, request=request)
            await bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Sent Telegram proactive to {telegram_id} via {archetype} bot")
            return True

        except Exception as e:
            logger.error(f"Error sending proactive to Telegram {telegram_id}: {e}")
            return False


class ProactiveWorker:
    """
    Worker that runs proactive scheduler periodically.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        context_builder_class,
        llm_client,
        boundary_manager,
        analytics=None
    ):
        self.db = db
        self.scheduler = ProactiveScheduler(
            db=db,
            context_builder_class=context_builder_class,
            llm_client=llm_client,
            boundary_manager=boundary_manager,
            analytics=analytics
        )
        self.running = False
    
    async def run(self):
        """Main worker loop."""
        self.running = True
        
        logger.info("[ProactiveWorker] Starting proactive worker")
        
        while self.running:
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"[ProactiveWorker] Cycle error: {e}", exc_info=True)
            
            await asyncio.sleep(PROACTIVE_WORKER_INTERVAL_SECONDS)
    
    async def _process_cycle(self):
        """Process one proactive cycle."""
        # Get all active users
        from models.sql_models import User
        
        users_result = await self.db.execute(
            select(User.id, User.is_active_today, User.proactive_count_today)
            .where(User.is_active == True)
            .limit(100)  # Process 100 users per cycle
        )
        users = users_result.fetchall()
        
        for user_id, is_active_today, proactive_count_today in users:
            try:
                # Generate proactive message
                result = await self.scheduler.generate(user_id)
                
                if result["success"]:
                    # Send the message
                    success = await self.scheduler.send_proactive_message(
                        user_id=user_id,
                        message=result["message"],
                        message_type=result["message_type"],
                        archetype=result["archetype"]
                    )
                    
                    if success:
                        logger.info(f"[ProactiveWorker] Sent proactive to {user_id}")
                    else:
                        logger.warning(f"[ProactiveWorker] Failed to send proactive to {user_id}")
                
            except Exception as e:
                logger.error(f"[ProactiveWorker] Error for user {user_id}: {e}")
    
    def stop(self):
        """Stop the worker."""
        self.running = False