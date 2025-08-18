"""
Security-related SQLAlchemy models for the Hybrid DNS Server
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .dns import Base


class RPZRule(Base):
    """Response Policy Zone Rule model for DNS security filtering"""
    __tablename__ = "rpz_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    rpz_zone = Column(String(50), nullable=False)  # malware, phishing, adult, etc.
    action = Column(String(20), nullable=False)  # block, redirect, passthru
    redirect_target = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(50), nullable=True)  # manual, threat_feed, auto
    description = Column(String(500), nullable=True)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="rpz_rules_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="rpz_rules_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("action IN ('block', 'redirect', 'passthru')", name='check_rpz_action'),
        CheckConstraint("rpz_zone IN ('malware', 'phishing', 'adult', 'social-media', 'gambling', 'custom')", name='check_rpz_zone'),
        CheckConstraint("length(domain) >= 1", name='check_domain_not_empty'),
        CheckConstraint("(action = 'redirect' AND redirect_target IS NOT NULL) OR action != 'redirect'", name='check_redirect_target'),
    )
    
    def __repr__(self):
        return f"<RPZRule(id={self.id}, domain='{self.domain}', action='{self.action}')>"
    
    def __str__(self):
        return f"RPZ Rule: {self.domain} -> {self.action}"


class ThreatFeed(Base):
    """Threat Feed model for managing external threat intelligence sources"""
    __tablename__ = "threat_feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    feed_type = Column(String(50), nullable=False)  # malware, phishing, adult, etc.
    format_type = Column(String(20), nullable=False)  # hosts, domains, rpz
    is_active = Column(Boolean, default=True, nullable=False)
    update_frequency = Column(Integer, default=3600, nullable=False)  # seconds
    last_updated = Column(DateTime, nullable=True)
    last_update_status = Column(String(20), nullable=True)  # success, failed, pending
    last_update_error = Column(Text, nullable=True)
    rules_count = Column(Integer, default=0, nullable=False)
    description = Column(String(500), nullable=True)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="threat_feeds_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="threat_feeds_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("feed_type IN ('malware', 'phishing', 'adult', 'social-media', 'gambling', 'custom')", name='check_feed_type'),
        CheckConstraint("format_type IN ('hosts', 'domains', 'rpz')", name='check_format_type'),
        CheckConstraint("update_frequency >= 300", name='check_update_frequency_minimum'),  # At least 5 minutes
        CheckConstraint("rules_count >= 0", name='check_rules_count_positive'),
        CheckConstraint("length(name) >= 1", name='check_feed_name_not_empty'),
        CheckConstraint("length(url) >= 1", name='check_feed_url_not_empty'),
        CheckConstraint("last_update_status IS NULL OR last_update_status IN ('success', 'failed', 'pending')", name='check_update_status'),
    )
    
    def __repr__(self):
        return f"<ThreatFeed(id={self.id}, name='{self.name}', type='{self.feed_type}')>"
    
    def __str__(self):
        return f"Threat Feed: {self.name} ({self.feed_type})"


# Database indexes for performance optimization
# These indexes are created automatically when the tables are created

# RPZ rule indexes for security filtering
Index('idx_rpz_rules_domain_active', RPZRule.domain, RPZRule.is_active)
Index('idx_rpz_rules_zone_action', RPZRule.rpz_zone, RPZRule.action)
Index('idx_rpz_rules_zone_active', RPZRule.rpz_zone, RPZRule.is_active)
Index('idx_rpz_rules_source', RPZRule.source)
Index('idx_rpz_rules_created_by', RPZRule.created_by)
Index('idx_rpz_rules_updated_by', RPZRule.updated_by)

# Threat feed indexes for feed management
Index('idx_threat_feeds_type_active', ThreatFeed.feed_type, ThreatFeed.is_active)
Index('idx_threat_feeds_last_updated', ThreatFeed.last_updated)
Index('idx_threat_feeds_update_status', ThreatFeed.last_update_status)
Index('idx_threat_feeds_created_by', ThreatFeed.created_by)
Index('idx_threat_feeds_updated_by', ThreatFeed.updated_by)