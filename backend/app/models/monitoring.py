"""
Monitoring and logging SQLAlchemy models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .dns import Base


class DNSLog(Base):
    """DNS Log model for storing DNS query logs"""
    __tablename__ = "dns_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    client_ip = Column(String(45), nullable=False)
    query_domain = Column(String(255), nullable=False)
    query_type = Column(String(10), nullable=False)
    response_code = Column(String(20), nullable=False)
    response_time = Column(Integer, nullable=True)  # milliseconds
    blocked = Column(Boolean, default=False, nullable=False)
    rpz_zone = Column(String(50), nullable=True)
    forwarder_used = Column(String(45), nullable=True)
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("length(client_ip) >= 7", name='check_client_ip_valid'),
        CheckConstraint("length(query_domain) >= 1", name='check_query_domain_not_empty'),
        CheckConstraint("query_type IN ('A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS', 'SOA', 'ANY')", name='check_query_type'),
        CheckConstraint("response_time IS NULL OR response_time >= 0", name='check_response_time_positive'),
        CheckConstraint("length(response_code) >= 1", name='check_response_code_not_empty'),
    )
    
    def __repr__(self):
        return f"<DNSLog(id={self.id}, client_ip='{self.client_ip}', domain='{self.query_domain}')>"
    
    def __str__(self):
        return f"DNS Query: {self.client_ip} -> {self.query_domain} ({self.query_type})"


class SystemStats(Base):
    """System Statistics model for storing performance metrics"""
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(String(500), nullable=False)
    metric_type = Column(String(20), nullable=False)  # counter, gauge, histogram
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("metric_type IN ('counter', 'gauge', 'histogram')", name='check_metric_type'),
        CheckConstraint("length(metric_name) >= 1", name='check_metric_name_not_empty'),
        CheckConstraint("length(metric_value) >= 1", name='check_metric_value_not_empty'),
    )
    
    def __repr__(self):
        return f"<SystemStats(id={self.id}, metric='{self.metric_name}', value='{self.metric_value}')>"
    
    def __str__(self):
        return f"Metric: {self.metric_name} = {self.metric_value}"


class AuditLog(Base):
    """Audit Log model for tracking user actions and system changes"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], overlaps="audit_logs")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("length(action) >= 1", name='check_action_not_empty'),
        CheckConstraint("length(resource_type) >= 1", name='check_resource_type_not_empty'),
        CheckConstraint("ip_address IS NULL OR length(ip_address) >= 7", name='check_audit_ip_valid'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}')>"
    
    def __str__(self):
        return f"Audit: {self.action} on {self.resource_type} (User: {self.user_id})"


# Database indexes for performance optimization
# These indexes are created automatically when the tables are created

# DNS Logs indexes for query analysis and monitoring
Index('idx_dns_logs_timestamp', DNSLog.timestamp)
Index('idx_dns_logs_client_domain', DNSLog.client_ip, DNSLog.query_domain)
Index('idx_dns_logs_blocked', DNSLog.blocked)
Index('idx_dns_logs_query_type', DNSLog.query_type)
Index('idx_dns_logs_timestamp_blocked', DNSLog.timestamp, DNSLog.blocked)
Index('idx_dns_logs_client_timestamp', DNSLog.client_ip, DNSLog.timestamp)
Index('idx_dns_logs_domain_timestamp', DNSLog.query_domain, DNSLog.timestamp)
Index('idx_dns_logs_rpz_zone', DNSLog.rpz_zone)
Index('idx_dns_logs_forwarder_used', DNSLog.forwarder_used)

# System Stats indexes for performance monitoring
Index('idx_system_stats_timestamp_metric', SystemStats.timestamp, SystemStats.metric_name)
Index('idx_system_stats_metric_timestamp', SystemStats.metric_name, SystemStats.timestamp)
Index('idx_system_stats_metric_type', SystemStats.metric_type)

# Audit Logs indexes for security and compliance
Index('idx_audit_logs_timestamp', AuditLog.timestamp)
Index('idx_audit_logs_user_action', AuditLog.user_id, AuditLog.action)
Index('idx_audit_logs_resource', AuditLog.resource_type, AuditLog.resource_id)
Index('idx_audit_logs_action_timestamp', AuditLog.action, AuditLog.timestamp)
Index('idx_audit_logs_resource_timestamp', AuditLog.resource_type, AuditLog.timestamp)
Index('idx_audit_logs_ip_timestamp', AuditLog.ip_address, AuditLog.timestamp)