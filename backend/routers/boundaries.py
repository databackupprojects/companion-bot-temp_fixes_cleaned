# backend/routers/boundaries.py
"""
Boundary management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from models.sql_models import User
from models.models import BoundaryCreate, BoundaryResponse
from routers.auth import get_current_user
from controllers import boundaries_controller

router = APIRouter()

@router.get("/", response_model=List[BoundaryResponse])
async def get_boundaries(
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[BoundaryResponse]:
    """Get all boundaries for the authenticated user."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await boundaries_controller.list_boundaries(db, user_id)

@router.post("/", response_model=BoundaryResponse)
async def create_boundary(
    boundary: BoundaryCreate,
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BoundaryResponse:
    """Create a new boundary."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await boundaries_controller.create_boundary(db, user_id, boundary)

@router.delete("/{boundary_id}")
async def delete_boundary(
    boundary_id: str,
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete (deactivate) a boundary."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await boundaries_controller.delete_boundary(db, user_id, boundary_id)

@router.put("/{boundary_id}", response_model=BoundaryResponse)
async def update_boundary(
    boundary_id: str,
    boundary: BoundaryCreate,
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BoundaryResponse:
    """Update a boundary (e.g., toggle active status)."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await boundaries_controller.update_boundary(db, user_id, boundary_id, boundary)

@router.post("/space-retract")
async def retract_space_boundary(
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Retract space boundary (user-initiated after 24h hard stop)."""
    if not user_id:
        user_id = str(current_user.id)
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await boundaries_controller.retract_space_boundary(db, user_id)