# backend/database.py
"""
Database configuration and connection setup for AI Companion Bot v3.1
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/companion_bot"
)

# Convert synchronous URL to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(f"Database URL: {DATABASE_URL.split('@')[0]}@...")

# Create async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    poolclass=NullPool,  # Use NullPool for simpler connection handling
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for better performance
        }
    }
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()

# Dependency to get DB session
# backend/database.py - Update get_db function
async def get_db() -> AsyncSession:
    """Get database session with proper async handling."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database (drop old tables and create new ones with updated schema)."""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        # Drop all existing tables
        logger.info("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables with updated schema
        logger.info("Creating tables with updated schema...")
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully with updated schema")

async def close_db():
    """Close database connections."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")

async def check_db_connection() -> bool:
    """Check database connection."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

# Test connection on import
async def test_connection():
    """Test database connection on startup."""
    try:
        if await check_db_connection():
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection failed")
            return False
    except Exception as e:
        logger.error(f"Database connection test error: {e}")
        return False