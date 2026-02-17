#!/usr/bin/env python3
"""
Script to create an admin user for the AI Companion Bot
Run this script to initialize the first admin user
"""

import asyncio
import sys
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
import os
from dotenv import load_dotenv

from utils.timezone import get_utc_now

# Load environment variables
load_dotenv()

# Import database and models
from database import AsyncSessionLocal, engine, Base
from models.sql_models import User, BotSettings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


async def create_admin_user(
    username: str,
    email: str,
    password: str,
    db: AsyncSession
) -> User:
    """Create an admin user in the database."""
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f"⚠️  User with username '{username}' or email '{email}' already exists!")
        return None
    
    # Create admin user
    admin_user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        is_admin=True,
        is_active=True,
        tier="premium",
        timezone="UTC",
        created_at=get_utc_now(),
        updated_at=get_utc_now()
    )
    
    db.add(admin_user)
    await db.flush()
    
    # Create default bot settings for admin
    bot_settings = BotSettings(
        user_id=admin_user.id,
        bot_name="AdminBot",
        bot_gender="female",
        archetype="golden_retriever",
        attachment_style="secure",
        flirtiness="subtle",
        toxicity="healthy"
    )
    
    db.add(bot_settings)
    await db.commit()
    await db.refresh(admin_user)
    
    return admin_user


async def main():
    """Main function to create admin user."""
    print("=" * 60)
    print("AI Companion Bot - Admin User Creation")
    print("=" * 60)
    
    # Get user input
    print("\nEnter admin user details:")
    username = input("Username (e.g., admin): ").strip()
    email = input("Email (e.g., admin@example.com): ").strip()
    password = input("Password (minimum 8 characters): ").strip()
    confirm_password = input("Confirm Password: ").strip()
    
    # Validation
    if not username or len(username) < 3:
        print("❌ Username must be at least 3 characters long!")
        return False
    
    if not email or "@" not in email:
        print("❌ Please enter a valid email address!")
        return False
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long!")
        return False
    
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return False
    
    # Create tables if they don't exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created/verified")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False
    
    # Create admin user
    try:
        async with AsyncSessionLocal() as db:
            admin_user = await create_admin_user(username, email, password, db)
            
            if admin_user:
                print("\n" + "=" * 60)
                print("✅ ADMIN USER CREATED SUCCESSFULLY!")
                print("=" * 60)
                print(f"\nAdmin Account Details:")
                print(f"  Username: {admin_user.username}")
                print(f"  Email: {admin_user.email}")
                print(f"  User ID: {admin_user.id}")
                print(f"  Role: {admin_user.role}")
                print(f"  Tier: {admin_user.tier}")
                print(f"\nCredentials:")
                print(f"  Email: {admin_user.email}")
                print(f"  Password: (as entered)")
                print("\n" + "=" * 60)
                print("Login Instructions:")
                print("=" * 60)
                print("\n1. Use /api/auth/login endpoint with:")
                print(f'   {{"email": "{admin_user.email}", "password": "YOUR_PASSWORD"}}')
                print("\n2. Or use /api/auth/token endpoint (OAuth2 compatible)")
                print("\n3. Store the returned access_token for API requests")
                print("\n4. Include token in Authorization header:")
                print('   Authorization: Bearer <access_token>')
                print("\n" + "=" * 60)
                
                return True
            else:
                return False
                
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
