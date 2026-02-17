import base64
import io
import json
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

import qrcode
from fastapi import HTTPException, status
from PIL import Image  # noqa: F401  # PIL required for qrcode image generation
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import FIRST_MESSAGES, QUIZ_TOKEN_EXPIRY_HOURS, get_telegram_deep_link
from models import QuizData
from models.models import Toxicity
from models.sql_models import BotSettings, QuizConfig, User
from utils.tone_generator import generate_tone_summary
from utils.timezone import get_utc_now


async def list_user_bots(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    from models.sql_models import BotSettings as Settings

    bot_settings_result = await db.execute(
        select(Settings).where(Settings.user_id == current_user.id).order_by(Settings.created_at.desc())
    )
    bot_settings_list = bot_settings_result.scalars().all()

    quiz_result = await db.execute(
        select(QuizConfig).where(QuizConfig.user_id == current_user.id).order_by(QuizConfig.created_at.desc())
    )
    quiz_configs = quiz_result.scalars().all()

    bots = []
    used_quiz_tokens = {settings.quiz_token for settings in bot_settings_list if settings.quiz_token}

    for settings in bot_settings_list:
        bots.append(
            {
                "id": str(settings.id),
                "bot_name": settings.bot_name or "Unnamed Bot",
                "archetype": settings.archetype or "golden_retriever",
                "bot_gender": settings.bot_gender or "female",
                "attachment_style": settings.attachment_style or "secure",
                "flirtiness": settings.flirtiness or "subtle",
                "toxicity": settings.toxicity or "healthy",
                "created_at": settings.created_at.isoformat() if settings.created_at else None,
                "token": settings.quiz_token,
                "is_active": settings.is_active,
                "tone_summary": settings.tone_summary,
            }
        )

    for config in quiz_configs:
        if config.token not in used_quiz_tokens:
            config_data = config.config_data if isinstance(config.config_data, dict) else {}
            bots.append(
                {
                    "id": str(config.id),
                    "bot_name": config_data.get("bot_name", "Unnamed Bot"),
                    "archetype": config_data.get("archetype", "golden_retriever"),
                    "bot_gender": config_data.get("bot_gender", "female"),
                    "attachment_style": config_data.get("attachment_style", "secure"),
                    "flirtiness": config_data.get("flirtiness", "subtle"),
                    "toxicity": config_data.get("toxicity", "healthy"),
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "token": config.token,
                    "is_active": True,
                    "tone_summary": config.tone_summary,
                }
            )

    return {"bots": bots, "count": len(bots), "tier": current_user.tier}


def start_quiz_session() -> Dict[str, Any]:
    session_token = secrets.token_urlsafe(16)
    return {"session_token": session_token, "message": "Quiz started. Use this token for subsequent steps.", "expires_in": "24 hours"}


def submit_step(step_number: int, data: Dict[str, Any], session_token: str) -> Dict[str, Any]:
    if step_number == 1:
        if "user_name" not in data:
            raise HTTPException(status_code=400, detail="user_name is required")
        return {"message": "Step 1 completed"}
    if step_number == 2:
        valid_genders = ["female", "male", "nonbinary"]
        if "bot_gender" not in data or data["bot_gender"] not in valid_genders:
            raise HTTPException(status_code=400, detail=f"bot_gender must be one of {valid_genders}")
        return {"message": "Step 2 completed"}
    if step_number == 3:
        valid_archetypes = ["golden_retriever", "tsundere", "lawyer", "cool_girl", "toxic_ex"]
        if "archetype" not in data or data["archetype"] not in valid_archetypes:
            raise HTTPException(status_code=400, detail=f"archetype must be one of {valid_archetypes}")
        from constants import NAME_SUGGESTIONS

        suggestions = NAME_SUGGESTIONS.get(data["archetype"], {}).get(data.get("bot_gender", "female"), [])
        return {"message": "Step 3 completed", "name_suggestions": suggestions[:5]}
    if step_number == 4:
        if "bot_name" not in data or not data["bot_name"].strip():
            raise HTTPException(status_code=400, detail="bot_name is required")
        return {"message": "Step 4 completed"}
    if step_number == 5:
        valid_styles = ["secure", "anxious", "avoidant"]
        if "attachment_style" not in data or data["attachment_style"] not in valid_styles:
            raise HTTPException(status_code=400, detail=f"attachment_style must be one of {valid_styles}")
        return {"message": "Step 5 completed"}
    if step_number == 6:
        valid_levels = ["none", "subtle", "flirty"]
        if "flirtiness" not in data or data["flirtiness"] not in valid_levels:
            raise HTTPException(status_code=400, detail=f"flirtiness must be one of {valid_levels}")
        return {"message": "Step 6 completed"}
    if step_number == 7:
        valid_levels = ["healthy", "mild", "toxic_light"]
        if "toxicity" not in data or data["toxicity"] not in valid_levels:
            raise HTTPException(status_code=400, detail=f"toxicity must be one of {valid_levels}")
        if data["toxicity"] == "toxic_light" and ("spice_consent" not in data or not data["spice_consent"]):
            raise HTTPException(status_code=400, detail="spice_consent is required for toxic_light")
        return {"message": "Step 7 completed"}

    raise HTTPException(status_code=400, detail=f"Invalid step number: {step_number}")


async def can_create_bot(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    quiz_result = await db.execute(select(QuizConfig).where(QuizConfig.user_id == current_user.id))
    quiz_bots = quiz_result.scalars().all()

    bot_settings_result = await db.execute(select(BotSettings).where(BotSettings.user_id == current_user.id))
    bot_settings_bots = bot_settings_result.scalars().all()

    all_bots = list(quiz_bots) + list(bot_settings_bots)
    bot_count = len(all_bots)

    used_archetypes = []
    for bot in all_bots:
        archetype = None
        if hasattr(bot, "archetype") and bot.archetype:
            archetype = bot.archetype
        elif hasattr(bot, "config_data") and bot.config_data:
            if isinstance(bot.config_data, dict):
                archetype = bot.config_data.get("archetype")
            elif isinstance(bot.config_data, str):
                try:
                    config = json.loads(bot.config_data)
                    archetype = config.get("archetype")
                except Exception:
                    archetype = None
        if archetype:
            used_archetypes.append(archetype)

    used_archetypes = list(set(used_archetypes))

    if current_user.tier == "premium":
        max_bots = 5
    elif current_user.tier == "plus":
        max_bots = 3
    else:
        max_bots = 1

    can_create = bot_count < max_bots
    return {
        "can_create": can_create,
        "bot_count": bot_count,
        "max_bots": max_bots,
        "tier": current_user.tier,
        "used_archetypes": used_archetypes,
        "message": (
            f"You can create {max_bots - bot_count} more bot(s)"
            if can_create
            else f"{current_user.tier.title()} tier users can create up to {max_bots} AI companion(s). Upgrade to create more."
        ),
    }


async def complete_quiz(quiz_data: QuizData, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(func.count(QuizConfig.id)).where(QuizConfig.user_id == current_user.id))
    bot_count = result.scalar() or 0

    if current_user.tier == "premium":
        max_bots = 10
    elif current_user.tier == "plus":
        max_bots = 3
    else:
        max_bots = 1

    if bot_count >= max_bots:
        raise HTTPException(
            status_code=403,
            detail=f"{current_user.tier.title()} tier users can create up to {max_bots} AI companion(s). Upgrade to create more.",
        )

    if quiz_data.toxicity == Toxicity.TOXIC_LIGHT and not quiz_data.spice_consent:
        raise HTTPException(status_code=400, detail="spice_consent is required for toxic_light toxicity")

    if quiz_data.timezone:
        current_user.timezone = quiz_data.timezone
        await db.commit()

    settings_dict = quiz_data.dict()
    tone_summary = generate_tone_summary(settings_dict)

    token = secrets.token_urlsafe(16)
    expires_at = get_utc_now() + timedelta(hours=24)

    quiz_config = QuizConfig(
        token=token,
        user_id=current_user.id,
        config_data=quiz_data.dict(),
        tone_summary=tone_summary,
        expires_at=expires_at,
    )

    db.add(quiz_config)
    await db.commit()

    deep_link = get_telegram_deep_link(quiz_data.archetype.value, token)

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(deep_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {
        "token": token,
        "deep_link": deep_link,
        "qr_code": f"data:image/png;base64,{qr_code_base64}",
        "bot_name": quiz_data.bot_name,
        "archetype": quiz_data.archetype.value,
        "first_message": FIRST_MESSAGES.get(quiz_data.archetype.value, "Hey!").format(user_name=quiz_data.user_name),
        "expires_at": expires_at.isoformat(),
    }


async def get_config(token: str, db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(
        select(QuizConfig).where(QuizConfig.token == token, QuizConfig.used_at.is_(None), QuizConfig.expires_at > get_utc_now())
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Token not found or expired")

    return {
        "config_data": config.config_data,
        "tone_summary": config.tone_summary,
        "expires_at": config.expires_at.isoformat(),
        "created_at": config.created_at.isoformat(),
    }


async def quick_start(quick_type: str, user_name: str, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    from constants import QUICK_START_ARCHETYPES

    archetype = QUICK_START_ARCHETYPES.get(quick_type, "golden_retriever")
    quiz_data = QuizData(
        user_name=user_name,
        bot_gender="female",
        archetype=archetype,
        bot_name="Dot",
        attachment_style="secure",
        flirtiness="subtle" if quick_type != "flirty" else "flirty",
        toxicity="healthy",
        spice_consent=False,
    )

    return await complete_quiz(quiz_data, current_user, db)


async def test_config(token: str, db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(QuizConfig).where(QuizConfig.token == token))
    config = result.scalar_one_or_none()

    if not config:
        return {"error": "Token not found"}

    data_type = type(config.config_data).__name__

    try:
        if isinstance(config.config_data, str):
            parsed = json.loads(config.config_data)
            parse_status = "success"
        else:
            parsed = config.config_data
            parse_status = "already dict"
    except Exception as e:
        parsed = str(e)
        parse_status = "error"

    return {
        "token": token,
        "data_type": data_type,
        "parse_status": parse_status,
        "config_data_sample": str(config.config_data)[:100] if config.config_data else None,
        "parsed_sample": str(parsed)[:100] if parsed else None,
        "expires_at": config.expires_at.isoformat() if config.expires_at else None,
        "used_at": config.used_at.isoformat() if config.used_at else None,
    }


async def delete_user_bot(current_user: User, db: AsyncSession) -> Dict[str, Any]:
    try:
        result = await db.execute(select(QuizConfig).where(QuizConfig.user_id == current_user.id))
        quiz_config = result.scalar_one_or_none()

        if not quiz_config:
            raise HTTPException(status_code=404, detail="No bot found for this user")

        settings_result = await db.execute(select(BotSettings).where(BotSettings.user_id == current_user.id))
        bot_settings = settings_result.scalar_one_or_none()
        if bot_settings:
            await db.delete(bot_settings)

        await db.delete(quiz_config)
        await db.commit()

        return {"success": True, "message": "Bot deleted successfully", "bot_id": str(quiz_config.id)}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting bot: {str(e)}")


async def admin_delete_user_bot(user_id: str, current_user: User, db: AsyncSession) -> Dict[str, Any]:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete user bots")

    try:
        user_result = await db.execute(select(User).where(User.id == user_id))
        target_user = user_result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

        result = await db.execute(select(QuizConfig).where(QuizConfig.user_id == target_user.id))
        quiz_config = result.scalar_one_or_none()

        if not quiz_config:
            raise HTTPException(status_code=404, detail=f"No bot found for user {target_user.id}")

        settings_result = await db.execute(select(BotSettings).where(BotSettings.user_id == target_user.id))
        bot_settings = settings_result.scalar_one_or_none()
        if bot_settings:
            await db.delete(bot_settings)

        await db.delete(quiz_config)
        await db.commit()

        return {
            "success": True,
            "message": f"Bot deleted successfully for user {target_user.id}",
            "user_id": str(target_user.id),
            "user_name": target_user.name or "Unknown",
            "bot_id": str(quiz_config.id),
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting bot: {str(e)}")
