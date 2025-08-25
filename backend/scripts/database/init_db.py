#!/usr/bin/env python3
"""
Database initialization script for Hybrid DNS Server
Creates all database tables and sets up initial configuration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.database import init_database, check_database_health
from app.core.logging_config import setup_logging
from app.core.config import get_settings

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def main():
    """Initialize the database"""
    try:
        logger.info("Starting database initialization...")
        
        # Verify settings
        settings = get_settings()
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        # Initialize database
        await init_database()
        
        # Verify database health
        if await check_database_health():
            logger.info("✅ Database initialization completed successfully!")
            logger.info("Database is healthy and all tables are accessible")
        else:
            logger.error("❌ Database initialization completed but health check failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.exception("Full error details:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())