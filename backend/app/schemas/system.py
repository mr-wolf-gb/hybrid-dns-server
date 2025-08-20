"""
System-related Pydantic schemas for the Hybrid DNS Server
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum
import json


class ValueType(str, Enum):
    """System configuration value types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigCategory(str, Enum):
    """System configuration categories"""
    DNS = "dns"
    SECURITY = "security"
    MONITORING = "monitoring"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    SYSTEM = "system"


class SystemHealthStatus(str, Enum):
    """System health status values"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# SystemConfig Schemas
class SystemConfigBase(BaseModel):
    """Base schema for SystemConfig"""
    key: str = Field(..., min_length=1, max_length=100, description="Configuration key")
    value: str = Field(..., min_length=1, description="Configuration value")
    value_type: ValueType = Field(..., description="Type of the configuration value")
    category: ConfigCategory = Field(..., description="Configuration category")
    description: Optional[str] = Field(None, max_length=500, description="Description of the configuration")
    is_sensitive: bool = Field(default=False, description="Whether this is sensitive data")

    @validator('key')
    def validate_key(cls, v):
        """Validate configuration key format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Configuration key cannot be empty')
        # Key should be alphanumeric with underscores and dots
        if not all(c.isalnum() or c in '._-' for c in v):
            raise ValueError('Configuration key can only contain alphanumeric characters, dots, underscores, and hyphens')
        return v.lower().strip()

    @model_validator(mode='after')
    def validate_value_format(self):
        """Validate value format based on value_type"""
        value_type = self.value_type
        value = self.value
        
        if value_type == ValueType.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                raise ValueError('Value must be a valid integer')
        elif value_type == ValueType.BOOLEAN:
            if not isinstance(value, str) or value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                raise ValueError('Boolean value must be true/false, 1/0, or yes/no')
        elif value_type == ValueType.JSON:
            try:
                json.loads(value)
            except (json.JSONDecodeError, TypeError):
                raise ValueError('Value must be valid JSON')
        return self


class SystemConfigCreate(SystemConfigBase):
    """Schema for creating system configuration"""
    pass


class SystemConfigUpdate(BaseModel):
    """Schema for updating system configuration"""
    value: Optional[str] = Field(None, min_length=1)
    value_type: Optional[ValueType] = None
    category: Optional[ConfigCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    is_sensitive: Optional[bool] = None

    @model_validator(mode='after')
    def validate_value_format(self):
        """Validate value format based on value_type"""
        if self.value is None:
            return self
            
        value_type = self.value_type
        value = self.value
        
        if value_type == ValueType.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                raise ValueError('Value must be a valid integer')
        elif value_type == ValueType.BOOLEAN:
            if not isinstance(value, str) or value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                raise ValueError('Boolean value must be true/false, 1/0, or yes/no')
        elif value_type == ValueType.JSON:
            try:
                json.loads(value)
            except (json.JSONDecodeError, TypeError):
                raise ValueError('Value must be valid JSON')
        return self


class SystemConfig(SystemConfigBase):
    """Schema for SystemConfig response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigPublic(BaseModel):
    """Schema for public system configuration (sensitive values hidden)"""
    id: int
    key: str
    value: Optional[str] = None  # Hidden if sensitive
    value_type: ValueType
    category: ConfigCategory
    description: Optional[str] = None
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# System Status Schemas
class ServiceStatus(BaseModel):
    """Schema for individual service status"""
    name: str
    status: SystemHealthStatus
    uptime: Optional[int] = None  # seconds
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class DatabaseStatus(BaseModel):
    """Schema for database status"""
    connected: bool
    connection_pool_size: Optional[int] = None
    active_connections: Optional[int] = None
    response_time: Optional[float] = None  # milliseconds
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class BindStatus(BaseModel):
    """Schema for BIND9 DNS server status"""
    running: bool
    config_valid: bool
    zones_loaded: int = 0
    queries_per_second: Optional[float] = None
    uptime: Optional[int] = None  # seconds
    version: Optional[str] = None
    last_reload: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class SystemStatus(BaseModel):
    """Schema for overall system status"""
    overall_status: SystemHealthStatus
    bind9: BindStatus
    database: DatabaseStatus
    services: List[ServiceStatus] = []
    system_info: Dict[str, Any] = {}
    last_updated: datetime
    
    class Config:
        from_attributes = True


class SystemMetrics(BaseModel):
    """Schema for system performance metrics"""
    cpu_usage: Optional[float] = None  # percentage
    memory_usage: Optional[float] = None  # percentage
    disk_usage: Optional[float] = None  # percentage
    network_io: Optional[Dict[str, int]] = None  # bytes in/out
    dns_queries_per_minute: Optional[int] = None
    active_zones: int = 0
    active_forwarders: int = 0
    active_rpz_rules: int = 0
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SystemInfo(BaseModel):
    """Schema for basic system information"""
    hostname: str
    os_name: str
    os_version: str
    python_version: str
    application_version: str
    uptime: int  # seconds
    timezone: str
    
    class Config:
        from_attributes = True


class BackupStatus(BaseModel):
    """Schema for backup status information"""
    last_backup: Optional[datetime] = None
    backup_size: Optional[int] = None  # bytes
    backup_location: Optional[str] = None
    auto_backup_enabled: bool = False
    next_scheduled_backup: Optional[datetime] = None
    backup_retention_days: int = 30
    
    class Config:
        from_attributes = True


class MaintenanceStatus(BaseModel):
    """Schema for maintenance status"""
    maintenance_mode: bool = False
    scheduled_maintenance: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    maintenance_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class SystemSummary(BaseModel):
    """Schema for system summary dashboard"""
    status: SystemStatus
    metrics: SystemMetrics
    info: SystemInfo
    backup: BackupStatus
    maintenance: MaintenanceStatus
    
    class Config:
        from_attributes = True


# Configuration validation schemas
class ConfigValidationResult(BaseModel):
    """Schema for configuration validation results"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    affected_services: List[str] = []
    
    class Config:
        from_attributes = True


class BulkConfigUpdate(BaseModel):
    """Schema for bulk configuration updates"""
    configs: List[SystemConfigCreate]
    validate_only: bool = False


class BulkConfigUpdateResult(BaseModel):
    """Schema for bulk configuration update results"""
    total_processed: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    validation_errors: List[str] = []
    updated_configs: List[str] = []
    failed_configs: List[str] = []
    
    class Config:
        from_attributes = True


# ACL Schemas
class ACLType(str, Enum):
    """ACL types for BIND9 configuration"""
    TRUSTED = "trusted"
    BLOCKED = "blocked"
    MANAGEMENT = "management"
    DNS_SERVERS = "dns-servers"
    MONITORING = "monitoring"
    RATE_LIMITED = "rate-limited"
    DYNAMIC_THREATS = "dynamic-threats"
    DYNAMIC_ALLOW = "dynamic-allow"
    CUSTOM = "custom"


class ACLEntryBase(BaseModel):
    """Base schema for ACL entries"""
    address: str = Field(..., min_length=1, max_length=100, description="IP address or network (e.g., '192.168.1.0/24', '!10.0.0.1')")
    comment: Optional[str] = Field(None, max_length=200, description="Optional comment for documentation")
    is_active: bool = Field(default=True, description="Whether this entry is active")

    @validator('address')
    def validate_address(cls, v):
        """Validate IP address or network format"""
        import ipaddress
        import re
        
        if not v or len(v.strip()) == 0:
            raise ValueError('Address cannot be empty')
        
        address = v.strip()
        
        # Handle negation prefix
        negated = False
        if address.startswith('!'):
            negated = True
            address = address[1:].strip()
        
        # Validate IP address or network
        try:
            # Try to parse as network first (handles both single IPs and networks)
            ipaddress.ip_network(address, strict=False)
        except ValueError:
            # Check if it's a valid hostname/domain
            hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(hostname_pattern, address):
                raise ValueError('Address must be a valid IP address, network, or hostname')
        
        return v.strip()


class ACLEntryCreate(ACLEntryBase):
    """Schema for creating ACL entries"""
    pass


class ACLEntryUpdate(BaseModel):
    """Schema for updating ACL entries"""
    address: Optional[str] = Field(None, min_length=1, max_length=100)
    comment: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

    @validator('address')
    def validate_address(cls, v):
        """Validate IP address or network format"""
        if v is None:
            return v
        return ACLEntryBase.validate_address(v)


class ACLEntry(ACLEntryBase):
    """Schema for ACL entry response"""
    id: int
    acl_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ACLBase(BaseModel):
    """Base schema for ACLs"""
    name: str = Field(..., min_length=1, max_length=100, description="ACL name (used in BIND config)")
    acl_type: ACLType = Field(..., description="Type of ACL")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    is_active: bool = Field(default=True, description="Whether this ACL is active")

    @validator('name')
    def validate_name(cls, v):
        """Validate ACL name format for BIND9 compatibility"""
        import re
        
        if not v or len(v.strip()) == 0:
            raise ValueError('ACL name cannot be empty')
        
        name = v.strip()
        
        # BIND9 ACL names must be valid identifiers
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
            raise ValueError('ACL name must start with a letter and contain only letters, numbers, underscores, and hyphens')
        
        # Reserved BIND9 ACL names
        reserved_names = ['any', 'none', 'localhost', 'localnets']
        if name.lower() in reserved_names:
            raise ValueError(f'ACL name "{name}" is reserved by BIND9')
        
        return name


class ACLCreate(ACLBase):
    """Schema for creating ACLs"""
    entries: List[ACLEntryCreate] = Field(default=[], description="Initial ACL entries")


class ACLUpdate(BaseModel):
    """Schema for updating ACLs"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    acl_type: Optional[ACLType] = None
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @validator('name')
    def validate_name(cls, v):
        """Validate ACL name format for BIND9 compatibility"""
        if v is None:
            return v
        return ACLBase.validate_name(v)


class ACL(ACLBase):
    """Schema for ACL response"""
    id: int
    entries: List[ACLEntry] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ACLSummary(BaseModel):
    """Schema for ACL summary (without entries)"""
    id: int
    name: str
    acl_type: ACLType
    description: Optional[str] = None
    is_active: bool
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkACLEntryUpdate(BaseModel):
    """Schema for bulk ACL entry updates"""
    entries: List[ACLEntryCreate]
    replace_all: bool = Field(default=False, description="Whether to replace all existing entries")


class ACLValidationResult(BaseModel):
    """Schema for ACL validation results"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    entry_count: int = 0
    
    class Config:
        from_attributes = True


class ACLConfigurationTemplate(BaseModel):
    """Schema for ACL configuration template data"""
    acls: List[ACL] = []
    include_predefined_acls: bool = True
    include_security_acls: bool = True
    include_dynamic_acls: bool = False
    trusted_networks: List[str] = []
    management_networks: List[str] = []
    dns_servers: List[str] = []
    monitoring_systems: List[str] = []
    blocked_networks: List[str] = []
    rate_limited_networks: List[str] = []
    dynamic_threats: List[Dict[str, str]] = []
    dynamic_allow: List[Dict[str, str]] = []
    generated_at: datetime
    config_version: str = "1.0"

    class Config:
        from_attributes = True