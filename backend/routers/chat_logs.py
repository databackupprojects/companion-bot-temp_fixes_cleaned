# backend/routers/chat_logs.py - Chat Logs Endpoints
"""Endpoints for accessing chat logs and statistics."""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from controllers import chat_logs_controller
from models.sql_models import User
from utils.auth import get_current_admin_user, get_current_user
from utils.chat_logger import chat_logger

router = APIRouter()

@router.get("/stats")
async def get_my_chat_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get chat logging statistics for current user."""
    return await chat_logs_controller.user_stats(chat_logger, current_user.id)

@router.get("/stats/{bot_id}")
async def get_bot_chat_stats(
    bot_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get chat logging statistics for a specific bot."""
    return await chat_logs_controller.user_stats(chat_logger, current_user.id, bot_id)

@router.get("/history/{bot_id}")
async def get_chat_history_from_logs(
    bot_id: str,
    date: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get chat history from logs for a specific bot."""
    if limit > 500:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 500")

    username = current_user.username or current_user.email or "user"
    return await chat_logs_controller.chat_history(
        chat_logger,
        current_user.id,
        username,
        bot_id,
        date,
        limit,
    )

@router.get("/admin/stats/{user_id}")
async def admin_get_user_stats(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Admin endpoint: Get chat stats for any user."""
    return await chat_logs_controller.admin_stats(chat_logger, user_id, current_admin.id)

@router.get("/config")
async def get_logging_config(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current chat logging configuration."""
    return await chat_logs_controller.logging_config(chat_logger)
