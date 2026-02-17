# backend/routers/settings.py
"""
Bot settings management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from database import get_db
from models.sql_models import User
from models import BotSettingsUpdate, BotSettingsResponse
from constants import ARCHETYPE_DEFAULTS
from routers.auth import get_current_user
from controllers import settings_controller

router = APIRouter()

@router.get("/", response_model=BotSettingsResponse)
async def get_settings(
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotSettingsResponse:
    """Get bot settings for a user."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await settings_controller.get_settings(db, user_id)

@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    settings_update: BotSettingsUpdate,
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotSettingsResponse:
    """Update bot settings."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await settings_controller.update_settings(db, user_id, settings_update)

@router.get("/advanced")
async def get_advanced_settings(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get advanced settings only."""
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await settings_controller.get_advanced_settings(db, user_id)

@router.put("/advanced")
async def update_advanced_settings(
    user_id: str,
    advanced_settings: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update advanced settings."""
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await settings_controller.update_advanced_settings(db, user_id, advanced_settings)