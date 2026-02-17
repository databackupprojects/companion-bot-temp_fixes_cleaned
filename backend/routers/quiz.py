from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers import quiz_controller
from database import get_db
from models import QuizData
from models.sql_models import User
from utils.auth import get_current_user

from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

@router.get("/my-bots")
async def get_user_bots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get all bots created by the current user - from both BotSettings and QuizConfig."""
    return await quiz_controller.list_user_bots(current_user, db)

@router.post("/start")
async def start_quiz(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Start a new quiz session."""
    return quiz_controller.start_quiz_session()

@router.post("/step/{step_number}")
async def submit_quiz_step(
    step_number: int,
    data: Dict[str, Any],
    session_token: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Submit a quiz step."""
    return quiz_controller.submit_step(step_number, data, session_token)

# backend/routers/quiz.py - Check if user can create a bot
@router.get("/can-create")
async def can_create_bot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Check if user can create another bot and return used archetypes (requires auth)."""
    return await quiz_controller.can_create_bot(current_user, db)

@router.post("/complete")
async def complete_quiz(
    quiz_data: QuizData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Complete quiz and generate configuration token. Requires authentication."""
    return await quiz_controller.complete_quiz(quiz_data, current_user, db)

@router.get("/config/{token}")
async def get_quiz_config(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get quiz configuration by token."""
    return await quiz_controller.get_config(token, db)

@router.post("/quick-start")
async def quick_start(
    quick_type: str,
    user_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Quick start with predefined archetypes."""
    return await quiz_controller.quick_start(quick_type, user_name, current_user, db)

# Add to backend/routers/quiz.py
@router.get("/test-config/{token}")
async def test_config(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Test endpoint to verify quiz configuration."""
    return await quiz_controller.test_config(token, db)


# ==========================================
# DELETE BOT ENDPOINTS
# ==========================================

@router.post("/delete")
async def delete_user_bot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Delete current user's bot (only 1 per user for free tier)."""
    return await quiz_controller.delete_user_bot(current_user, db)


@router.post("/admin/delete-bot/{user_id}")
async def admin_delete_user_bot(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint: Delete a specific user's bot.
    Only admins can use this endpoint.
    """
    return await quiz_controller.admin_delete_user_bot(user_id, current_user, db)