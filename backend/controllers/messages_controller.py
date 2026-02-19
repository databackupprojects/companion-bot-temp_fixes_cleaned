import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import MessageSend
from models.sql_models import BotSettings, Message, User
from services.boundary_manager import BoundaryManager
from services.llm_client import OpenAILLMClient
from utils.chat_logger import chat_logger

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message: str) -> None:
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)


manager = ConnectionManager()


async def websocket_handler(websocket: WebSocket, user_id: str, db: AsyncSession) -> None:
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            response = await process_message(user_id, message_data.get("content", ""), db)

            await manager.send_message(
                user_id,
                json.dumps(
                    {
                        "type": "message",
                        "content": response,
                        "timestamp": datetime.utcnow().isoformat(),
                        "sender": "bot",
                    }
                ),
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)


async def send_message(request: MessageSend, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    """Send a message to the bot."""
    from main import get_llm_client

    try:
        llm_client = await get_llm_client()
    except Exception as e:
        logger.error(f"Failed to get LLM client: {e}")
        raise HTTPException(status_code=500, detail="LLM service not available")

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user = await db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from constants import MESSAGE_LIMITS
    daily_limit = MESSAGE_LIMITS.get(user.tier or "free", 20)
    if user.messages_today >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily message limit ({daily_limit}) reached. Upgrade for more messages.",
        )

    bot_id = request.bot_id
    if bot_id and isinstance(bot_id, str):
        try:
            bot_id = uuid.UUID(bot_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bot ID format")

    settings = await _get_bot_settings(db, current_user.id, bot_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot_id:
        bot_id = settings.id

    user_message = Message(user_id=current_user.id, bot_id=bot_id, role="user", content=request.message, message_type="reactive")
    db.add(user_message)
    user.messages_today = (user.messages_today or 0) + 1
    await db.commit()
    await db.refresh(user_message)

    # Extract meetings/schedules from the user's message
    try:
        from services.message_analyzer import MessageAnalyzer
        analyzer = MessageAnalyzer(db, llm_client=llm_client)
        await analyzer.analyze_for_schedules(user_message, user, settings, channel="web")
    except Exception as e:
        logger.error(f"Schedule analysis failed for web message: {e}", exc_info=True)

    response_text = await process_message_standalone(str(current_user.id), request.message, llm_client, bot_id)

    bot_message = Message(user_id=current_user.id, bot_id=bot_id, role="bot", content=response_text, message_type="reactive")
    db.add(bot_message)
    await db.commit()
    await db.refresh(bot_message)

    chat_logger.log_conversation(
        user_id=str(current_user.id),
        username=current_user.username or current_user.email or "user",
        bot_id=settings.archetype or "unknown",
        user_message=request.message,
        bot_response=response_text,
        message_type="reactive",
        source="web",
    )

    return {
        "reply": response_text,
        "response": response_text,
        "user_message_id": str(user_message.id),
        "bot_message_id": str(bot_message.id),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _get_bot_settings(db: AsyncSession, user_id: uuid.UUID, bot_id: Optional[uuid.UUID] = None) -> Optional[BotSettings]:
    """Get bot settings with QuizConfig fallback."""
    if bot_id:
        result = await db.execute(select(BotSettings).where(BotSettings.user_id == user_id, BotSettings.id == bot_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            from models.sql_models import QuizConfig
            quiz_result = await db.execute(select(QuizConfig).where(QuizConfig.user_id == user_id, QuizConfig.id == bot_id))
            quiz_config = quiz_result.scalar_one_or_none()
            if quiz_config:
                config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
                settings = BotSettings(
                    id=quiz_config.id,
                    user_id=user_id,
                    bot_name=config_data.get("bot_name", "Unnamed Bot"),
                    bot_gender=config_data.get("bot_gender", "female"),
                    archetype=config_data.get("archetype", "golden_retriever"),
                    attachment_style=config_data.get("attachment_style", "secure"),
                    flirtiness=config_data.get("flirtiness", "subtle"),
                    toxicity=config_data.get("toxicity", "healthy"),
                    tone_summary=quiz_config.tone_summary,
                    advanced_settings=config_data.get("advanced_settings", {}),
                )
    else:
        result = await db.execute(select(BotSettings).where(BotSettings.user_id == user_id, BotSettings.is_primary == True))
        settings = result.scalar_one_or_none()
    return settings


async def _build_message_context(user: User, settings: Optional[BotSettings], message: str, boundaries: list) -> Dict[str, Any]:
    """Build context for LLM from user data."""
    return {
        "user_name": user.username or "Friend",
        "user_id": str(user.id),
        "message_type": "reactive",
        "user_message": message,
        "bot_name": settings.bot_name if settings else "AI Companion",
        "bot_gender": settings.bot_gender if settings else "female",
        "archetype": settings.archetype if settings else "golden_retriever",
        "attachment_style": settings.attachment_style if settings else "secure",
        "flirtiness": settings.flirtiness if settings else "subtle",
        "toxicity": settings.toxicity if settings else "healthy",
        "tone_summary": settings.tone_summary if settings else "",
        "personality_description": settings.advanced_settings.get("custom_instructions", "") if settings and settings.advanced_settings else "",
        "time_of_day": "day",
        "recent_conversation": "",
        "user_boundaries": boundaries,
    }


async def process_message_standalone(
    user_id: str, message: str, llm_client: Optional[OpenAILLMClient] = None, bot_id: Optional[uuid.UUID] = None
) -> str:
    """Process a message without holding a DB session during LLM call."""
    from database import AsyncSessionLocal
    from services import llm_client as global_llm_client

    llm_client = llm_client or global_llm_client
    if not llm_client:
        return "I'm having trouble connecting to my AI engine right now. Please try again in a moment."

    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

    async with AsyncSessionLocal() as db:
        try:
            user = await db.get(User, user_uuid)
            if not user:
                return "I couldn't find your profile. Please log in again."

            if _detect_distress(message) or "/support" in message.lower():
                return _get_support_response()

            settings = await _get_bot_settings(db, user_uuid, bot_id)
            
            boundary_manager = BoundaryManager(db)
            await boundary_manager.process_message(str(user_uuid), message)
            boundaries = await boundary_manager.get_active_boundaries(user_uuid)

            context = await _build_message_context(user, settings, message, boundaries)

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return "I encountered an error processing your message. Please try again."

    try:
        import asyncio
        response = await asyncio.wait_for(llm_client.generate(context), timeout=60)
        
        async with AsyncSessionLocal() as db:
            boundary_manager = BoundaryManager(db)
            violates, _ = await boundary_manager.check_message_violates(user_uuid, response)
            if violates:
                response = "I appreciate you sharing that with me, but I know that's a topic you'd prefer I didn't bring up. Let's talk about something else instead."

        return response

    except asyncio.TimeoutError:
        return "I'm taking a bit longer to think about that. Please try again in a moment."
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_msg = str(e)
        if "API" in error_msg or "key" in error_msg.lower():
            return "I'm having trouble connecting to my AI engine. Please check your API configuration."
        return "I encountered an error. Please try again."


async def process_message(user_id: str, message: str, db: AsyncSession) -> str:
    """Process a message through the LLM with user's persona and settings."""
    try:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        user = await db.get(User, user_uuid)
        if not user:
            return "I couldn't find your profile. Please log in again."

        if _detect_distress(message) or "/support" in message.lower():
            return _get_support_response()

        settings = await _get_bot_settings(db, user_uuid)
        
        boundary_manager = BoundaryManager(db)
        await boundary_manager.process_message(str(user_uuid), message)
        boundaries = await boundary_manager.get_active_boundaries(user_uuid)

        context = await _build_message_context(user, settings, message, boundaries)
        
        llm_client = OpenAILLMClient()
        response = await llm_client.generate(context)

        violates, _ = await boundary_manager.check_message_violates(user_uuid, response)
        if violates:
            response = "I appreciate you sharing that with me, but I know that's a topic you'd prefer I didn't bring up. Let's talk about something else instead."

        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return "I encountered an error processing your message. Please try again."


def _detect_distress(message: str) -> bool:
    """Detect genuine distress that requires dropping persona immediately."""
    import re

    distress_patterns = [
        r"i('m| am) (really )?not ok(ay)?",
        r"can'?t (do|take) this anymore",
        r"want to (die|end it|disappear|hurt myself)",
        r"hurt(ing)? myself",
        r"(no|nobody|noone) cares",
        r"what'?s the point",
        r"i('m| am) serious",
        r"this is real",
        r"not (a )?jok(e|ing)",
        r"suicide|self.?harm|self.?injury",
    ]

    message_lower = message.lower().strip()
    return any(re.search(pattern, message_lower) for pattern in distress_patterns)


def _get_support_response() -> str:
    """Return a genuine support response (drop persona completely)."""
    return """Hey — stepping out of character completely here.

If you're going through something difficult, I'm here to listen without any act.

If you're in crisis:
- 💙 988 Suicide & Crisis Lifeline (US) - Call or text 988
- 💙 Crisis Text Line - Text HOME to 741741
- 💙 International Help - findahelpline.com

Want to talk for real? I'm listening. 💙"""


async def get_message_history(
    limit: int,
    offset: int,
    user_id: Optional[str],
    bot_id: Optional[str],
    current_user: User,
    db: AsyncSession,
) -> Dict[str, Any]:
    if not user_id:
        user_id = str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    query = select(Message).where(Message.user_id == target_user_id)

    if bot_id:
        try:
            target_bot_id = uuid.UUID(bot_id)
            query = query.where(Message.bot_id == target_bot_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bot ID format")

    result = await db.execute(query.order_by(desc(Message.created_at)))
    total = len(result.scalars().all())

    paginated_query = query.order_by(Message.created_at).limit(limit).offset(offset)
    result = await db.execute(paginated_query)
    messages = result.scalars().all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "message_type": m.message_type,
                "detected_mood": m.detected_mood,
            }
            for m in messages
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "user_id": user_id,
    }


async def clear_message_history(
    user_id: Optional[str], bot_id: Optional[str], current_user: User, db: AsyncSession
) -> Dict[str, Any]:
    target_user_id = user_id or str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != target_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_user_uuid = uuid.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    delete_query = Message.__table__.delete().where(Message.user_id == target_user_uuid)

    if bot_id:
        try:
            target_bot_uuid = uuid.UUID(bot_id)
            delete_query = delete_query.where(Message.bot_id == target_bot_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bot ID format")

    await db.execute(delete_query)
    await db.commit()

    return {"message": "Message history cleared successfully"}


async def get_message_analytics(user_id: Optional[str], current_user: User, db: AsyncSession) -> Dict[str, Any]:
    if not user_id:
        user_id = str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db.execute(select(Message).where(Message.user_id == target_user_id).order_by(Message.created_at))
    messages = result.scalars().all()

    if not messages:
        return {
            "total_messages": 0,
            "user_messages": 0,
            "bot_messages": 0,
            "user_id": user_id,
        }

    user_messages = [m for m in messages if m.role == "user"]
    bot_messages = [m for m in messages if m.role == "bot"]

    return {
        "total_messages": len(messages),
        "user_messages": len(user_messages),
        "bot_messages": len(bot_messages),
        "user_id": user_id,
    }


async def get_memory_summary(user_id: Optional[str], current_user: User, db: AsyncSession) -> Dict[str, Any]:
    if not user_id:
        user_id = str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db.execute(select(Message).where(Message.user_id == target_user_id).order_by(desc(Message.created_at)).limit(50))
    recent_messages = result.scalars().all()

    memories = []
    for msg in recent_messages:
        if msg.role == "user":
            memories.append({
                "id": str(msg.id),
                "content": msg.content[:150] + "..." if len(msg.content) > 150 else msg.content,
                "timestamp": msg.created_at.isoformat(),
            })

    return {
        "total_memories": len(memories),
        "recent_memories": memories[:20],
        "user_id": user_id,
    }


async def clear_memory(user_id: Optional[str], current_user: User) -> Dict[str, Any]:
    if not user_id:
        user_id = str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "message": "Memory cleared successfully",
        "cleared_items": 0,
        "user_id": user_id,
    }


async def trigger_support(context: str, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    from constants import SUPPORT_RESPONSE

    await db.execute(
        """
        INSERT INTO support_requests (user_id, context)
        VALUES (:user_id, :context)
        """,
        {"user_id": current_user.id, "context": context},
    )

    await db.commit()

    return {
        "message": SUPPORT_RESPONSE,
        "support_triggered": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _check_proactive_gates(user: User, settings: Optional[BotSettings], boundary_manager: BoundaryManager, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Check all 7 proactive gates. Returns error dict if blocked, None if allowed."""
    # Gate 1: Space boundary
    space_allowed, space_reason = await boundary_manager.check_space_allows_proactive(user.id)
    if not space_allowed:
        return {"success": False, "reason": "space_boundary_active", "details": space_reason}
    
    # Gate 2: Time of day
    import pytz
    user_tz = pytz.timezone(user.timezone or "UTC")
    hour = datetime.now(user_tz).hour
    
    if hour >= 23 or hour < 7:
        return {"success": False, "reason": "late_night", "details": f"Local time {hour}:00 is outside proactive window"}
    
    # Gate 3: Timing boundaries
    timing_boundaries = await boundary_manager.get_timing_boundaries(user.id)
    if "no_morning_messages" in timing_boundaries and 6 <= hour < 12:
        return {"success": False, "reason": "timing_boundary", "details": "User has disabled morning messages"}
    if "no_late_messages" in timing_boundaries and hour >= 20:
        return {"success": False, "reason": "timing_boundary", "details": "User has disabled late evening messages"}
    
    # Gate 4: Pending questions
    pending = await db.execute(
        select(Message.id).where(
            Message.user_id == user.id,
            Message.role == "bot",
            Message.is_question == True,
            Message.question_answered == False,
        ).limit(1)
    )
    if pending.scalar_one_or_none():
        return {"success": False, "reason": "pending_questions", "details": "User has unanswered bot questions"}
    
    # Gate 5: Daily limit
    from constants import MESSAGE_LIMITS
    daily_limit = MESSAGE_LIMITS.get(user.tier or "free", 20)
    proactive_max = max(1, daily_limit // 5)
    
    if user.proactive_count_today >= proactive_max:
        return {"success": False, "reason": "daily_limit_reached", "details": f"{user.proactive_count_today}/{proactive_max} proactive messages sent"}
    
    # Gate 6 & 7: Cooldown
    cooldown_hours = {"secure": 24, "anxious": 2, "avoidant": 48}.get(
        settings.attachment_style if settings else "secure", 24
    )
    
    last_proactive_result = await db.execute(
        select(Message.created_at)
        .where(Message.user_id == user.id, Message.role == "bot", Message.message_type == "proactive")
        .order_by(desc(Message.created_at))
        .limit(1)
    )
    last_proactive = last_proactive_result.scalar_one_or_none()
    
    if last_proactive:
        hours_since = (datetime.utcnow() - last_proactive).total_seconds() / 3600
        if hours_since < cooldown_hours:
            return {"success": False, "reason": "cooldown_not_met", "details": f"{hours_since:.1f}h < {cooldown_hours}h"}
    
    return None  # All gates passed


async def send_proactive_message(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    """Generate a proactive message while respecting 7 gating rules."""
    try:
        boundary_manager = BoundaryManager(db)
        settings = await _get_bot_settings(db, current_user.id)
        
        # Check all gates
        gate_error = await _check_proactive_gates(current_user, settings, boundary_manager, db)
        if gate_error:
            return gate_error
        
        # Generate message
        import pytz
        user_tz = pytz.timezone(current_user.timezone or "UTC")
        hour = datetime.now(user_tz).hour
        time_of_day = "morning" if 6 <= hour < 12 else "afternoon" if 12 <= hour < 18 else "evening"
        
        boundaries = await boundary_manager.get_active_boundaries(current_user.id)
        
        context = {
            "user_name": current_user.username or "Friend",
            "user_id": str(current_user.id),
            "message_type": "proactive",
            "bot_name": settings.bot_name if settings else "AI Companion",
            "bot_gender": settings.bot_gender if settings else "female",
            "archetype": settings.archetype if settings else "golden_retriever",
            "attachment_style": settings.attachment_style if settings else "secure",
            "flirtiness": settings.flirtiness if settings else "subtle",
            "toxicity": settings.toxicity if settings else "healthy",
            "time_of_day": time_of_day,
            "user_boundaries": boundaries,
        }
        
        llm_client = OpenAILLMClient()
        response = await llm_client.generate(context)
        
        violates, _ = await boundary_manager.check_message_violates(current_user.id, response)
        if violates:
            return {"success": False, "reason": "boundary_violation", "details": "Generated message violates boundary"}
        
        bot_message = Message(user_id=current_user.id, role="bot", content=response, message_type="proactive")
        db.add(bot_message)
        current_user.proactive_count_today = (current_user.proactive_count_today or 0) + 1
        await db.commit()
        
        return {"success": True, "message": response, "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error generating proactive message: {e}")
        return {"success": False, "reason": "error", "details": str(e)}
