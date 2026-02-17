"""
Database Reset Script
Use this to completely reset the database and recreate the schema.
WARNING: This will DELETE ALL DATA from the database!
"""

import asyncio
import logging
from dotenv import load_dotenv
from database import engine, Base
from models.sql_models import User, Message, UserSettings, Boundary, Analytics, BotPersona
from create_admin import create_admin_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def reset_database():
    """
    Reset the entire database:
    1. Drop all existing tables
    2. Create fresh tables
    3. Optionally create admin user
    """
    try:
        logger.warning("⚠️  STARTING DATABASE RESET")
        logger.warning("This will DELETE ALL DATA from the database!")
        
        # Confirm action
        confirm = input("\nAre you sure you want to delete all data? Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            logger.info("Database reset cancelled")
            return
        
        # Drop all tables
        logger.info("Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ All tables dropped")
        
        # Create fresh tables
        logger.info("Creating fresh database schema...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema created")
        
        # Ask if user wants to create admin account
        create_admin = input("\nCreate admin user account? (yes/no): ")
        if create_admin.lower() == 'yes':
            await create_admin_user()
            logger.info("✅ Admin user created")
        
        logger.info("\n✅ DATABASE RESET COMPLETED SUCCESSFULLY")
        logger.info("All data has been cleared and schema recreated")
        
    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")
        raise


async def clear_data_only():
    """
    Clear all data but keep the schema.
    Use this if you want to preserve table structure but delete all records.
    """
    try:
        logger.warning("⚠️  CLEARING ALL DATA (keeping schema)")
        
        # Confirm action
        confirm = input("Are you sure you want to delete all data? Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            logger.info("Data clear cancelled")
            return
        
        # Delete all records
        logger.info("Clearing all data...")
        async with engine.begin() as conn:
            # Delete in order to respect foreign keys
            await conn.run_sync(lambda session: session.query(Message).delete())
            await conn.run_sync(lambda session: session.query(Boundary).delete())
            await conn.run_sync(lambda session: session.query(UserSettings).delete())
            await conn.run_sync(lambda session: session.query(BotPersona).delete())
            await conn.run_sync(lambda session: session.query(Analytics).delete())
            await conn.run_sync(lambda session: session.query(User).delete())
        
        logger.info("✅ All data cleared successfully")
        
    except Exception as e:
        logger.error(f"❌ Error clearing data: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "="*60)
    print("AI Companion Bot - Database Reset Tool")
    print("="*60)
    print("\nChoose an option:")
    print("1. Full reset (drop tables + recreate)")
    print("2. Clear data only (keep schema)")
    print("3. Exit")
    print("-"*60)
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(reset_database())
    elif choice == "2":
        asyncio.run(clear_data_only())
    elif choice == "3":
        print("Cancelled")
    else:
        print("Invalid choice")
