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


# Database indexes for performance optimization
Index('idx_system_config_category', SystemConfig.category)
Index('idx_system_config_key_category', SystemConfig.key, SystemConfig.category)
Index('idx_system_config_created_by', SystemConfig.created_by)
Index('idx_system_config_updated_by', SystemConfig.updated_by)