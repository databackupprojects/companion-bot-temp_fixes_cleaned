from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from controllers import messages_controller
from database import get_db
from models import MessageSend
from models.sql_models import User
from utils.auth import get_current_user

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await messages_controller.websocket_handler(websocket, user_id, db)


@router.post("/", include_in_schema=True)
@router.post("", include_in_schema=False)
async def send_message(
    request: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.send_message(request, current_user, db)


@router.get("/history")
async def get_message_history(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    bot_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.get_message_history(limit, offset, user_id, bot_id, current_user, db)


@router.delete("/clear")
async def clear_message_history(
    user_id: Optional[str] = None,
    bot_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.clear_message_history(user_id, bot_id, current_user, db)


@router.get("/analytics")
async def get_message_analytics(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.get_message_analytics(user_id, current_user, db)


@router.get("/memory")
async def get_memory_summary(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.get_memory_summary(user_id, current_user, db)


@router.delete("/memory")
async def clear_memory(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return await messages_controller.clear_memory(user_id, current_user)


@router.post("/support")
async def trigger_support(
    context: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.trigger_support(context, current_user, db)


@router.post("/proactive")
async def send_proactive_message(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await messages_controller.send_proactive_message(current_user, db)
