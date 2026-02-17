# backend/routers/users.py - WITH SECURITY
"""User management endpoints with security."""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers import users_controller
from database import get_db
from models.sql_models import User
from models.models import UserCreate, UserResponse
from routers.auth import get_current_user

router = APIRouter()

# ==========================================
# PUBLIC ENDPOINTS
# ==========================================

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new web user."""
    return await users_controller.register_user(db, user_create)

# ==========================================
# PROTECTED ENDPOINTS (Require Authentication)
# ==========================================

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get current user information (requires auth)."""
    return users_controller.current_user_info(current_user)

@router.get("/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's bot settings (requires auth)."""
    return await users_controller.get_settings(current_user, db)

@router.put("/settings")
async def update_user_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update user's bot settings (requires auth)."""
    return await users_controller.update_settings(settings, current_user, db)

@router.get("/limits")
async def get_user_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's current limits (requires auth)."""
    return users_controller.get_limits(current_user)

@router.post("/consent")
async def update_consent(
    consent: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update user's spice consent (requires auth)."""
    return await users_controller.update_consent(consent, current_user, db)

@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user statistics (requires auth)."""
    return await users_controller.user_stats(current_user, db)

@router.post("/link-telegram")
async def link_telegram_account(
    telegram_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Link Telegram account to web user (requires auth)."""
    return await users_controller.link_telegram(telegram_id, current_user, db)

@router.get("/analytics")
async def get_user_analytics(
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's analytics data (requires auth)."""
    return await users_controller.analytics(user_id, current_user, db)

@router.get("/upgrade")
async def get_upgrade_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get upgrade/pricing information (requires auth)."""
    return users_controller.upgrade_info(current_user)