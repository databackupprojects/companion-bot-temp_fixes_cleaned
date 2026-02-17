# backend/routers/auth.py - SWAGGER COMPATIBLE VERSION with Role-Based Access
"""Authentication endpoints for user registration and login with role-based access control."""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from controllers import auth_controller
from database import get_db
from models.models import Token, UserCreate
from models.sql_models import User
from utils.auth import get_current_admin_user, get_current_user

router = APIRouter()

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="JWT"
)

ACCESS_TOKEN_EXPIRE_MINUTES = auth_controller.ACCESS_TOKEN_EXPIRE_MINUTES

async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = auth_controller.decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

# ==========================================
# TOKEN ENDPOINT (For Swagger OAuth2)
# ==========================================

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    """OAuth2 compatible token login for Swagger UI."""
    return await auth_controller.login_for_access_token(db, form_data.username, form_data.password)

# ==========================================
# JSON LOGIN (For API clients)
# ==========================================

@router.post("/login")
async def login_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Login user and get JWT token.

    Accepts JSON ({"email":..., "password":...}) or form-encoded data
    (application/x-www-form-urlencoded), and also supports Telegram ID login.
    """
    # Parse incoming data based on content type
    content_type = request.headers.get('content-type', '')
    email = None
    telegram_id = None
    password = None

    if 'application/json' in content_type:
        body = await request.json()
        email = body.get('email')
        telegram_id = body.get('telegram_id')
        password = body.get('password')
    else:
        form = await request.form()
        email = form.get('email') or request.query_params.get('email')
        telegram_id = form.get('telegram_id') or request.query_params.get('telegram_id')
        password = form.get('password') or request.query_params.get('password')

    return await auth_controller.login_user(db, email, telegram_id, password)

# ==========================================
# REGISTRATION
# ==========================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Register a new user."""
    return await auth_controller.register_user(db, user_data)

# ==========================================
# ADMIN REGISTRATION (Protected)
# ==========================================

@router.post("/admin/register", status_code=status.HTTP_201_CREATED)
async def register_admin_user(
    user_data: UserCreate,
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Register a new admin user (admin only)."""
    return await auth_controller.register_admin_user(db, user_data, current_admin)

# ==========================================
# USER INFO
# ==========================================

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current authenticated user info."""
    return auth_controller.build_user_info(current_user)

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Refresh JWT token."""
    return auth_controller.refresh_token(current_user)

@router.post("/logout")
async def logout_user() -> Dict[str, str]:
    """Logout user (client-side token invalidation)."""
    return {"message": "Successfully logged out"}