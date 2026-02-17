# backend/routers/admin.py - Admin Endpoints with Role-Based Access Control
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from database import get_db
from models.sql_models import User
from models import TierSettingsCreate, TierSettingsUpdate, TierSettingsResponse
from utils.auth import get_current_admin_user
from controllers import admin_controller

router = APIRouter()

# ==========================================
# ADMIN ONLY ENDPOINTS (Require admin role)
# ==========================================

@router.get("/stats")
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get admin statistics (admin only)."""
    return await admin_controller.admin_stats(db)

@router.get("/users")
async def get_all_users(
    current_admin: User = Depends(get_current_admin_user),
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all users (admin only)."""
    return await admin_controller.list_users(db, limit, offset)

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed user information (admin only)."""
    return await admin_controller.user_details(db, user_id)

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Deactivate a user (admin only)."""
    return await admin_controller.deactivate_user(db, user_id)

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Activate a user (admin only)."""
    return await admin_controller.activate_user(db, user_id)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a user permanently (admin only)."""
    return await admin_controller.delete_user(db, user_id)

@router.get("/messages-stats")
async def get_messages_stats(
    current_admin: User = Depends(get_current_admin_user),
    days: int = 7,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get message statistics (admin only)."""
    return await admin_controller.messages_stats(db, days)

@router.post("/users/{user_id}/upgrade-tier")
async def upgrade_user_tier(
    user_id: str,
    new_tier: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Upgrade user tier (admin only)."""
    return await admin_controller.upgrade_tier(db, user_id, new_tier)
# ==========================================
# TIER SETTINGS MANAGEMENT (Admin Only)
# ==========================================

@router.get("/tier-settings", response_model=List[TierSettingsResponse])
async def get_tier_settings(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all tier settings (admin only)."""
    return await admin_controller.list_tier_settings(db)

@router.get("/tier-settings/{tier_name}", response_model=TierSettingsResponse)
async def get_tier_setting(
    tier_name: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific tier settings (admin only)."""
    return await admin_controller.get_tier_setting(db, tier_name)

@router.post("/tier-settings", response_model=TierSettingsResponse)
async def create_tier_setting(
    tier_data: TierSettingsCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new tier settings (admin only)."""
    return await admin_controller.create_tier_setting(db, tier_data)

@router.put("/tier-settings/{tier_name}", response_model=TierSettingsResponse)
async def update_tier_setting(
    tier_name: str,
    tier_data: TierSettingsUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update tier settings (admin only)."""
    return await admin_controller.update_tier_setting(db, tier_name, tier_data)

@router.delete("/tier-settings/{tier_name}")
async def delete_tier_setting(
    tier_name: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete tier settings (admin only)."""
    return await admin_controller.delete_tier_setting(db, tier_name)
