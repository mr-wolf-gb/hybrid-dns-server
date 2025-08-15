"""
Database configuration and management for Hybrid DNS Server API
"""

import asyncio
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, MetaData, String, Text, Table,
    create_engine, func, text
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Database URL setup
if settings.DATABASE_URL.startswith("sqlite"):
    # For SQLite, use aiosqlite for async operations
    database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
elif settings.DATABASE_URL.startswith("postgresql"):
    # For PostgreSQL, use asyncpg for async operations
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    database_url = settings.DATABASE_URL

# SQLAlchemy setup
engine = create_async_engine(
    database_url,
    echo=settings.DATABASE_ECHO,
    future=True
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Metadata for table creation
metadata = MetaData()


# Database tables definitions
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String(50), unique=True, index=True, nullable=False),
    Column("email", String(100), unique=True, index=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
    Column("is_active", Boolean, default=True),
    Column("is_superuser", Boolean, default=False),
    Column("two_factor_secret", String(32), nullable=True),
    Column("two_factor_enabled", Boolean, default=False),
    Column("failed_login_attempts", Integer, default=0),
    Column("locked_until", DateTime, nullable=True),
    Column("last_login", DateTime, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, nullable=False),
    Column("session_token", String(255), unique=True, index=True, nullable=False),
    Column("expires_at", DateTime, nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
    Column("ip_address", String(45), nullable=True),
    Column("user_agent", String(500), nullable=True),
)

zones_table = Table(
    "zones",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String(255), unique=True, index=True, nullable=False),
    Column("zone_type", String(20), nullable=False),  # master, slave, forward
    Column("file_path", String(500), nullable=True),
    Column("master_servers", Text, nullable=True),  # JSON array for slave zones
    Column("forwarders", Text, nullable=True),  # JSON array for forward zones
    Column("is_active", Boolean, default=True),
    Column("serial", Integer, nullable=True),
    Column("refresh", Integer, default=10800),
    Column("retry", Integer, default=3600),
    Column("expire", Integer, default=604800),
    Column("minimum", Integer, default=86400),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

dns_records_table = Table(
    "dns_records",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("zone_id", Integer, nullable=False),
    Column("name", String(255), nullable=False),
    Column("record_type", String(10), nullable=False),  # A, AAAA, CNAME, MX, etc.
    Column("value", String(500), nullable=False),
    Column("ttl", Integer, nullable=True),
    Column("priority", Integer, nullable=True),  # For MX, SRV records
    Column("weight", Integer, nullable=True),  # For SRV records
    Column("port", Integer, nullable=True),  # For SRV records
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

forwarders_table = Table(
    "forwarders",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("domain", String(255), nullable=False),
    Column("forwarder_type", String(20), nullable=False),  # ad, intranet, public
    Column("servers", Text, nullable=False),  # JSON array of IP addresses
    Column("is_active", Boolean, default=True),
    Column("description", String(500), nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

rpz_rules_table = Table(
    "rpz_rules",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("domain", String(255), nullable=False),
    Column("rpz_zone", String(50), nullable=False),  # malware, phishing, etc.
    Column("action", String(20), nullable=False),  # block, redirect, passthru
    Column("redirect_target", String(255), nullable=True),
    Column("is_active", Boolean, default=True),
    Column("source", String(50), nullable=True),  # manual, threat_feed, auto
    Column("description", String(500), nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

dns_logs_table = Table(
    "dns_logs",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("timestamp", DateTime, nullable=False),
    Column("client_ip", String(45), nullable=False),
    Column("query_domain", String(255), nullable=False),
    Column("query_type", String(10), nullable=False),
    Column("response_code", String(20), nullable=False),
    Column("response_time", Integer, nullable=True),  # milliseconds
    Column("blocked", Boolean, default=False),
    Column("rpz_zone", String(50), nullable=True),
    Column("forwarder_used", String(45), nullable=True),
)

system_stats_table = Table(
    "system_stats",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("timestamp", DateTime, nullable=False),
    Column("metric_name", String(100), nullable=False),
    Column("metric_value", String(500), nullable=False),
    Column("metric_type", String(20), nullable=False),  # counter, gauge, histogram
)

audit_logs_table = Table(
    "audit_logs",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("timestamp", DateTime, server_default=func.now()),
    Column("user_id", Integer, nullable=True),
    Column("action", String(100), nullable=False),
    Column("resource_type", String(50), nullable=False),
    Column("resource_id", String(100), nullable=True),
    Column("details", Text, nullable=True),
    Column("ip_address", String(45), nullable=True),
    Column("user_agent", String(500), nullable=True),
)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Initialize database tables and create default data"""
    logger.info("Initializing database...")
    
    try:
        # Create tables using async engine
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        
        # Create default admin user if it doesn't exist
        await create_default_admin()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def create_default_admin():
    """Create default admin user if none exists"""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with async_session() as session:
        # Check if any users exist
        result = await session.execute(text("SELECT COUNT(*) as count FROM users"))
        count = result.scalar()
        
        if count == 0:
            # Create default admin user
            hashed_password = pwd_context.hash("changeme123")
            
            insert_query = text("""
            INSERT INTO users (username, email, hashed_password, is_active, is_superuser)
            VALUES (:username, :email, :hashed_password, :is_active, :is_superuser)
            """)
            
            await session.execute(
                insert_query,
                {
                    "username": "admin",
                    "email": "admin@localhost",
                    "hashed_password": hashed_password,
                    "is_active": True,
                    "is_superuser": True
                }
            )
            await session.commit()
            
            logger.info("Created default admin user (username: admin, password: changeme123)")
            logger.warning("⚠️  Please change the default admin password immediately!")


async def close_database():
    """Close database connection"""
    await engine.dispose()
    logger.info("Database connection closed")