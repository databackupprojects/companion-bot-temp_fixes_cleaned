import uuid
from typing import Dict, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import ARCHETYPE_DEFAULTS
from models.sql_models import BotSettings, User
from models import BotSettingsUpdate, BotSettingsResponse
from utils.tone_generator import generate_tone_summary


async def get_settings(db: AsyncSession, user_id: str) -> BotSettingsResponse:
    target_user_id = _to_uuid(user_id)

    result = await db.execute(select(BotSettings).where(BotSettings.user_id == target_user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        settings = BotSettings(user_id=target_user_id, advanced_settings=ARCHETYPE_DEFAULTS.get("golden_retriever", {}))
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return _serialize(settings)


async def update_settings(db: AsyncSession, user_id: str, payload: BotSettingsUpdate) -> BotSettingsResponse:
    target_user_id = _to_uuid(user_id)

    user_result = await db.execute(select(User).where(User.id == target_user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(BotSettings).where(BotSettings.user_id == target_user_id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = BotSettings(user_id=target_user_id)
        db.add(settings)

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(settings, field):
            setattr(settings, field, value)

    if any(field in update_data for field in ["archetype", "attachment_style", "flirtiness", "toxicity"]):
        settings.tone_summary = generate_tone_summary(
            {
                "archetype": settings.archetype,
                "attachment_style": settings.attachment_style,
                "flirtiness": settings.flirtiness,
                "toxicity": settings.toxicity,
                "bot_name": settings.bot_name,
                "bot_gender": settings.bot_gender,
            }
        )

    await db.commit()
    await db.refresh(settings)
    return _serialize(settings)


async def get_advanced_settings(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    target_user_id = _to_uuid(user_id)

    result = await db.execute(select(BotSettings.advanced_settings).where(BotSettings.user_id == target_user_id))
    row = result.fetchone()
    if not row or not row[0]:
        return ARCHETYPE_DEFAULTS.get("golden_retriever", {})
    return row[0]


async def update_advanced_settings(db: AsyncSession, user_id: str, advanced_settings: Dict[str, Any]) -> Dict[str, Any]:
    target_user_id = _to_uuid(user_id)

    result = await db.execute(select(BotSettings).where(BotSettings.user_id == target_user_id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = BotSettings(user_id=target_user_id)
        db.add(settings)

    settings.advanced_settings = advanced_settings
    await db.commit()
    return {"message": "Advanced settings updated successfully"}


def _serialize(settings: BotSettings) -> BotSettingsResponse:
    return BotSettingsResponse.model_validate(settings)


def _to_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
