"""
Monitoring-related Pydantic schemas for the Hybrid DNS Server
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Metric types for system statistics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class QueryType(str, Enum):
    """DNS query types"""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    PTR = "PTR"
    NS = "NS"
    SOA = "SOA"
    ANY = "ANY"


class ResourceType(str, Enum):
    """Resource types for audit logging"""
    ZONE = "zone"
    DNS_RECORD = "dns_record"
    FORWARDER = "forwarder"
    RPZ_RULE = "rpz_rule"
    THREAT_FEED = "threat_feed"
    SYSTEM_CONFIG = "system_config"
    USER = "user"
    SESSION = "session"
    API_KEY = "api_key"


# DNS Log Schemas
class DNSLogBase(BaseModel):
    """Base schema for DNS logs"""
    timestamp: datetime = Field(..., description="Timestamp of the DNS query")
    client_ip: str = Field(..., min_length=7, max_length=45, description="Client IP address")
    query_domain: str = Field(..., min_length=1, max_length=255, description="Queried domain name")
    query_type: QueryType = Field(..., description="DNS query type")
    response_code: str = Field(..., min_length=1, max_length=20, description="DNS response code")
    response_time: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")
    blocked: bool = Field(default=False, description="Whether the query was blocked")
    rpz_zone: Optional[str] = Field(None, max_length=50, description="RPZ zone that blocked the query")
    forwarder_used: Optional[str] = Field(None, max_length=45, description="Forwarder server used")

    @validator('client_ip')
    def validate_client_ip(cls, v):
        """Validate client IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

    @validator('query_domain')
    def validate_query_domain(cls, v):
        """Validate domain name format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Query domain cannot be empty')
        return v.lower().strip()


class DNSLogCreate(DNSLogBase):
    """Schema for creating DNS log entries"""
    pass


class DNSLogUpdate(BaseModel):
    """Schema for updating DNS log entries (limited fields)"""
    blocked: Optional[bool] = None
    rpz_zone: Optional[str] = Field(None, max_length=50)


class DNSLog(DNSLogBase):
    """Schema for DNS log response"""
    id: int

    class Config:
        from_attributes = True


# System Stats Schemas
class SystemStatsBase(BaseModel):
    """Base schema for system statistics"""
    timestamp: datetime = Field(..., description="Timestamp of the metric")
    metric_name: str = Field(..., min_length=1, max_length=100, description="Name of the metric")
    metric_value: str = Field(..., min_length=1, max_length=500, description="Value of the metric")
    metric_type: MetricType = Field(..., description="Type of the metric")

    @validator('metric_name')
    def validate_metric_name(cls, v):
        """Validate metric name format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Metric name cannot be empty')
        return v.strip()

    @validator('metric_value')
    def validate_metric_value(cls, v):
        """Validate metric value format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Metric value cannot be empty')
        return v.strip()


class SystemStatsCreate(SystemStatsBase):
    """Schema for creating system statistics entries"""
    pass


class SystemStatsUpdate(BaseModel):
    """Schema for updating system statistics entries"""
    metric_value: Optional[str] = Field(None, min_length=1, max_length=500)
    metric_type: Optional[MetricType] = None


class SystemStats(SystemStatsBase):
    """Schema for system statistics response"""
    id: int

    class Config:
        from_attributes = True


# Audit Log Schemas
class AuditLogBase(BaseModel):
    """Base schema for audit logs"""
    timestamp: datetime = Field(..., description="Timestamp of the action")
    user_id: Optional[int] = Field(None, description="ID of the user who performed the action")
    action: str = Field(..., min_length=1, max_length=100, description="Action performed")
    resource_type: ResourceType = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, max_length=100, description="ID of the resource affected")
    details: Optional[str] = Field(None, description="Additional details about the action")
    ip_address: Optional[str] = Field(None, min_length=7, max_length=45, description="IP address of the client")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")

    @validator('action')
    def validate_action(cls, v):
        """Validate action format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Action cannot be empty')
        return v.strip()

    @validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format"""
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError:
                raise ValueError('Invalid IP address format')
        return v


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log entries"""
    pass


class AuditLogUpdate(BaseModel):
    """Schema for updating audit log entries (limited fields)"""
    details: Optional[str] = None


class AuditLog(AuditLogBase):
    """Schema for audit log response"""
    id: int

    class Config:
        from_attributes = True


# Query and filtering schemas
class DNSLogQuery(BaseModel):
    """Schema for DNS log query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    client_ip: Optional[str] = None
    query_domain: Optional[str] = None
    query_type: Optional[QueryType] = None
    blocked: Optional[bool] = None
    rpz_zone: Optional[str] = None
    forwarder_used: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class SystemStatsQuery(BaseModel):
    """Schema for system statistics query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metric_name: Optional[str] = None
    metric_type: Optional[MetricType] = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class AuditLogQuery(BaseModel):
    """Schema for audit log query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


# Analytics and reporting schemas
class DNSQueryStats(BaseModel):
    """Schema for DNS query statistics"""
    total_queries: int = 0
    blocked_queries: int = 0
    unique_clients: int = 0
    unique_domains: int = 0
    top_domains: List[dict] = []
    top_clients: List[dict] = []
    query_types: dict = {}
    response_codes: dict = {}
    blocked_by_rpz: dict = {}
    
    class Config:
        from_attributes = True


class SystemMetricsSummary(BaseModel):
    """Schema for system metrics summary"""
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    network_io: Optional[dict] = None
    dns_queries_per_minute: Optional[int] = None
    active_connections: Optional[int] = None
    uptime: Optional[int] = None
    
    class Config:
        from_attributes = True


class AuditSummary(BaseModel):
    """Schema for audit log summary"""
    total_actions: int = 0
    unique_users: int = 0
    actions_by_type: dict = {}
    resources_by_type: dict = {}
    recent_actions: List[dict] = []
    failed_actions: int = 0
    
    class Config:
        from_attributes = True


class MonitoringDashboard(BaseModel):
    """Schema for monitoring dashboard data"""
    dns_stats: DNSQueryStats
    system_metrics: SystemMetricsSummary
    audit_summary: AuditSummary
    alerts: List[dict] = []
    last_updated: datetime
    
    class Config:
        from_attributes = True