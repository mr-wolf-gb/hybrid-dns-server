"""Alembic environment configuration for Hybrid DNS Server"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Import all models to ensure they are registered with Base
from app.models.dns import Base
from app.models import (
    Zone, DNSRecord, Forwarder, ForwarderHealth, RPZRule, ThreatFeed, SystemConfig,
    User, Session, DNSLog, SystemStats, AuditLog
)

# Import all model modules to ensure all models are registered
from app.models import dns, auth, monitoring, system, security, events
from app.core.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from settings"""
    settings = get_settings()
    database_url = settings.DATABASE_URL
    
    # For Alembic, we need to use the sync version of the database URL
    if database_url.startswith("sqlite+aiosqlite://"):
        database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return database_url


def is_async_database():
    """Check if we're using an async database that requires async migrations"""
    database_url = get_database_url()
    return database_url.startswith("postgresql://")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online_sync() -> None:
    """Run migrations in 'online' mode with synchronous engine (for SQLite)."""
    from sqlalchemy import engine_from_config
    
    # Get database URL
    database_url = get_database_url()
    
    # Create sync engine configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


async def run_async_migrations() -> None:
    """Run migrations with async engine (for PostgreSQL)."""
    # Get database URL but convert to async version for PostgreSQL
    settings = get_settings()
    database_url = settings.DATABASE_URL
    
    # Convert to async URL for PostgreSQL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Create async engine configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    if is_async_database():
        # Use async migrations for PostgreSQL
        asyncio.run(run_async_migrations())
    else:
        # Use sync migrations for SQLite
        run_migrations_online_sync()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()