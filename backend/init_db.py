#!/usr/bin/env python3
"""
Standalone database initialization script
This script can be run independently to initialize the database
without loading all the application modules that might have import issues.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def init_database():
    """Initialize database tables and create default data"""
    try:
        # Import here to avoid early loading of settings
        from app.core.database import init_database as db_init
        
        print("Initializing database...")
        await db_init()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())