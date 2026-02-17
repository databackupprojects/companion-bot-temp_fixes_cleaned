import uuid
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import ARCHETYPE_DEFAULTS
from models import BotSettingsCreate, BotSettingsUpdate, BotSettingsResponse, BotListResponse
from models.sql_models import BotSettings, User, TierSettings, QuizConfig
from utils.tone_generator import generate_tone_summary


async def list_bots(db: AsyncSession, user_id: uuid.UUID) -> BotListResponse:
    result = await db.execute(
        select(BotSettings)
        .where(BotSettings.user_id == user_id)
        .order_by(BotSettings.is_primary.desc(), BotSettings.created_at.asc())
    )
    bot_settings_list = result.scalars().all()

    quiz_result = await db.execute(
        select(QuizConfig).where(QuizConfig.user_id == user_id).order_by(QuizConfig.created_at.desc())
    )
    quiz_configs = quiz_result.scalars().all()

    all_bots: List[BotSettings] = list(bot_settings_list)
    used_quiz_tokens = {bot.quiz_token for bot in bot_settings_list if bot.quiz_token}
    for idx, quiz_config in enumerate(quiz_configs):
        if quiz_config.token in used_quiz_tokens:
            continue
        config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
        bot = BotSettings(
            id=quiz_config.id,
            user_id=user_id,
            bot_name=config_data.get("bot_name", "Unnamed Bot"),
            bot_gender=config_data.get("bot_gender", "female"),
            archetype=config_data.get("archetype", "golden_retriever"),
            attachment_style=config_data.get("attachment_style", "secure"),
            flirtiness=config_data.get("flirtiness", "subtle"),
            toxicity=config_data.get("toxicity", "healthy"),
            tone_summary=quiz_config.tone_summary,
            is_active=True,
            is_primary=len(all_bots) == 0 and idx == 0,
            created_at=quiz_config.created_at,
            updated_at=quiz_config.created_at,
            advanced_settings=config_data.get(
                "advanced_settings", ARCHETYPE_DEFAULTS.get(config_data.get("archetype", "golden_retriever"), {})
            ),
        )
        all_bots.append(bot)

    if not all_bots:
        default_bot = BotSettings(
            user_id=user_id,
            is_primary=True,
            is_active=True,
            advanced_settings=ARCHETYPE_DEFAULTS.get("golden_retriever", {}),
        )
        db.add(default_bot)
        await db.commit()
        await db.refresh(default_bot)
        all_bots = [default_bot]

    primary_bot = next((bot for bot in all_bots if bot.is_primary), None)
    return BotListResponse(
        bots=[BotSettingsResponse.from_orm(bot) for bot in all_bots],
        total=len(all_bots),
        primary_bot_id=primary_bot.id if primary_bot else None,
    )


async def get_bot(db: AsyncSession, user_id: uuid.UUID, bot_id: uuid.UUID) -> BotSettingsResponse:
    result = await db.execute(
        select(BotSettings).where(BotSettings.id == bot_id, BotSettings.user_id == user_id)
    )
    bot = result.scalar_one_or_none()
    if bot:
        return BotSettingsResponse.from_orm(bot)

    quiz_result = await db.execute(select(QuizConfig).where(QuizConfig.id == bot_id, QuizConfig.user_id == user_id))
    quiz_config = quiz_result.scalar_one_or_none()
    if quiz_config:
        config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
        bot = BotSettings(
            id=quiz_config.id,
            user_id=user_id,
            bot_name=config_data.get("bot_name", "Unnamed Bot"),
            bot_gender=config_data.get("bot_gender", "female"),
            archetype=config_data.get("archetype", "golden_retriever"),
            attachment_style=config_data.get("attachment_style", "secure"),
            flirtiness=config_data.get("flirtiness", "subtle"),
            toxicity=config_data.get("toxicity", "healthy"),
            tone_summary=quiz_config.tone_summary,
            is_active=True,
            is_primary=False,
            created_at=quiz_config.created_at,
            updated_at=quiz_config.created_at,
            advanced_settings=config_data.get(
                "advanced_settings", ARCHETYPE_DEFAULTS.get(config_data.get("archetype", "golden_retriever"), {})
            ),
        )
        return BotSettingsResponse.from_orm(bot)

    raise HTTPException(status_code=404, detail="Bot not found")


async def create_bot(db: AsyncSession, user: User, payload: BotSettingsCreate) -> BotSettingsResponse:
    tier_result = await db.execute(select(TierSettings).where(TierSettings.tier_name == user.tier))
    tier_settings = tier_result.scalar_one_or_none()
    max_bots = tier_settings.max_bots if tier_settings else 1

    existing_result = await db.execute(
        select(BotSettings).where(BotSettings.user_id == user.id, BotSettings.is_active == True)
    )
    existing_bots = existing_result.scalars().all()
    if len(existing_bots) >= max_bots:
        raise HTTPException(status_code=403, detail=f"Maximum number of bots ({max_bots}) reached for your tier ({user.tier}). Upgrade to create more bots.")

    archetype_check = await db.execute(
        select(BotSettings).where(
            BotSettings.user_id == user.id,
            BotSettings.archetype == payload.archetype,
            BotSettings.is_active == True,
        )
    )
    if archetype_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have a bot with this archetype")

    tone_summary = generate_tone_summary(
        {
            "archetype": payload.archetype,
            "attachment_style": payload.attachment_style,
            "flirtiness": payload.flirtiness,
            "toxicity": payload.toxicity,
            "bot_name": payload.bot_name,
            "bot_gender": payload.bot_gender,
        }
    )

    new_bot = BotSettings(
        user_id=user.id,
        bot_name=payload.bot_name,
        bot_gender=payload.bot_gender,
        archetype=payload.archetype,
        attachment_style=payload.attachment_style,
        flirtiness=payload.flirtiness,
        toxicity=payload.toxicity,
        advanced_settings=payload.advanced_settings or ARCHETYPE_DEFAULTS.get(payload.archetype, {}),
        tone_summary=tone_summary,
        is_primary=len(existing_bots) == 0,
        is_active=True,
    )

    db.add(new_bot)
    await db.commit()
    await db.refresh(new_bot)
    return BotSettingsResponse.from_orm(new_bot)


async def update_bot(db: AsyncSession, user_id: uuid.UUID, bot_id: uuid.UUID, payload: BotSettingsUpdate) -> BotSettingsResponse:
    bot = await _get_or_promote_bot(db, user_id, bot_id)

    update_data = payload.dict(exclude_unset=True)
    if update_data.get("is_primary") is True:
        other_bots_result = await db.execute(
            select(BotSettings).where(BotSettings.user_id == user_id, BotSettings.id != bot_id)
        )
        for other_bot in other_bots_result.scalars():
            other_bot.is_primary = False

    for field, value in update_data.items():
        if hasattr(bot, field):
            setattr(bot, field, value)

    if any(field in update_data for field in ["attachment_style", "flirtiness", "toxicity", "bot_name", "bot_gender"]):
        bot.tone_summary = generate_tone_summary(
            {
                "archetype": bot.archetype,
                "attachment_style": bot.attachment_style,
                "flirtiness": bot.flirtiness,
                "toxicity": bot.toxicity,
                "bot_name": bot.bot_name,
                "bot_gender": bot.bot_gender,
            }
        )

    await db.commit()
    await db.refresh(bot)
    return BotSettingsResponse.from_orm(bot)


async def delete_bot(db: AsyncSession, user_id: uuid.UUID, bot_id: uuid.UUID) -> Dict[str, str]:
    result = await db.execute(select(BotSettings).where(BotSettings.id == bot_id, BotSettings.user_id == user_id))
    bot = result.scalar_one_or_none()

    if not bot:
        quiz_result = await db.execute(select(QuizConfig).where(QuizConfig.id == bot_id, QuizConfig.user_id == user_id))
        quiz_config = quiz_result.scalar_one_or_none()
        if not quiz_config:
            raise HTTPException(status_code=404, detail="Bot not found")
        await db.delete(quiz_config)
        await db.commit()
        return {"message": "Bot deleted successfully"}

    bot_settings_count = await db.execute(select(BotSettings).where(BotSettings.user_id == user_id))
    quiz_count = await db.execute(select(QuizConfig).where(QuizConfig.user_id == user_id))
    total_bots = len(bot_settings_count.scalars().all()) + len(quiz_count.scalars().all())
    if total_bots <= 1:
        raise HTTPException(status_code=403, detail="Cannot delete your last bot")

    if bot.is_primary:
        other_bots_result = await db.execute(
            select(BotSettings)
            .where(BotSettings.user_id == user_id, BotSettings.id != bot_id)
            .order_by(BotSettings.created_at.asc())
        )
        other_bot = other_bots_result.scalars().first()
        if other_bot:
            other_bot.is_primary = True

    await db.delete(bot)
    await db.commit()
    return {"message": "Bot deleted successfully"}


async def _get_or_promote_bot(db: AsyncSession, user_id: uuid.UUID, bot_id: uuid.UUID) -> BotSettings:
    result = await db.execute(select(BotSettings).where(BotSettings.id == bot_id, BotSettings.user_id == user_id))
    bot = result.scalar_one_or_none()
    if bot:
        return bot

    quiz_result = await db.execute(select(QuizConfig).where(QuizConfig.id == bot_id, QuizConfig.user_id == user_id))
    quiz_config = quiz_result.scalar_one_or_none()
    if not quiz_config:
        raise HTTPException(status_code=404, detail="Bot not found")

    config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
    bot = BotSettings(
        id=quiz_config.id,
        user_id=user_id,
        bot_name=config_data.get("bot_name", "Unnamed Bot"),
        bot_gender=config_data.get("bot_gender", "female"),
        archetype=config_data.get("archetype", "golden_retriever"),
        attachment_style=config_data.get("attachment_style", "secure"),
        flirtiness=config_data.get("flirtiness", "subtle"),
        toxicity=config_data.get("toxicity", "healthy"),
        tone_summary=quiz_config.tone_summary,
        is_active=True,
        is_primary=False,
        created_at=quiz_config.created_at,
        updated_at=quiz_config.created_at,
        advanced_settings=config_data.get(
            "advanced_settings", ARCHETYPE_DEFAULTS.get(config_data.get("archetype", "golden_retriever"), {})
        ),
    )
    db.add(bot)
    return bot
