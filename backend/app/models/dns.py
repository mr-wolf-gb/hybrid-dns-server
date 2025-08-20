"""
DNS-related SQLAlchemy models for the Hybrid DNS Server
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Zone(Base):
    """DNS Zone model for managing DNS zones"""
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    zone_type = Column(String(20), nullable=False)  # master, slave, forward
    file_path = Column(String(500), nullable=True)
    master_servers = Column(JSON, nullable=True)  # JSON array for slave zones
    forwarders = Column(JSON, nullable=True)  # JSON array for forward zones
    is_active = Column(Boolean, default=True, nullable=False)
    serial = Column(Integer, nullable=True)
    refresh = Column(Integer, default=10800, nullable=False)
    retry = Column(Integer, default=3600, nullable=False)
    expire = Column(Integer, default=604800, nullable=False)
    minimum = Column(Integer, default=86400, nullable=False)
    email = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships with proper cascade delete
    records = relationship("DNSRecord", back_populates="zone", cascade="all, delete-orphan", passive_deletes=True)
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="zones_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="zones_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("zone_type IN ('master', 'slave', 'forward')", name='check_zone_type'),
        CheckConstraint("refresh >= 300 AND refresh <= 86400", name='check_refresh_range'),
        CheckConstraint("retry >= 300 AND retry <= 86400", name='check_retry_range'),
        CheckConstraint("expire >= 86400 AND expire <= 2419200", name='check_expire_range'),
        CheckConstraint("minimum >= 300 AND minimum <= 86400", name='check_minimum_range'),
        CheckConstraint("serial IS NULL OR serial >= 1", name='check_serial_positive'),
        CheckConstraint("length(name) >= 1", name='check_name_not_empty'),
        CheckConstraint("length(email) >= 1", name='check_email_not_empty'),
    )
    
    def __repr__(self):
        return f"<Zone(id={self.id}, name='{self.name}', type='{self.zone_type}')>"
    
    def __str__(self):
        return f"Zone: {self.name} ({self.zone_type})"


class DNSRecord(Base):
    """DNS Record model for managing individual DNS records within zones"""
    __tablename__ = "dns_records"
    
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    record_type = Column(String(10), nullable=False)  # A, AAAA, CNAME, MX, etc.
    value = Column(String(500), nullable=False)
    ttl = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)  # For MX, SRV records
    weight = Column(Integer, nullable=True)  # For SRV records
    port = Column(Integer, nullable=True)  # For SRV records
    is_active = Column(Boolean, default=True, nullable=False)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    zone = relationship("Zone", back_populates="records")
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="dns_records_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="dns_records_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("record_type IN ('A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS', 'SOA')", name='check_record_type'),
        CheckConstraint("ttl IS NULL OR (ttl >= 60 AND ttl <= 86400)", name='check_ttl_range'),
        CheckConstraint("priority IS NULL OR (priority >= 0 AND priority <= 65535)", name='check_priority_range'),
        CheckConstraint("weight IS NULL OR (weight >= 0 AND weight <= 65535)", name='check_weight_range'),
        CheckConstraint("port IS NULL OR (port >= 1 AND port <= 65535)", name='check_port_range'),
        CheckConstraint("length(name) >= 1", name='check_record_name_not_empty'),
        CheckConstraint("length(value) >= 1", name='check_record_value_not_empty'),
    )
    
    def __repr__(self):
        return f"<DNSRecord(id={self.id}, name='{self.name}', type='{self.record_type}', value='{self.value}')>"
    
    def __str__(self):
        return f"{self.name} {self.record_type} {self.value}"


class Forwarder(Base):
    """DNS Forwarder model for managing conditional forwarding rules"""
    __tablename__ = "forwarders"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domains = Column(JSON, nullable=False)  # JSON array of domains to forward
    forwarder_type = Column(String(20), nullable=False)  # active_directory, intranet, public
    servers = Column(JSON, nullable=False)  # JSON array of server configurations
    is_active = Column(Boolean, default=True, nullable=False)
    health_check_enabled = Column(Boolean, default=True, nullable=False)
    description = Column(String(500), nullable=True)
    # Authentication integration fields
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships with proper cascade delete
    health_checks = relationship("ForwarderHealth", back_populates="forwarder", cascade="all, delete-orphan", passive_deletes=True)
    # User relationships for audit trail
    creator = relationship("User", foreign_keys=[created_by], overlaps="forwarders_created")
    updater = relationship("User", foreign_keys=[updated_by], overlaps="forwarders_updated")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("forwarder_type IN ('active_directory', 'intranet', 'public')", name='check_forwarder_type'),
        CheckConstraint("length(name) >= 1", name='check_forwarder_name_not_empty'),
        # Note: JSON array length validation will be handled at application level for cross-database compatibility
    )
    
    def __repr__(self):
        return f"<Forwarder(id={self.id}, name='{self.name}', type='{self.forwarder_type}')>"
    
    def __str__(self):
        return f"Forwarder: {self.name} ({self.forwarder_type})"


class ForwarderHealth(Base):
    """Forwarder Health model for tracking health status of DNS forwarders"""
    __tablename__ = "forwarder_health"
    
    id = Column(Integer, primary_key=True, index=True)
    forwarder_id = Column(Integer, ForeignKey("forwarders.id", ondelete="CASCADE"), nullable=False)
    server_ip = Column(String(45), nullable=False)
    status = Column(String(20), nullable=False)  # healthy, unhealthy, timeout, error
    response_time = Column(Integer, nullable=True)  # milliseconds
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    forwarder = relationship("Forwarder", back_populates="health_checks")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("status IN ('healthy', 'unhealthy', 'timeout', 'error')", name='check_health_status'),
        CheckConstraint("response_time IS NULL OR response_time >= 0", name='check_response_time_positive'),
        CheckConstraint("length(server_ip) >= 7", name='check_server_ip_valid'),  # Minimum IP length
    )
    
    def __repr__(self):
        return f"<ForwarderHealth(id={self.id}, forwarder_id={self.forwarder_id}, status='{self.status}')>"
    
    def __str__(self):
        return f"Health Check: {self.server_ip} - {self.status}"


class DNSRecordHistory(Base):
    """DNS Record History model for tracking changes to DNS records"""
    __tablename__ = "dns_record_history"
    
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, nullable=False)  # Original record ID (may not exist anymore)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    
    # Record data at time of change
    name = Column(String(255), nullable=False)
    record_type = Column(String(10), nullable=False)
    value = Column(String(500), nullable=False)
    ttl = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    port = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False)
    
    # Change tracking
    change_type = Column(String(20), nullable=False)  # create, update, delete, activate, deactivate
    changed_at = Column(DateTime, server_default=func.now(), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Change details
    change_details = Column(JSON, nullable=True)  # What fields changed
    previous_values = Column(JSON, nullable=True)  # Previous values for updates
    
    # Relationships
    zone = relationship("Zone")
    changed_by_user = relationship("User", foreign_keys=[changed_by])
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("change_type IN ('create', 'update', 'delete', 'activate', 'deactivate')", name='check_change_type'),
        CheckConstraint("length(name) >= 1", name='check_history_name_not_empty'),
        CheckConstraint("length(record_type) >= 1", name='check_history_record_type_not_empty'),
        CheckConstraint("length(value) >= 1", name='check_history_value_not_empty'),
        CheckConstraint("ttl IS NULL OR ttl > 0", name='check_history_ttl_positive'),
        CheckConstraint("priority IS NULL OR priority >= 0", name='check_history_priority_non_negative'),
        CheckConstraint("weight IS NULL OR weight >= 0", name='check_history_weight_non_negative'),
        CheckConstraint("port IS NULL OR (port >= 1 AND port <= 65535)", name='check_history_port_range'),
    )
    
    def __repr__(self):
        return f"<DNSRecordHistory(id={self.id}, record_id={self.record_id}, change_type='{self.change_type}')>"
    
    def __str__(self):
        return f"History: {self.change_type} {self.record_type} record '{self.name}' at {self.changed_at}"


# Security models moved to security.py


# Database indexes for performance optimization
# These indexes are created automatically when the tables are created

# DNS Records indexes for efficient querying
Index('idx_dns_records_zone_type', DNSRecord.zone_id, DNSRecord.record_type)
Index('idx_dns_records_name', DNSRecord.name)
Index('idx_dns_records_active', DNSRecord.is_active)
Index('idx_dns_records_zone_active', DNSRecord.zone_id, DNSRecord.is_active)
Index('idx_dns_records_type_active', DNSRecord.record_type, DNSRecord.is_active)
Index('idx_dns_records_created_by', DNSRecord.created_by)
Index('idx_dns_records_updated_by', DNSRecord.updated_by)

# Zone indexes for zone management
Index('idx_zones_type_active', Zone.zone_type, Zone.is_active)
Index('idx_zones_name_active', Zone.name, Zone.is_active)
Index('idx_zones_updated_at', Zone.updated_at)
Index('idx_zones_created_by', Zone.created_by)
Index('idx_zones_updated_by', Zone.updated_by)

# Forwarder health indexes for monitoring
Index('idx_forwarder_health_forwarder_status', ForwarderHealth.forwarder_id, ForwarderHealth.status)
Index('idx_forwarder_health_checked_at', ForwarderHealth.checked_at)
Index('idx_forwarder_health_server_status', ForwarderHealth.server_ip, ForwarderHealth.status)

# Forwarder indexes for conditional forwarding
Index('idx_forwarders_type_active', Forwarder.forwarder_type, Forwarder.is_active)
Index('idx_forwarders_active', Forwarder.is_active)
Index('idx_forwarders_created_by', Forwarder.created_by)
Index('idx_forwarders_updated_by', Forwarder.updated_by)

# DNS Record History indexes for audit and tracking
Index('idx_dns_record_history_record_id', DNSRecordHistory.record_id)
Index('idx_dns_record_history_zone_id', DNSRecordHistory.zone_id)
Index('idx_dns_record_history_changed_at', DNSRecordHistory.changed_at)
Index('idx_dns_record_history_changed_by', DNSRecordHistory.changed_by)
Index('idx_dns_record_history_change_type', DNSRecordHistory.change_type)
Index('idx_dns_record_history_record_type', DNSRecordHistory.record_type)
Index('idx_dns_record_history_name', DNSRecordHistory.name)

# Security-related indexes moved to security.py


