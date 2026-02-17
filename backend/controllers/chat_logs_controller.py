import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from utils.chat_logger import ChatLogger


async def user_stats(chat_logger: ChatLogger, user_id: uuid.UUID, bot_id: Optional[str] = None) -> Dict[str, Any]:
    stats = chat_logger.get_user_stats(str(user_id), bot_id)
    return {
        "user_id": str(user_id),
        "bot_id": bot_id,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def chat_history(
    chat_logger: ChatLogger,
    user_id: uuid.UUID,
    username: str,
    bot_id: str,
    date: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    history = chat_logger.get_conversation_history(
        user_id=str(user_id), username=username, bot_id=bot_id, date=date, limit=limit
    )
    return {
        "user_id": str(user_id),
        "bot_id": bot_id,
        "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
        "conversations": history,
        "count": len(history),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def admin_stats(chat_logger: ChatLogger, target_user_id: str, admin_id: uuid.UUID) -> Dict[str, Any]:
    stats = chat_logger.get_user_stats(target_user_id)
    return {
        "user_id": target_user_id,
        "stats": stats,
        "requested_by": str(admin_id),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def logging_config(chat_logger: ChatLogger) -> Dict[str, Any]:
    message = (
        "Chat logging is enabled. Your conversations are being stored for improvement."
        if chat_logger.enabled
        else "Chat logging is disabled."
    )
    return {
        "enabled": chat_logger.enabled,
        "logs_dir": chat_logger.logs_dir if chat_logger.enabled else None,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
