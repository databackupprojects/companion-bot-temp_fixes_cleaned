import uuid
from typing import List, Dict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sql_models import UserBoundary
from models.models import BoundaryCreate, BoundaryResponse
from services.boundary_manager import BoundaryManager


async def list_boundaries(db: AsyncSession, user_id: str) -> List[BoundaryResponse]:
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    boundaries_result = await db.execute(select(UserBoundary).where(UserBoundary.user_id == target_user_id))
    boundaries = boundaries_result.scalars().all()

    return [
        BoundaryResponse(
            id=boundary.id,
            boundary_type=boundary.boundary_type,
            boundary_value=boundary.boundary_value,
            active=boundary.active,
            created_at=boundary.created_at,
        )
        for boundary in boundaries
    ]


async def create_boundary(db: AsyncSession, user_id: str, payload: BoundaryCreate) -> BoundaryResponse:
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    existing_result = await db.execute(
        select(UserBoundary).where(
            UserBoundary.user_id == target_user_id,
            UserBoundary.boundary_type == payload.boundary_type.value,
            UserBoundary.boundary_value == payload.boundary_value,
            UserBoundary.active == True,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Boundary already exists")

    new_boundary = UserBoundary(
        user_id=target_user_id,
        boundary_type=payload.boundary_type.value,
        boundary_value=payload.boundary_value,
        active=payload.active,
    )
    db.add(new_boundary)
    await db.commit()
    await db.refresh(new_boundary)

    return BoundaryResponse(
        id=new_boundary.id,
        boundary_type=new_boundary.boundary_type,
        boundary_value=new_boundary.boundary_value,
        active=new_boundary.active,
        created_at=new_boundary.created_at,
    )


async def delete_boundary(db: AsyncSession, user_id: str, boundary_id: str) -> Dict[str, str]:
    try:
        target_user_id = uuid.UUID(user_id)
        boundary_uuid = uuid.UUID(boundary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await db.execute(
        select(UserBoundary).where(
            UserBoundary.id == boundary_uuid,
            UserBoundary.user_id == target_user_id,
        )
    )
    boundary = result.scalar_one_or_none()
    if not boundary:
        raise HTTPException(status_code=404, detail="Boundary not found")

    await db.delete(boundary)
    await db.commit()
    return {"message": "Boundary deleted successfully"}


async def update_boundary(db: AsyncSession, user_id: str, boundary_id: str, payload: BoundaryCreate) -> BoundaryResponse:
    try:
        target_user_id = uuid.UUID(user_id)
        boundary_uuid = uuid.UUID(boundary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await db.execute(
        select(UserBoundary).where(
            UserBoundary.id == boundary_uuid,
            UserBoundary.user_id == target_user_id,
        )
    )
    existing_boundary = result.scalar_one_or_none()
    if not existing_boundary:
        raise HTTPException(status_code=404, detail="Boundary not found")

    existing_boundary.boundary_type = payload.boundary_type.value if hasattr(payload.boundary_type, "value") else payload.boundary_type
    existing_boundary.boundary_value = payload.boundary_value
    existing_boundary.active = payload.active

    await db.commit()
    await db.refresh(existing_boundary)

    return BoundaryResponse(
        id=existing_boundary.id,
        boundary_type=existing_boundary.boundary_type,
        boundary_value=existing_boundary.boundary_value,
        active=existing_boundary.active,
        created_at=existing_boundary.created_at,
    )


async def retract_space_boundary(db: AsyncSession, user_id: str) -> Dict[str, str]:
    boundary_manager = BoundaryManager(db)
    success = await boundary_manager._deactivate_space_boundary(user_id)
    if success:
        return {"message": "Space boundary retracted successfully"}
    return {"message": "No active space boundary found"}
