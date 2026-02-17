import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def get_or_create_user(
    db,
    telegram_id: int,
    archetype: Optional[str] = None,
    bot_defaults: Optional[Dict[str, Any]] = None,
    log_context: str = "",
) -> Dict[str, Any]:
    """Fetch a user by telegram_id or create a new one with optional bot defaults."""
    from sqlalchemy import select
    from models.sql_models import User, BotSettings

    try:
        try:
            await db.rollback()
        except Exception:
            pass

        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return {
                "id": str(user.id),
                "telegram_id": user.telegram_id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "tier": user.tier,
                "timezone": user.timezone,
                "spice_consent": user.spice_consent,
                "messages_today": user.messages_today,
                "proactive_count_today": user.proactive_count_today,
                "last_active_at": user.last_active_at,
                "is_active_today": user.is_active_today,
            }

        archetype_value = archetype or "golden_retriever"
        new_user = User(
            telegram_id=telegram_id,
            tier="free",
            timezone="UTC",
            spice_consent=False,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        bot_kwargs = {"user_id": new_user.id, "archetype": archetype_value}
        if bot_defaults:
            bot_kwargs.update({k: v for k, v in bot_defaults.items() if v is not None})

        try:
            bot_settings = BotSettings(**bot_kwargs)
            db.add(bot_settings)
            await db.commit()
        except Exception as bot_err:
            await db.rollback()
            logger.error("%sFailed to create bot settings for user %s: %s", log_context, new_user.id, bot_err, exc_info=True)

        logger.info("%sCreated new user %s with archetype %s", log_context, new_user.id, archetype_value)

        return {
            "id": str(new_user.id),
            "telegram_id": telegram_id,
            "username": None,
            "name": None,
            "email": None,
            "tier": "free",
            "timezone": "UTC",
            "spice_consent": False,
            "messages_today": 0,
            "proactive_count_today": 0,
            "last_active_at": None,
            "is_active_today": False,
        }

    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.error("%sError in get_or_create_user: %s", log_context, exc, exc_info=True)
        raise
