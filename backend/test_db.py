#!/usr/bin/env python3
"""
Test database connection and basic functionality
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

async def test_database():
    """Test database connection and functionality"""
    try:
        # Import here to avoid early loading of settings
        from app.core.database import get_database_session
        from sqlalchemy import text
        
        print("Testing database connection...")
        
        async for session in get_database_session():
            try:
                # Test basic connection
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                print(f"Database connection test: {test_value}")
                
                # Test if users table exists
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"Users table exists with {user_count} users")
                
                break
            except Exception as e:
                print(f"Database test error: {e}")
                raise
        
        print("Database test completed successfully!")
        
    except Exception as e:
        print(f"Failed to test database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_database())