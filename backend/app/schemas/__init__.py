# Schemas package

from .dns import (
    # Zone schemas
    ZoneBase,
    ZoneCreate,
    ZoneUpdate,
    Zone,
    # DNS Record schemas
    DNSRecordBase,
    DNSRecordCreate,
    DNSRecordUpdate,
    DNSRecord,
    # Forwarder schemas
    ForwarderServer,
    ForwarderBase,
    ForwarderCreate,
    ForwarderUpdate,
    Forwarder,
    # Forwarder Health schemas
    ForwarderHealthBase,
    ForwarderHealthCreate,
    ForwarderHealthUpdate,
    ForwarderHealth,
    # Response schemas
    PaginatedResponse,
    HealthCheckResult,
    ZoneValidationResult,
    ValidationResult,
    # Enums
    ZoneType,
    RecordType,
    ForwarderType,
)

from .security import (
    # ThreatFeed schemas
    ThreatFeedBase,
    ThreatFeedCreate,
    ThreatFeedUpdate,
    ThreatFeed,
    ThreatFeedStatus,
    ThreatFeedUpdateResult,
    BulkThreatFeedUpdateResult,
    # RPZ schemas
    RPZRuleBase,
    RPZRuleCreate,
    RPZRuleUpdate,
    RPZRule,
    RPZRuleImportResult,
    # Enums
    FeedType,
    FormatType,
    UpdateStatus,
    RPZAction,
)

from .system import (
    # SystemConfig schemas
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfig,
    SystemConfigPublic,
    # System Status schemas
    ServiceStatus,
    DatabaseStatus,
    BindStatus,
    SystemStatus,
    SystemMetrics,
    SystemInfo,
    BackupStatus,
    MaintenanceStatus,
    SystemSummary,
    # Validation schemas
    ConfigValidationResult,
    BulkConfigUpdate,
    BulkConfigUpdateResult,
    # ACL schemas
    ACLEntryBase,
    ACLEntryCreate,
    ACLEntryUpdate,
    ACLEntry,
    ACLBase,
    ACLCreate,
    ACLUpdate,
    ACL,
    ACLSummary,
    BulkACLEntryUpdate,
    ACLValidationResult,
    ACLConfigurationTemplate,
    # Enums
    ValueType,
    ConfigCategory,
    SystemHealthStatus,
    ACLType,
)

from .monitoring import (
    # DNS Log schemas
    DNSLogBase,
    DNSLogCreate,
    DNSLogUpdate,
    DNSLog,
    # System Stats schemas
    SystemStatsBase,
    SystemStatsCreate,
    SystemStatsUpdate,
    SystemStats,
    # Audit Log schemas
    AuditLogBase,
    AuditLogCreate,
    AuditLogUpdate,
    AuditLog,
    # Query schemas
    DNSLogQuery,
    SystemStatsQuery,
    AuditLogQuery,
    # Analytics schemas
    DNSQueryStats,
    SystemMetricsSummary,
    AuditSummary,
    MonitoringDashboard,
    # Enums
    MetricType,
    QueryType,
    ResourceType,
)

from .auth import (
    # Authentication schemas
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    ChangePasswordRequest,
    # User schemas
    UserInfo,
    UserCreate,
    UserUpdate,
    # Session schemas
    SessionInfo,
    SessionCreate,
    SessionUpdate,
    # Password reset schemas
    PasswordResetRequest,
    PasswordResetConfirm,
    # API Key schemas
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyInfo,
)

__all__ = [
    # Zone schemas
    "ZoneBase",
    "ZoneCreate",
    "ZoneUpdate",
    "Zone",
    # DNS Record schemas
    "DNSRecordBase",
    "DNSRecordCreate",
    "DNSRecordUpdate",
    "DNSRecord",
    # Forwarder schemas
    "ForwarderServer",
    "ForwarderBase",
    "ForwarderCreate",
    "ForwarderUpdate",
    "Forwarder",
    # Forwarder Health schemas
    "ForwarderHealthBase",
    "ForwarderHealthCreate",
    "ForwarderHealthUpdate",
    "ForwarderHealth",
    # Response schemas
    "PaginatedResponse",
    "HealthCheckResult",
    "ZoneValidationResult",
    "ValidationResult",
    "SystemStatus",
    # ThreatFeed schemas
    "ThreatFeedBase",
    "ThreatFeedCreate", 
    "ThreatFeedUpdate",
    "ThreatFeed",
    "ThreatFeedStatus",
    "ThreatFeedUpdateResult",
    "BulkThreatFeedUpdateResult",
    # RPZ schemas
    "RPZRuleBase",
    "RPZRuleCreate",
    "RPZRuleUpdate", 
    "RPZRule",
    "RPZRuleImportResult",
    # SystemConfig schemas
    "SystemConfigBase",
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfig",
    "SystemConfigPublic",
    # System Status schemas
    "ServiceStatus",
    "DatabaseStatus",
    "BindStatus",
    "SystemMetrics",
    "SystemInfo",
    "BackupStatus",
    "MaintenanceStatus",
    "SystemSummary",
    # Validation schemas
    "ConfigValidationResult",
    "BulkConfigUpdate",
    "BulkConfigUpdateResult",
    # ACL schemas
    "ACLEntryBase",
    "ACLEntryCreate",
    "ACLEntryUpdate",
    "ACLEntry",
    "ACLBase",
    "ACLCreate",
    "ACLUpdate",
    "ACL",
    "ACLSummary",
    "BulkACLEntryUpdate",
    "ACLValidationResult",
    "ACLConfigurationTemplate",
    # DNS Log schemas
    "DNSLogBase",
    "DNSLogCreate",
    "DNSLogUpdate",
    "DNSLog",
    # System Stats schemas
    "SystemStatsBase",
    "SystemStatsCreate",
    "SystemStatsUpdate",
    "SystemStats",
    # Audit Log schemas
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogUpdate",
    "AuditLog",
    # Query schemas
    "DNSLogQuery",
    "SystemStatsQuery",
    "AuditLogQuery",
    # Analytics schemas
    "DNSQueryStats",
    "SystemMetricsSummary",
    "AuditSummary",
    "MonitoringDashboard",
    # Authentication schemas
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "RefreshTokenRequest",
    "TwoFactorSetupResponse",
    "TwoFactorVerifyRequest",
    "ChangePasswordRequest",
    # User schemas
    "UserInfo",
    "UserCreate",
    "UserUpdate",
    # Session schemas
    "SessionInfo",
    "SessionCreate",
    "SessionUpdate",
    # Password reset schemas
    "PasswordResetRequest",
    "PasswordResetConfirm",
    # API Key schemas
    "ApiKeyCreate",
    "ApiKeyUpdate",
    "ApiKeyInfo",
    # Enums
    "ZoneType",
    "RecordType",
    "ForwarderType",
    "RPZAction",
    "FeedType",
    "FormatType",
    "UpdateStatus",
    "ValueType",
    "ConfigCategory",
    "SystemHealthStatus",
    "ACLType",
    "MetricType",
    "QueryType",
    "ResourceType",
]