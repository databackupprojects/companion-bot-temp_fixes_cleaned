#!/usr/bin/env python3
"""
Database migration runner script
Executes SQL migrations from the database/migrations directory
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

async def run_migrations():
    """Run all pending migrations from the migrations directory."""
    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return False
    
    # Get all migration files, sorted by name
    migration_files = sorted(migrations_dir.glob("v*.sql"))
    
    if not migration_files:
        logger.warning("No migration files found")
        return True
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    try:
        async with engine.begin() as conn:
            for migration_file in migration_files:
                try:
                    logger.info(f"Running migration: {migration_file.name}")
                    
                    # Read SQL file
                    with open(migration_file, 'r') as f:
                        sql = f.read()
                    
                    # Skip empty files
                    if not sql.strip():
                        logger.warning(f"Skipping empty migration file: {migration_file.name}")
                        continue
                    
                    # Execute SQL
                    # Split by semicolon to handle multiple statements
                    statements = [s.strip() for s in sql.split(';') if s.strip()]
                    for statement in statements:
                        # Skip comments
                        if statement.startswith('--'):
                            continue
                        await conn.execute(text(statement))
                    
                    logger.info(f"✅ Completed: {migration_file.name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error running migration {migration_file.name}: {e}")
                    return False
        
        logger.info("✅ All migrations completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False

async def main():
    """Main entry point."""
    success = await run_migrations()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
