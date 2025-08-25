#!/usr/bin/env python3
"""
Admin user creation script for Hybrid DNS Server
Creates or updates the admin user account
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.database import get_database_session
from app.core.logging_config import setup_logging
from app.core.config import get_settings
from app.models.auth import User
from passlib.context import CryptContext
from sqlalchemy import select

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_or_update_admin(username: str, password: str, email: str, full_name: str):
    """Create or update admin user"""
    try:
        async for session in get_database_session():
            # Check if user already exists
            result = await session.execute(select(User).where(User.username == username))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Update existing user
                existing_user.email = email
                existing_user.hashed_password = pwd_context.hash(password)
                existing_user.is_active = True
                existing_user.is_superuser = True
                
                await session.commit()
                logger.info(f"✅ Updated existing admin user: {username}")
                
            else:
                # Create new user
                admin_user = User(
                    username=username,
                    email=email,
                    hashed_password=pwd_context.hash(password),
                    is_active=True,
                    is_superuser=True
                )
                
                session.add(admin_user)
                await session.commit()
                logger.info(f"✅ Created new admin user: {username}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to create/update admin user: {e}")
        logger.exception("Full error details:")
        return False


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """Basic password validation"""
    if len(password) < 6:
        return False
    return True


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Create or update admin user")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--full-name", required=True, help="Admin full name")
    
    args = parser.parse_args()
    
    # Get credentials from environment variables if not provided via args
    username = args.username or os.getenv("ADMIN_USERNAME", "admin")
    password = args.password or os.getenv("ADMIN_PASSWORD")
    email = args.email or os.getenv("ADMIN_EMAIL", "admin@localhost")
    full_name = args.full_name or os.getenv("ADMIN_FULL_NAME", "System Administrator")
    
    # Validate inputs
    if not username:
        logger.error("❌ Username is required")
        sys.exit(1)
    
    if not password:
        logger.error("❌ Password is required")
        sys.exit(1)
    
    if not validate_password(password):
        logger.error("❌ Password must be at least 6 characters long")
        sys.exit(1)
    
    if not validate_email(email):
        logger.error("❌ Invalid email format")
        sys.exit(1)
    
    logger.info("Creating/updating admin user...")
    logger.info(f"Username: {username}")
    logger.info(f"Email: {email}")
    logger.info(f"Full Name: {full_name}")
    
    # Verify settings
    settings = get_settings()
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Create/update admin user
    success = await create_or_update_admin(username, password, email, full_name)
    
    if success:
        logger.info("✅ Admin user setup completed successfully!")
        logger.info(f"You can now login with username: {username}")
    else:
        logger.error("❌ Admin user setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())