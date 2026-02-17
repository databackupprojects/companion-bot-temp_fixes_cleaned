import uuid
from datetime import timedelta
from typing import Any, Dict

import bcrypt
import pytz
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import MESSAGE_LIMITS, PROACTIVE_LIMITS
from models.models import UserCreate, UserResponse
from models.sql_models import BotSettings, Message, User
from utils.timezone import get_utc_now, to_user_timezone


async def register_user(db: AsyncSession, user_create: UserCreate) -> UserResponse:
    existing_user = await db.execute(
        select(User).where((User.username == user_create.username) | (User.email == user_create.email))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    password_hash = (
        bcrypt.hashpw(user_create.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        if user_create.password
        else None
    )

    user = User(
        username=user_create.username,
        email=user_create.email,
        password_hash=password_hash,
        telegram_id=user_create.telegram_id,
        tier=user_create.tier or "free",
        timezone=user_create.timezone or "UTC",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    bot_settings = BotSettings(user_id=user.id)
    db.add(bot_settings)
    await db.commit()

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        tier=user.tier,
        telegram_id=user.telegram_id,
        messages_today=user.messages_today,
        proactive_count_today=user.proactive_count_today,
        last_active_at=user.last_active_at,
        timezone=user.timezone,
        spice_consent=user.spice_consent,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def current_user_info(current_user: User) -> Dict[str, Any]:
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "tier": current_user.tier,
        "messages_today": current_user.messages_today,
        "proactive_count_today": current_user.proactive_count_today,
        "telegram_id": current_user.telegram_id,
        "timezone": current_user.timezone,
        "spice_consent": current_user.spice_consent,
        "last_active_at": current_user.last_active_at.isoformat() if current_user.last_active_at else None,
        "created_at": current_user.created_at.isoformat(),
    }


async def get_settings(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(BotSettings).where(BotSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()

    if not settings:
        from constants import ARCHETYPE_DEFAULTS

        return {
            "bot_name": "Dot",
            "bot_gender": "female",
            "archetype": "golden_retriever",
            "attachment_style": "secure",
            "flirtiness": "subtle",
            "toxicity": "healthy",
            "tone_summary": None,
            "advanced_settings": ARCHETYPE_DEFAULTS.get("golden_retriever", {}),
        }

    return {
        "bot_name": settings.bot_name,
        "bot_gender": settings.bot_gender,
        "archetype": settings.archetype,
        "attachment_style": settings.attachment_style,
        "flirtiness": settings.flirtiness,
        "toxicity": settings.toxicity,
        "tone_summary": settings.tone_summary,
        "advanced_settings": settings.advanced_settings or {},
    }


async def update_settings(payload: Dict[str, Any], current_user: User, db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(BotSettings).where(BotSettings.user_id == current_user.id))
    bot_settings = result.scalar_one_or_none()

    if not bot_settings:
        bot_settings = BotSettings(user_id=current_user.id)
        db.add(bot_settings)

    for key, value in payload.items():
        if hasattr(bot_settings, key):
            setattr(bot_settings, key, value)

    await db.commit()
    return {"message": "Settings updated successfully"}


def get_limits(current_user: User) -> Dict[str, Any]:
    return {
        "tier": current_user.tier,
        "messages_today": current_user.messages_today,
        "message_limit": MESSAGE_LIMITS.get(current_user.tier, 20),
        "proactive_count_today": current_user.proactive_count_today,
        "proactive_limit": PROACTIVE_LIMITS.get(current_user.tier, 1),
        "remaining_messages": max(0, MESSAGE_LIMITS.get(current_user.tier, 20) - current_user.messages_today),
        "remaining_proactive": max(0, PROACTIVE_LIMITS.get(current_user.tier, 1) - current_user.proactive_count_today),
    }


async def update_consent(consent: bool, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    current_user.spice_consent = consent
    if consent:
        current_user.spice_consent_at = get_utc_now()

    await db.commit()
    return {"message": "Consent updated successfully"}


async def user_stats(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    message_count = await db.execute(select(func.count(Message.id)).where(Message.user_id == current_user.id))
    total_messages = message_count.scalar() or 0

    user_tz_now = to_user_timezone(get_utc_now(), current_user.timezone or "UTC")
    today_start_user = user_tz_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_start_user.astimezone(pytz.UTC).replace(tzinfo=None)
    today_messages = await db.execute(
        select(func.count(Message.id)).where(Message.user_id == current_user.id, Message.created_at >= today_start)
    )
    today_count = today_messages.scalar() or 0

    return {
        "total_messages": total_messages,
        "messages_today": today_count,
        "proactive_today": current_user.proactive_count_today,
        "days_active": 1,
        "avg_messages_per_day": total_messages / 30 if total_messages > 0 else 0,
    }


async def link_telegram(telegram_id: int, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    existing = await db.execute(select(User).where(User.telegram_id == telegram_id, User.id != current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Telegram ID already linked to another account")

    current_user.telegram_id = telegram_id
    await db.commit()

    return {"message": "Telegram account linked successfully", "telegram_id": telegram_id, "user_id": str(current_user.id)}


async def analytics(user_id: str, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    target_user_id = user_id or str(current_user.id)

    if not current_user.is_admin and str(current_user.id) != target_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_uuid = uuid.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    total_messages = await db.execute(select(func.count(Message.id)).where(Message.user_id == target_uuid))
    total_count = total_messages.scalar() or 0

    user = await db.get(User, target_uuid)
    user_tz = pytz.timezone(user.timezone or "UTC") if user else pytz.UTC

    user_tz_now = to_user_timezone(get_utc_now(), user.timezone or "UTC" if user else "UTC")
    today_start_user = user_tz_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_start_user.astimezone(pytz.UTC).replace(tzinfo=None)

    today_messages = await db.execute(
        select(func.count(Message.id)).where(Message.user_id == target_uuid, Message.created_at >= today_start)
    )
    today_count = today_messages.scalar() or 0

    week_start = today_start_user - timedelta(days=7)
    week_start_utc = week_start.astimezone(pytz.UTC).replace(tzinfo=None)
    weekly_messages = await db.execute(
        select(func.count(Message.id)).where(Message.user_id == target_uuid, Message.created_at >= week_start_utc)
    )
    weekly_count = weekly_messages.scalar() or 0

    month_start = today_start_user.replace(day=1)
    month_start_utc = month_start.astimezone(pytz.UTC).replace(tzinfo=None)
    monthly_messages = await db.execute(
        select(func.count(Message.id)).where(Message.user_id == target_uuid, Message.created_at >= month_start_utc)
    )
    monthly_count = monthly_messages.scalar() or 0

    return {
        "total_messages": total_count,
        "today_messages": today_count,
        "weekly_messages": weekly_count,
        "monthly_messages": monthly_count,
        "daily_limit": 50,
        "remaining_today": max(0, 50 - current_user.messages_today),
    }


def upgrade_info(current_user: User) -> Dict[str, Any]:
    return {
        "current_tier": current_user.tier,
        "features": {
            "free": {
                "messages_per_day": 50,
                "proactive_messages": 5,
                "memory_capacity": "Basic",
                "support": "Community",
            },
            "premium": {
                "messages_per_day": 200,
                "proactive_messages": 20,
                "memory_capacity": "Advanced",
                "support": "Priority",
                "price": "$9.99/month",
            },
        },
        "can_upgrade": current_user.tier == "free",
    }
