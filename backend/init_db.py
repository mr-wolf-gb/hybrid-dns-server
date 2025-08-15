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

# Set up environment file path - look for .env in parent directory first
env_file_parent = backend_dir.parent / ".env"
env_file_current = backend_dir / ".env"

if env_file_parent.exists():
    # Load environment variables from parent directory .env file
    print(f"Loading environment from: {env_file_parent}")
    with open(env_file_parent, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
elif env_file_current.exists():
    # Load environment variables from current directory .env file
    print(f"Loading environment from: {env_file_current}")
    with open(env_file_current, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
else:
    print("Warning: No .env file found in current or parent directory")

async def init_database():
    """Initialize database tables and create default data"""
    try:
        # Verify that required environment variables are set
        required_vars = ['SECRET_KEY', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            print("Make sure the .env file exists and contains all required variables.")
            sys.exit(1)
        
        print(f"Environment variables loaded:")
        print(f"  SECRET_KEY: {'*' * 20}")
        print(f"  DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")
        
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