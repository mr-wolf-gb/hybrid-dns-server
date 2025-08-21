"""
System-related SQLAlchemy models for the Hybrid DNS Server
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .dns import Base


class SystemConfig(Base):
    """System Configuration model for storing global system settings"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), nullable=False)  # string, integer, boolean, json
    category = Column(String(50), nullable=False)  # dns, security, monitoring, etc.
    description = Column(String(500), nullable=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)  # For passwords, API keys, etc.
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="system_configs_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="system_configs_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("value_type IN ('string', 'integer', 'boolean', 'json')", name='check_value_type'),
        CheckConstraint("category IN ('dns', 'security', 'monitoring', 'auth', 'system')", name='check_category'),
        CheckConstraint("length(key) >= 1", name='check_config_key_not_empty'),
        CheckConstraint("length(value) >= 1", name='check_config_value_not_empty'),
        CheckConstraint("length(category) >= 1", name='check_config_category_not_empty'),
    )
    
    def __repr__(self):
        return f"<SystemConfig(id={self.id}, key='{self.key}', category='{self.category}')>"
    
    def __str__(self):
        return f"Config: {self.key} = {self.value if not self.is_sensitive else '***'}"


class ACL(Base):
    """Access Control List model for BIND9 ACL configuration"""
    __tablename__ = "acls"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    acl_type = Column(String(50), nullable=False)  # trusted, blocked, management, dns-servers, etc.
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    entries = relationship("ACLEntry", back_populates="acl", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by], overlaps="acls_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="acls_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("acl_type IN ('trusted', 'blocked', 'management', 'dns-servers', 'monitoring', 'rate-limited', 'dynamic-threats', 'dynamic-allow', 'custom')", name='check_acl_type'),
        CheckConstraint("length(name) >= 1", name='check_acl_name_not_empty'),
        CheckConstraint("name ~ '^[a-zA-Z0-9_-]+$'", name='check_acl_name_format'),  # Valid BIND ACL name format (PostgreSQL regex)
    )
    
    def __repr__(self):
        return f"<ACL(id={self.id}, name='{self.name}', type='{self.acl_type}')>"
    
    def __str__(self):
        return f"ACL: {self.name} ({self.acl_type}) - {len(self.entries) if self.entries else 0} entries"


class ACLEntry(Base):
    """ACL Entry model for individual IP addresses/networks in an ACL"""
    __tablename__ = "acl_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    acl_id = Column(Integer, ForeignKey("acls.id", ondelete="CASCADE"), nullable=False)
    address = Column(String(100), nullable=False)  # IP address or network (e.g., "192.168.1.0/24", "!10.0.0.1")
    comment = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    acl = relationship("ACL", back_populates="entries")
    creator = relationship("User", foreign_keys=[created_by], overlaps="acl_entries_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="acl_entries_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("length(address) >= 1", name='check_acl_entry_address_not_empty'),
        # Ensure unique address per ACL
        Index('idx_acl_entry_unique', 'acl_id', 'address', unique=True),
    )
    
    def __repr__(self):
        return f"<ACLEntry(id={self.id}, acl_id={self.acl_id}, address='{self.address}')>"
    
    def __str__(self):
        return f"ACL Entry: {self.address} ({self.comment or 'No comment'})"


# Database indexes for performance optimization
Index('idx_system_config_category', SystemConfig.category)
Index('idx_system_config_key_category', SystemConfig.key, SystemConfig.category)
Index('idx_system_config_created_by', SystemConfig.created_by)
Index('idx_system_config_updated_by', SystemConfig.updated_by)

# ACL indexes
Index('idx_acl_name', ACL.name)
Index('idx_acl_type', ACL.acl_type)
Index('idx_acl_active', ACL.is_active)
Index('idx_acl_created_by', ACL.created_by)
Index('idx_acl_updated_by', ACL.updated_by)

# ACL Entry indexes
Index('idx_acl_entry_acl_id', ACLEntry.acl_id)
Index('idx_acl_entry_address', ACLEntry.address)
Index('idx_acl_entry_active', ACLEntry.is_active)
Index('idx_acl_entry_created_by', ACLEntry.created_by)
Index('idx_acl_entry_updated_by', ACLEntry.updated_by)