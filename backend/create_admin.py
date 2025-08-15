#!/usr/bin/env python3
"""
Standalone admin user creation script
"""

import asyncio
import getpass
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

async def create_admin_user():
    """Create admin user"""
    try:
        # Import here to avoid early loading of settings
        from app.core.database import get_database_session
        from passlib.context import CryptContext
        from sqlalchemy import text
        
        # Get user input
        print("\nPlease create an admin user for the DNS server:")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        full_name = input("Full Name: ")
        email = input("Email: ")
        
        if not username or not password or not email:
            print("Error: Username, password, and email are required")
            sys.exit(1)
        
        pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
        hashed_password = pwd_context.hash(password)
        
        async for session in get_database_session():
            try:
                # Check if user already exists
                result = await session.execute(
                    text('SELECT id FROM users WHERE username = :username'),
                    {'username': username}
                )
                existing_user = result.fetchone()
                
                if existing_user:
                    # Update existing user
                    await session.execute(
                        text('''
                        UPDATE users SET 
                            email = :email,
                            hashed_password = :hashed_password,
                            is_active = true,
                            is_superuser = true
                        WHERE username = :username
                        '''),
                        {
                            'username': username,
                            'email': email,
                            'hashed_password': hashed_password
                        }
                    )
                    print(f'Admin user "{username}" updated successfully')
                else:
                    # Create new user
                    await session.execute(
                        text('''
                        INSERT INTO users (username, email, hashed_password, is_active, is_superuser)
                        VALUES (:username, :email, :hashed_password, true, true)
                        '''),
                        {
                            'username': username,
                            'email': email,
                            'hashed_password': hashed_password
                        }
                    )
                    print(f'Admin user "{username}" created successfully')
                
                await session.commit()
                break
            except Exception as e:
                await session.rollback()
                print(f'Error creating admin user: {e}')
                raise
        
    except Exception as e:
        print(f"Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_admin_user())