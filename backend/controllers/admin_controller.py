import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.sql_models import User, Message, BotSettings, TierSettings
from models import TierSettingsCreate, TierSettingsUpdate, TierSettingsResponse


async def admin_stats(db: AsyncSession) -> Dict[str, Any]:
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.last_active_at >= today_start))
    ).scalar() or 0

    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0

    archetype_distribution = dict(
        (await db.execute(select(BotSettings.archetype, func.count(BotSettings.id)).group_by(BotSettings.archetype))).all()
    )

    admin_count = (
        await db.execute(select(func.count(User.id)).where(User.role == "admin"))
    ).scalar() or 0

    return {
        "total_users": user_count,
        "active_users_today": active_users,
        "total_messages": total_messages,
        "admin_count": admin_count,
        "archetype_distribution": archetype_distribution,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def list_users(db: AsyncSession, limit: int, offset: int) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    return [
        {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tier": user.tier,
            "messages_today": user.messages_today,
            "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


async def user_details(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    user = await _get_user_or_404(db, user_id)

    message_count = (
        await db.execute(select(func.count(Message.id)).where(Message.user_id == user.id))
    ).scalar() or 0

    settings_result = await db.execute(select(BotSettings).where(BotSettings.user_id == user.id))
    settings = settings_result.scalar_one_or_none()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "is_active": user.is_active,
        "telegram_id": user.telegram_id,
        "messages_today": user.messages_today,
        "total_messages": message_count,
        "proactive_count_today": user.proactive_count_today,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "timezone": user.timezone,
        "spice_consent": user.spice_consent,
        "bot_settings": _serialize_bot_settings(settings),
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


async def deactivate_user(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    user = await _get_user_or_404(db, user_id)
    _assert_not_admin(user)
    user.is_active = False
    await db.commit()
    return {"message": f"User {user.username} deactivated successfully"}


async def activate_user(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    user = await _get_user_or_404(db, user_id)
    user.is_active = True
    await db.commit()
    return {"message": f"User {user.username} activated successfully"}


async def delete_user(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    user = await _get_user_or_404(db, user_id)
    _assert_not_admin(user)
    username = user.username
    email = user.email
    await db.delete(user)
    await db.commit()
    return {"message": f"User {username} ({email}) deleted permanently", "deleted_user_id": user_id}


async def messages_stats(db: AsyncSession, days: int) -> Dict[str, Any]:
    start_date = datetime.utcnow() - timedelta(days=days)

    total_messages = (
        await db.execute(select(func.count(Message.id)).where(Message.created_at >= start_date))
    ).scalar() or 0

    messages_by_type = dict(
        (
            await db.execute(
                select(Message.message_type, func.count(Message.id))
                .where(Message.created_at >= start_date)
                .group_by(Message.message_type)
            )
        ).all()
    )

    top_users_rows = (
        await db.execute(
            select(User.username, func.count(Message.id).label("message_count"))
            .join(Message, User.id == Message.user_id)
            .where(Message.created_at >= start_date)
            .group_by(User.id, User.username)
            .order_by(func.count(Message.id).desc())
            .limit(10)
        )
    ).all()
    top_users = [{"username": row[0], "message_count": row[1]} for row in top_users_rows]

    return {
        "period_days": days,
        "total_messages": total_messages,
        "messages_by_type": messages_by_type,
        "top_users": top_users,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
    }


async def upgrade_tier(db: AsyncSession, user_id: str, new_tier: str) -> Dict[str, Any]:
    valid_tiers = ["free", "pro", "premium"]
    if new_tier not in valid_tiers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tier. Must be one of {valid_tiers}")

    user = await _get_user_or_404(db, user_id)

    old_tier = user.tier
    user.tier = new_tier
    if new_tier == "premium":
        user.tier_expires_at = datetime.utcnow() + timedelta(days=365)
    elif new_tier == "pro":
        user.tier_expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        user.tier_expires_at = None

    await db.commit()
    return {
        "message": f"User tier upgraded from {old_tier} to {new_tier}",
        "user_id": str(user.id),
        "new_tier": user.tier,
        "expires_at": user.tier_expires_at.isoformat() if user.tier_expires_at else None,
    }


async def list_tier_settings(db: AsyncSession) -> List[TierSettingsResponse]:
    result = await db.execute(select(TierSettings).order_by(TierSettings.max_bots.asc()))
    settings = result.scalars().all()
    return [TierSettingsResponse.from_orm(s) for s in settings]


async def get_tier_setting(db: AsyncSession, tier_name: str) -> TierSettingsResponse:
    setting = await _get_tier_or_404(db, tier_name)
    return TierSettingsResponse.from_orm(setting)


async def create_tier_setting(db: AsyncSession, tier_data: TierSettingsCreate) -> TierSettingsResponse:
    exists = (
        await db.execute(select(TierSettings).where(TierSettings.tier_name == tier_data.tier_name))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail=f"Tier '{tier_data.tier_name}' already exists")

    new_setting = TierSettings(
        tier_name=tier_data.tier_name,
        max_bots=tier_data.max_bots,
        max_messages_per_day=tier_data.max_messages_per_day,
        max_proactive_per_day=tier_data.max_proactive_per_day,
        features=tier_data.features,
    )
    db.add(new_setting)
    await db.commit()
    await db.refresh(new_setting)
    return TierSettingsResponse.from_orm(new_setting)


async def update_tier_setting(db: AsyncSession, tier_name: str, tier_data: TierSettingsUpdate) -> TierSettingsResponse:
    setting = await _get_tier_or_404(db, tier_name)
    for field, value in tier_data.dict(exclude_unset=True).items():
        setattr(setting, field, value)
    await db.commit()
    await db.refresh(setting)
    return TierSettingsResponse.from_orm(setting)


async def delete_tier_setting(db: AsyncSession, tier_name: str) -> Dict[str, str]:
    if tier_name in ["free", "plus", "premium"]:
        raise HTTPException(status_code=403, detail="Cannot delete default tier settings. You can only update them.")
    setting = await _get_tier_or_404(db, tier_name)
    await db.delete(setting)
    await db.commit()
    return {"message": f"Tier '{tier_name}' deleted successfully"}


def _serialize_bot_settings(settings: Optional[BotSettings]) -> Optional[Dict[str, Any]]:
    if not settings:
        return None
    return {
        "bot_name": settings.bot_name,
        "bot_gender": settings.bot_gender,
        "archetype": settings.archetype,
        "attachment_style": settings.attachment_style,
        "flirtiness": settings.flirtiness,
        "toxicity": settings.toxicity,
    }


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _get_tier_or_404(db: AsyncSession, tier_name: str) -> TierSettings:
    result = await db.execute(select(TierSettings).where(TierSettings.tier_name == tier_name))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Tier settings not found")
    return setting


def _assert_not_admin(user: User) -> None:
    if user.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify admin users")
