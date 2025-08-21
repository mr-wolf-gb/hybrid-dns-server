"""
Database configuration and management for Hybrid DNS Server API
"""

import asyncio
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, MetaData, String, Text, Table,
    create_engine, func, text, select
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .logging_config import get_logger

# Create base class for models
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# Database setup will be initialized when needed
engine = None
async_session = None

# Metadata for table creation
metadata = Base.metadata


# All database tables are now defined as SQLAlchemy models
# The metadata is automatically populated from the model definitions


class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self._initialized = False
    
    def _initialize_engine(self):
        """Initialize database engine and session maker"""
        if not self._initialized:
            settings = get_settings()
            
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
            self.engine = create_async_engine(
                database_url,
                echo=settings.DATABASE_ECHO,
                future=True
            )

            self.async_session = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self._initialized = True
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        self._initialize_engine()
        
        async with self.async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def fetch_one(self, query: str, values: dict = None):
        """Execute a query and fetch one result"""
        async with self.async_session() as session:
            try:
                result = await session.execute(text(query), values or {})
                row = result.fetchone()
                if row:
                    # Convert Row to dict
                    return dict(row._mapping)
                return None
            except Exception as e:
                await session.rollback()
                raise e

    async def fetch_all(self, query: str, values: dict = None):
        """Execute a query and fetch all results"""
        async with self.async_session() as session:
            try:
                result = await session.execute(text(query), values or {})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                await session.rollback()
                raise e

    async def execute(self, query: str, values: dict = None):
        """Execute a query without returning results"""
        async with self.async_session() as session:
            try:
                await session.execute(text(query), values or {})
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

    async def close(self):
        """Close database connection"""
        if self.engine is not None:
            await self.engine.dispose()
            logger = get_logger(__name__)
            logger.info("Database connection closed")


# Global database instance
database = Database()


def _initialize_database_engine():
    """Initialize database engine and session maker (legacy function)"""
    global engine, async_session
    
    if engine is None:
        database._initialize_engine()
        engine = database.engine
        async_session = database.async_session


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection"""
    async for session in database.get_session():
        yield session


async def init_database():
    """Initialize database tables and create default data"""
    # Import models here to avoid circular imports
    from ..models import dns, auth, monitoring, system, security, events
    
    _initialize_database_engine()
    logger = get_logger(__name__)
    logger.info("Initializing database...")
    
    try:
        # Create tables using async engine
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        
        logger.info("Database tables created successfully")
        
        # Apply application-managed migrations (idempotent)
        await apply_app_migrations()

        # Log the tables that were created
        table_names = [table.name for table in metadata.tables.values()]
        logger.info(f"Created tables: {', '.join(sorted(table_names))}")
        
        # Verify indexes were created
        await verify_indexes()
        
        # Create default admin user if it doesn't exist
        await create_default_admin()
        
        # Create default system configuration if it doesn't exist
        await create_default_system_config()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def verify_indexes():
    """Verify that all performance indexes were created"""
    _initialize_database_engine()
    logger = get_logger(__name__)
    
    try:
        async with engine.begin() as conn:
            # Count indexes that were created
            if 'postgresql' in str(engine.url):
                # PostgreSQL query to count our performance indexes
                result = await conn.execute(text("""
                    SELECT COUNT(*) as index_count
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND indexname LIKE 'idx_%'
                """))
            else:
                # SQLite query to count our performance indexes
                result = await conn.execute(text("""
                    SELECT COUNT(*) as index_count
                    FROM sqlite_master 
                    WHERE type = 'index' 
                    AND name LIKE 'idx_%'
                """))
            
            index_count = result.scalar()
            logger.info(f"Created {index_count} performance indexes")
            
            # Log a warning if we have fewer indexes than expected
            # Count based on the indexes defined in our models:
            # DNS models: ~15 indexes, Auth models: ~8 indexes, Monitoring models: ~12 indexes, System models: ~2 indexes
            expected_indexes = 37  # Total number of custom indexes we defined
            if index_count < expected_indexes * 0.8:  # Allow some variance
                logger.warning(f"Expected around {expected_indexes} indexes, but only found {index_count}")
                logger.warning("Some indexes may not have been created properly")
            else:
                logger.info(f"Database indexes verified successfully ({index_count} indexes found)")
            
    except Exception as e:
        logger.warning(f"Could not verify indexes: {e}")
        # Don't fail initialization if index verification fails


async def apply_app_migrations():
    """Apply idempotent, application-level migrations to align DB with current models.
    This replaces Alembic for environments where migrations aren't used.
    """
    _initialize_database_engine()
    logger = get_logger(__name__)

    async with engine.begin() as conn:
        # Determine dialect
        is_postgres = 'postgresql' in str(engine.url)

        # Helper to check column existence
        async def column_exists(table: str, column: str) -> bool:
            if is_postgres:
                res = await conn.execute(text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table
                      AND column_name = :column
                    """
                ), {"table": table, "column": column})
                return res.scalar() is not None
            else:
                res = await conn.execute(text(
                    """
                    PRAGMA table_info(:table)
                    """
                ), {"table": table})
                return any(row[1] == column for row in res.fetchall())

        # Helper to check index existence (best-effort)
        async def index_exists(table: str, index_name: str) -> bool:
            if is_postgres:
                res = await conn.execute(text(
                    """
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = :table
                      AND indexname = :index
                    """
                ), {"table": table, "index": index_name})
                return res.scalar() is not None
            else:
                res = await conn.execute(text(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND tbl_name = :table AND name = :index
                    """
                ), {"table": table, "index": index_name})
                return res.scalar() is not None

        # 1) forwarders: ensure priority/grouping/template columns exist
        forwarders_adds = [
            ("priority", "INTEGER NOT NULL DEFAULT 5"),
            ("group_name", "VARCHAR(100)"),
            ("group_priority", "INTEGER NOT NULL DEFAULT 5"),
            ("is_template", "BOOLEAN NOT NULL DEFAULT FALSE" if is_postgres else "BOOLEAN NOT NULL DEFAULT 0"),
            ("template_name", "VARCHAR(255)"),
            ("created_from_template", "VARCHAR(255)"),
        ]

        for col, ddl in forwarders_adds:
            try:
                if not await column_exists('forwarders', col):
                    await conn.execute(text(f"ALTER TABLE forwarders ADD COLUMN {col} {ddl}"))
                    logger.info(f"Added column forwarders.{col}")
            except Exception as e:
                logger.warning(f"Skipping add column forwarders.{col}: {e}")

        # 2) Create forwarder_templates table if missing
        try:
            if is_postgres:
                res = await conn.execute(text(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'forwarder_templates'
                    """
                ))
                has_templates = res.scalar() is not None
            else:
                res = await conn.execute(text(
                    """
                    SELECT name FROM sqlite_master WHERE type='table' AND name='forwarder_templates'
                    """
                ))
                has_templates = res.scalar() is not None

            if not has_templates:
                # Use a portable subset of types for compatibility
                await conn.execute(text(
                    """
                    CREATE TABLE forwarder_templates (
                        id INTEGER PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description VARCHAR(500),
                        forwarder_type VARCHAR(20) NOT NULL,
                        default_domains TEXT,
                        default_servers TEXT,
                        default_priority INTEGER NOT NULL DEFAULT 5,
                        default_group_name VARCHAR(100),
                        default_health_check_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        is_system_template BOOLEAN NOT NULL DEFAULT FALSE,
                        usage_count INTEGER NOT NULL DEFAULT 0,
                        created_by INTEGER,
                        updated_by INTEGER,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                ))
                logger.info("Created table forwarder_templates")
        except Exception as e:
            logger.warning(f"Skipping create table forwarder_templates: {e}")

        # 3) Ensure expected indexes on forwarders
        forwarder_indexes = {
            'idx_forwarders_priority': ('forwarders', 'priority'),
            'idx_forwarders_group_name': ('forwarders', 'group_name'),
            'idx_forwarders_group_priority': ('forwarders', 'group_name, group_priority'),
            'idx_forwarders_is_template': ('forwarders', 'is_template'),
            'idx_forwarders_template_name': ('forwarders', 'template_name'),
            'idx_forwarders_created_from_template': ('forwarders', 'created_from_template'),
        }
        for idx_name, (tbl, cols) in forwarder_indexes.items():
            try:
                if not await index_exists(tbl, idx_name):
                    await conn.execute(text(f"CREATE INDEX {idx_name} ON {tbl} ({cols})"))
                    logger.info(f"Created index {idx_name}")
            except Exception as e:
                logger.warning(f"Skipping create index {idx_name}: {e}")

        # 4) Ensure expected indexes on forwarder_templates
        template_indexes = {
            'idx_forwarder_templates_name': ('forwarder_templates', 'name'),
            'idx_forwarder_templates_type': ('forwarder_templates', 'forwarder_type'),
            'idx_forwarder_templates_system': ('forwarder_templates', 'is_system_template'),
            'idx_forwarder_templates_usage': ('forwarder_templates', 'usage_count'),
            'idx_forwarder_templates_created_by': ('forwarder_templates', 'created_by'),
        }
        for idx_name, (tbl, cols) in template_indexes.items():
            try:
                if not await index_exists(tbl, idx_name):
                    await conn.execute(text(f"CREATE INDEX {idx_name} ON {tbl} ({cols})"))
                    logger.info(f"Created index {idx_name}")
            except Exception as e:
                logger.warning(f"Skipping create index {idx_name}: {e}")

    # No exception bubbling; we want init to continue even if best-effort fixes fail
    logger.info("Application-level migrations applied (best-effort)")


async def create_default_admin():
    """Create default admin user if none exists"""
    from passlib.context import CryptContext
    from sqlalchemy import select
    from ..models.auth import User
    
    _initialize_database_engine()
    logger = get_logger(__name__)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with async_session() as session:
        # Check if any users exist
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar()
        
        if count == 0:
            # Create default admin user
            hashed_password = pwd_context.hash("changeme123")
            
            admin_user = User(
                username="admin",
                email="admin@localhost",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True
            )
            
            session.add(admin_user)
            await session.commit()
            
            logger.info("Created default admin user (username: admin, password: changeme123)")
            logger.warning("⚠️  Please change the default admin password immediately!")


async def create_default_system_config():
    """Create default system configuration if none exists"""
    from sqlalchemy import select
    from ..models.system import SystemConfig
    
    _initialize_database_engine()
    logger = get_logger(__name__)
    
    async with async_session() as session:
        # Check if any system config exists
        result = await session.execute(select(func.count(SystemConfig.id)))
        count = result.scalar()
        
        if count == 0:
            # Create default system configuration
            default_configs = [
                SystemConfig(
                    key="bind9_config_path",
                    value="/etc/bind",
                    value_type="string",
                    category="dns",
                    description="Path to BIND9 configuration directory"
                ),
                SystemConfig(
                    key="bind9_zones_path",
                    value="/etc/bind/zones",
                    value_type="string",
                    category="dns",
                    description="Path to BIND9 zone files directory"
                ),
                SystemConfig(
                    key="bind9_rpz_path",
                    value="/etc/bind/rpz",
                    value_type="string",
                    category="dns",
                    description="Path to BIND9 RPZ files directory"
                ),
                SystemConfig(
                    key="default_ttl",
                    value="3600",
                    value_type="integer",
                    category="dns",
                    description="Default TTL for DNS records"
                ),
                SystemConfig(
                    key="health_check_interval",
                    value="300",
                    value_type="integer",
                    category="monitoring",
                    description="Forwarder health check interval in seconds"
                ),
                SystemConfig(
                    key="threat_feed_update_interval",
                    value="3600",
                    value_type="integer",
                    category="security",
                    description="Threat feed update interval in seconds"
                ),
                SystemConfig(
                    key="log_retention_days",
                    value="30",
                    value_type="integer",
                    category="monitoring",
                    description="Number of days to retain DNS logs"
                ),
                SystemConfig(
                    key="enable_query_logging",
                    value="true",
                    value_type="boolean",
                    category="monitoring",
                    description="Enable DNS query logging"
                ),
                SystemConfig(
                    key="enable_rpz",
                    value="true",
                    value_type="boolean",
                    category="security",
                    description="Enable Response Policy Zones"
                ),
                SystemConfig(
                    key="max_failed_login_attempts",
                    value="5",
                    value_type="integer",
                    category="security",
                    description="Maximum failed login attempts before account lockout"
                )
            ]
            
            for config in default_configs:
                session.add(config)
            
            await session.commit()
            logger.info(f"Created {len(default_configs)} default system configuration entries")


async def check_database_health():
    """Check database health and model integrity"""
    _initialize_database_engine()
    logger = get_logger(__name__)
    
    try:
        async with async_session() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Check if all expected tables exist
            expected_tables = {
                'zones', 'dns_records', 'forwarders', 'forwarder_health', 
                'rpz_rules', 'threat_feeds', 'system_config', 'users', 
                'sessions', 'dns_logs', 'system_stats', 'audit_logs'
            }
            
            if 'postgresql' in str(engine.url):
                result = await session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
            else:
                result = await session.execute(text("""
                    SELECT name as table_name 
                    FROM sqlite_master 
                    WHERE type = 'table'
                """))
            
            existing_tables = {row[0] for row in result.fetchall()}
            missing_tables = expected_tables - existing_tables
            
            if missing_tables:
                logger.error(f"Missing database tables: {missing_tables}")
                return False
            
            # Test model relationships by counting records
            table_counts = {}
            for table_name in expected_tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    table_counts[table_name] = count
                except Exception as e:
                    logger.error(f"Error querying table {table_name}: {e}")
                    return False
            
            logger.info("Database health check passed")
            logger.info(f"Table record counts: {table_counts}")
            return True
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_database():
    """Close database connection"""
    await database.close()