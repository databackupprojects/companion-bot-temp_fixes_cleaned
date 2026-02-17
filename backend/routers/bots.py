# backend/routers/bots.py
"""Bots management endpoints - delegates core logic to controller."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from controllers import bots_controller
from database import get_db
from models import BotListResponse, BotSettingsCreate, BotSettingsResponse, BotSettingsUpdate
from models.sql_models import BotSettings, QuizConfig, User
from routers.auth import get_current_user
from sqlalchemy import select
router = APIRouter()

@router.get("/", response_model=BotListResponse)
async def get_all_bots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotListResponse:
    return await bots_controller.list_bots(db, current_user.id)

@router.get("/{bot_id}", response_model=BotSettingsResponse)
async def get_bot(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotSettingsResponse:
    return await bots_controller.get_bot(db, current_user.id, bot_id)

@router.post("/", response_model=BotSettingsResponse)
async def create_bot(
    bot_data: BotSettingsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotSettingsResponse:
    return await bots_controller.create_bot(db, current_user, bot_data)

@router.put("/{bot_id}", response_model=BotSettingsResponse)
async def update_bot(
    bot_id: uuid.UUID,
    bot_update: BotSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BotSettingsResponse:
    return await bots_controller.update_bot(db, current_user.id, bot_id, bot_update)

@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await bots_controller.delete_bot(db, current_user.id, bot_id)

@router.get("/{bot_id}/telegram-link")
async def get_telegram_link(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Telegram deep link and QR code for a bot."""
    
    # First try to find in BotSettings
    result = await db.execute(
        select(BotSettings).where(
            BotSettings.id == bot_id,
            BotSettings.user_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    # If not found in BotSettings, try QuizConfig
    if not bot:
        from models.sql_models import QuizConfig
        quiz_result = await db.execute(
            select(QuizConfig).where(
                QuizConfig.id == bot_id,
                QuizConfig.user_id == current_user.id
            )
        )
        quiz_config = quiz_result.scalar_one_or_none()
        
        if quiz_config:
            # Create a temporary BotSettings-like object from quiz_config
            config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
            bot_archetype = config_data.get('archetype', 'golden_retriever')
            start_param = quiz_config.token  # Use the quiz token directly
        else:
            raise HTTPException(status_code=404, detail="Bot not found")
    else:
        # Use stored token if available, otherwise fallback to user_id
        start_param = bot.quiz_token if bot.quiz_token else str(current_user.id)
        bot_archetype = bot.archetype
    
    # Import constants to get Telegram bot usernames
    from constants import get_telegram_deep_link
    
    # Create deep link using the start parameter
    deep_link = get_telegram_deep_link(bot_archetype, start_param)
    
    # Generate QR code data URL
    import qrcode
    from io import BytesIO
    import base64
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(deep_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{img_str}"
    
    # Extract telegram username from deep link
    import re
    telegram_username_match = re.search(r't\.me/([^?]+)', deep_link)
    telegram_username = telegram_username_match.group(1) if telegram_username_match else 'bot'
    
    # Get bot info
    if bot:
        bot_name = bot.bot_name
        archetype = bot.archetype
    else:
        config_data = quiz_config.config_data if isinstance(quiz_config.config_data, dict) else {}
        bot_name = config_data.get('bot_name', 'Unnamed Bot')
        archetype = config_data.get('archetype', 'golden_retriever')
    
    return {
        "bot_id": str(bot_id),
        "bot_name": bot_name,
        "archetype": archetype,
        "telegram_username": telegram_username,
        "deep_link": deep_link,
        "qr_code": qr_code_url
    }


