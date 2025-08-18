"""
Authentication and user management SQLAlchemy models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .dns import Base


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships with proper cascade delete
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.user_id", passive_deletes=True)
    
    # DNS model relationships (created/updated by user)
    zones_created = relationship("Zone", foreign_keys="Zone.created_by", passive_deletes=True)
    zones_updated = relationship("Zone", foreign_keys="Zone.updated_by", passive_deletes=True)
    dns_records_created = relationship("DNSRecord", foreign_keys="DNSRecord.created_by", passive_deletes=True)
    dns_records_updated = relationship("DNSRecord", foreign_keys="DNSRecord.updated_by", passive_deletes=True)
    forwarders_created = relationship("Forwarder", foreign_keys="Forwarder.created_by", passive_deletes=True)
    forwarders_updated = relationship("Forwarder", foreign_keys="Forwarder.updated_by", passive_deletes=True)
    
    # Security model relationships
    rpz_rules_created = relationship("RPZRule", foreign_keys="RPZRule.created_by", passive_deletes=True)
    rpz_rules_updated = relationship("RPZRule", foreign_keys="RPZRule.updated_by", passive_deletes=True)
    threat_feeds_created = relationship("ThreatFeed", foreign_keys="ThreatFeed.created_by", passive_deletes=True)
    threat_feeds_updated = relationship("ThreatFeed", foreign_keys="ThreatFeed.updated_by", passive_deletes=True)
    
    # System model relationships
    system_configs_created = relationship("SystemConfig", foreign_keys="SystemConfig.created_by", passive_deletes=True)
    system_configs_updated = relationship("SystemConfig", foreign_keys="SystemConfig.updated_by", passive_deletes=True)
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("length(username) >= 3 AND length(username) <= 50", name='check_username_length'),
        CheckConstraint("length(email) >= 5 AND length(email) <= 100", name='check_email_length'),
        CheckConstraint("email LIKE '%@%'", name='check_email_format'),
        CheckConstraint("length(hashed_password) >= 60", name='check_password_hash_length'),  # bcrypt hashes are 60 chars
        CheckConstraint("failed_login_attempts >= 0", name='check_failed_attempts_positive'),
        CheckConstraint("two_factor_secret IS NULL OR length(two_factor_secret) = 32", name='check_2fa_secret_length'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def __str__(self):
        return f"User: {self.username} ({self.email})"


class Session(Base):
    """Session model for managing user sessions"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("length(session_token) >= 32", name='check_session_token_length'),
        CheckConstraint("expires_at > created_at", name='check_session_expiry_future'),
        CheckConstraint("ip_address IS NULL OR length(ip_address) >= 7", name='check_ip_address_valid'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, expires_at='{self.expires_at}')>"
    
    def __str__(self):
        return f"Session: {self.session_token[:8]}... (User: {self.user_id})"


# Database indexes for performance optimization
# These indexes are created automatically when the tables are created

# User indexes for authentication and user management
Index('idx_users_username_active', User.username, User.is_active)
Index('idx_users_email_active', User.email, User.is_active)
Index('idx_users_last_login', User.last_login)
Index('idx_users_locked_until', User.locked_until)
Index('idx_users_two_factor_enabled', User.two_factor_enabled)
Index('idx_users_created_at', User.created_at)

# Session indexes for session management and security
Index('idx_sessions_user_expires', Session.user_id, Session.expires_at)
Index('idx_sessions_token_expires', Session.session_token, Session.expires_at)
Index('idx_sessions_expires_at', Session.expires_at)
Index('idx_sessions_ip_created', Session.ip_address, Session.created_at)