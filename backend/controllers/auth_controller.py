import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Token, UserCreate
from models.sql_models import BotSettings, User

SECRET_KEY = os.getenv("SECRET_KEY", "c2fb03d064ff4ed71c8e85905addd4e0")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode JWT and return payload."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def login_for_access_token(db: AsyncSession, email: str, password: str) -> Token:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.is_active:
        raise credentials_exception if not user else HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated by an administrator. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.password_hash or not verify_password(password, user.password_hash):
        raise credentials_exception

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
        username=user.username,
        email=user.email,
        tier=user.tier,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def login_user(db: AsyncSession, email: Optional[str], telegram_id: Optional[str], password: Optional[str]) -> Dict[str, Any]:
    if not email and not telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Telegram ID required")

    if email:
        result = await db.execute(select(User).where(User.email == email))
    else:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated by an administrator. Please contact support.",
        )

    if email and password and (not user.password_hash or not verify_password(password, user.password_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def register_user(db: AsyncSession, user_data: UserCreate) -> Dict[str, Any]:
    existing_user = await db.execute(
        select(User).where(or_(User.email == user_data.email, User.username == user_data.username))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    password_hash = get_password_hash(user_data.password) if user_data.password else None
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        telegram_id=user_data.telegram_id,
        tier=user_data.tier or "free",
        timezone=user_data.timezone or "Asia/Karachi",
        role="user",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    bot_settings = BotSettings(user_id=user.id)
    db.add(bot_settings)
    await db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def register_admin_user(db: AsyncSession, user_data: UserCreate, current_admin: User) -> Dict[str, Any]:
    if current_admin.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can register other admins")

    existing_user = await db.execute(
        select(User).where(or_(User.email == user_data.email, User.username == user_data.username))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    password_hash = get_password_hash(user_data.password) if user_data.password else None
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        telegram_id=user_data.telegram_id,
        tier="premium",
        timezone=user_data.timezone or "Asia/Karachi",
        role="admin",
        is_admin=True,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    bot_settings = BotSettings(user_id=user.id)
    db.add(bot_settings)
    await db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def build_user_info(user: User) -> Dict[str, Any]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tier": user.tier,
        "telegram_id": user.telegram_id,
        "messages_today": user.messages_today,
        "proactive_count_today": user.proactive_count_today,
        "timezone": user.timezone,
        "spice_consent": user.spice_consent,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "created_at": user.created_at.isoformat(),
    }


def refresh_token(current_user: User) -> Dict[str, Any]:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(current_user.id)}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}
