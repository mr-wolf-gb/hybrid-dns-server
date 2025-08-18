"""
Configuration management for Hybrid DNS Server API
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_NAME: str = "Hybrid DNS Server API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS and hosts
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1", "10.10.20.13", "*"])
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    # Database
    DATABASE_URL: str = "sqlite:///./dns_server.db"
    DATABASE_ECHO: bool = False
    
    # Server Configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    
    # BIND9 Configuration
    BIND_CONFIG_DIR: str = "/etc/bind"
    BIND_ZONES_DIR: str = "/etc/bind/zones"
    BIND_RPZ_DIR: str = "/etc/bind/rpz"
    BIND_SERVICE_NAME: str = "bind9"
    BIND9_CONFIG_DIR: str = "/etc/bind"
    BIND9_ZONES_DIR: str = "/etc/bind/zones"
    BIND9_RPZ_DIR: str = "/etc/bind/rpz" 
    BIND9_LOG_DIR: str = "/var/log/named"
    BIND9_SERVICE_NAME: str = "named"
    BIND9_RNDC_KEY: str = "/etc/bind/rndc.key"
    
    # Custom configuration paths (for development/testing)
    CUSTOM_CONFIG_DIR: Optional[str] = None
    CUSTOM_ZONES_DIR: Optional[str] = None
    CUSTOM_RPZ_DIR: Optional[str] = None
    
    # DNS Settings
    DEFAULT_TTL: int = 86400
    DEFAULT_REFRESH: int = 10800
    DEFAULT_RETRY: int = 3600
    DEFAULT_EXPIRE: int = 604800
    DEFAULT_MINIMUM: int = 86400
    
    # Monitoring and Health Checks
    MONITORING_ENABLED: bool = True
    MONITORING_INTERVAL: int = 60
    HEALTH_CHECK_INTERVAL: int = 60  # seconds
    DNS_QUERY_TIMEOUT: int = 5  # seconds
    BIND_STATS_URL: str = "http://127.0.0.1:8053"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Authentication
    ENABLE_2FA: bool = True
    SESSION_TIMEOUT: int = 3600  # seconds
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION: int = 900  # seconds
    TOTP_ISSUER_NAME: str = "Hybrid DNS Server"
    TOTP_VALID_WINDOW: int = 1
    
    # Background Tasks
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Threat Intelligence
    THREAT_FEED_UPDATE_INTERVAL: int = 3600  # seconds
    THREAT_FEEDS: List[str] = [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "https://someonewhocares.org/hosts/zero/hosts",
        "https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/BaseFilter/sections/adservers.txt"
    ]
    
    # Backup Settings
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL: int = 86400  # seconds (daily)
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_DIR: str = "/var/backups/dns-server"
    BACKUP_SCHEDULE: str = "0 2 * * *"
    
    # Email Notifications (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    NOTIFICATION_FROM_EMAIL: Optional[str] = None
    NOTIFICATION_ADMIN_EMAILS: List[str] = []
    
    # File Paths
    @property
    def config_dir(self) -> Path:
        """Get configuration directory path"""
        return Path(self.CUSTOM_CONFIG_DIR or self.BIND9_CONFIG_DIR)
    
    @property
    def zones_dir(self) -> Path:
        """Get zones directory path"""
        return Path(self.CUSTOM_ZONES_DIR or self.BIND9_ZONES_DIR)
    
    @property
    def rpz_dir(self) -> Path:
        """Get RPZ directory path"""
        return Path(self.CUSTOM_RPZ_DIR or self.BIND9_RPZ_DIR)
    
    @property
    def log_dir(self) -> Path:
        """Get log directory path"""
        return Path(self.BIND9_LOG_DIR)
    
    # Configuration file paths
    @property
    def named_conf_options(self) -> Path:
        """Path to named.conf.options"""
        return self.config_dir / "named.conf.options"
    
    @property
    def named_conf_local(self) -> Path:
        """Path to named.conf.local"""
        return self.config_dir / "named.conf.local"
    
    @property
    def zones_conf(self) -> Path:
        """Path to zones.conf (dynamically managed)"""
        return self.config_dir / "zones.conf"
    
    class Config:
        # Look for .env file in multiple locations
        env_file = [".env", "../.env"]
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for getting specific setting values
def get_setting(key: str, default=None):
    """Get a specific setting value"""
    settings = get_settings()
    return getattr(settings, key, default)