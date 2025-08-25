"""
Comprehensive event types and data models for the unified WebSocket system
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import uuid


class EventType(Enum):
    """Comprehensive WebSocket event types for all system operations"""
    
    # Health and monitoring events
    HEALTH_UPDATE = "health_update"
    HEALTH_ALERT = "health_alert"
    FORWARDER_STATUS_CHANGE = "forwarder_status_change"
    FORWARDER_HEALTH_CHECK = "forwarder_health_check"
    SYSTEM_STATUS = "system_status"
    SYSTEM_METRICS = "system_metrics"
    PERFORMANCE_ALERT = "performance_alert"
    RESOURCE_USAGE = "resource_usage"
    BIND_STATUS_UPDATE = "bind_status_update"
    NETWORK_INTERFACE_METRICS = "network_interface_metrics"
    NETWORK_METRICS = "network_metrics"
    DISK_METRICS = "disk_metrics"
    
    # DNS management events
    ZONE_CREATED = "zone_created"
    ZONE_UPDATED = "zone_updated"
    ZONE_DELETED = "zone_deleted"
    ZONE_IMPORTED = "zone_imported"
    ZONE_EXPORTED = "zone_exported"
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    RECORD_BULK_OPERATION = "record_bulk_operation"
    BIND_RELOAD = "bind_reload"
    BIND_CONFIG_CHANGE = "bind_config_change"
    CONFIG_CHANGE = "config_change"
    CONFIG_BACKUP = "config_backup"
    CONFIG_RESTORE = "config_restore"
    
    # DNS query and analytics events
    DNS_QUERY_LOG = "dns_query_log"
    DNS_QUERY_BATCH = "dns_query_batch"
    DNS_QUERY_STATISTICS = "dns_query_statistics"
    DNS_QUERY_STATS = "dns_query_stats"
    DNS_QUERY_BLOCKED = "dns_query_blocked"
    DNS_QUERY_ALLOWED = "dns_query_allowed"
    DNS_ANALYTICS_UPDATE = "dns_analytics_update"
    DNS_QUERY_STREAM = "dns_query_stream"
    DNS_QUERY_REALTIME = "dns_query_realtime"
    
    # Security events
    SECURITY_ALERT = "security_alert"
    SECURITY_THREAT_DETECTED = "security_threat_detected"
    RPZ_UPDATE = "rpz_update"
    RPZ_RULE_CREATED = "rpz_rule_created"
    RPZ_RULE_UPDATED = "rpz_rule_updated"
    RPZ_RULE_DELETED = "rpz_rule_deleted"
    THREAT_DETECTED = "threat_detected"
    THREAT_FEED_UPDATE = "threat_feed_update"
    MALWARE_BLOCKED = "malware_blocked"
    PHISHING_BLOCKED = "phishing_blocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # User and session events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    SESSION_EXPIRED = "session_expired"
    SESSION_CREATED = "session_created"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    
    # Connection and WebSocket events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"
    CONNECTION_ERROR = "connection_error"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_DELETED = "subscription_deleted"
    PING = "ping"
    PONG = "pong"
    HEARTBEAT = "heartbeat"
    
    # System administration events
    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    BACKUP_FAILED = "backup_failed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    SERVICE_RESTARTED = "service_restarted"
    
    # Bulk operations and progress events
    BULK_OPERATION_STARTED = "bulk_operation_started"
    BULK_OPERATION_PROGRESS = "bulk_operation_progress"
    BULK_OPERATION_COMPLETED = "bulk_operation_completed"
    BULK_OPERATION_FAILED = "bulk_operation_failed"
    IMPORT_STARTED = "import_started"
    IMPORT_PROGRESS = "import_progress"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"
    EXPORT_STARTED = "export_started"
    EXPORT_PROGRESS = "export_progress"
    EXPORT_COMPLETED = "export_completed"
    EXPORT_FAILED = "export_failed"
    
    # Error and debugging events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    DEBUG_INFO = "debug_info"
    AUDIT_LOG = "audit_log"
    
    # Custom and extensible events
    CUSTOM_EVENT = "custom_event"
    WEBHOOK_TRIGGERED = "webhook_triggered"
    API_CALL_MADE = "api_call_made"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_ACKNOWLEDGED = "notification_acknowledged"
    NOTIFICATION_STATISTICS = "notification_statistics"


class EventPriority(Enum):
    """Event priority levels for message routing and processing"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"  # For immediate delivery, bypasses batching


class EventCategory(Enum):
    """Event categories for filtering and organization"""
    HEALTH = "health"
    DNS = "dns"
    SECURITY = "security"
    USER = "user"
    SYSTEM = "system"
    CONNECTION = "connection"
    BULK_OPERATION = "bulk_operation"
    ERROR = "error"
    AUDIT = "audit"
    CUSTOM = "custom"


class EventSeverity(Enum):
    """Event severity levels for logging and alerting"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class EventMetadata:
    """Event metadata for additional context and routing"""
    source_service: Optional[str] = None
    source_component: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """Comprehensive event data model for the unified WebSocket system"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.CUSTOM_EVENT
    category: EventCategory = EventCategory.CUSTOM
    priority: EventPriority = EventPriority.NORMAL
    severity: EventSeverity = EventSeverity.INFO
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_user_id: Optional[str] = None
    target_user_id: Optional[str] = None
    metadata: EventMetadata = field(default_factory=EventMetadata)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert event to WebSocket message format"""
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category.value,
            "priority": self.priority.value,
            "severity": self.severity.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source_user_id": self.source_user_id,
            "target_user_id": self.target_user_id,
            "metadata": {
                "source_service": self.metadata.source_service,
                "source_component": self.metadata.source_component,
                "correlation_id": self.metadata.correlation_id,
                "trace_id": self.metadata.trace_id,
                "session_id": self.metadata.session_id,
                "request_id": self.metadata.request_id,
                "ip_address": self.metadata.ip_address,
                "user_agent": self.metadata.user_agent,
                "tags": self.metadata.tags,
                "custom_fields": self.metadata.custom_fields
            },
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for persistence"""
        return self.to_websocket_message()
    
    def is_expired(self) -> bool:
        """Check if event has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if event can be retried"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry count"""
        self.retry_count += 1
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the event metadata"""
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)
    
    def add_custom_field(self, key: str, value: Any) -> None:
        """Add a custom field to the event metadata"""
        self.metadata.custom_fields[key] = value
    
    def get_routing_key(self) -> str:
        """Get routing key for event distribution"""
        return f"{self.category.value}.{self.type.value}.{self.priority.value}"


@dataclass
class EventFilter:
    """Event filter for subscription management"""
    event_types: Optional[List[EventType]] = None
    event_categories: Optional[List[EventCategory]] = None
    priorities: Optional[List[EventPriority]] = None
    severities: Optional[List[EventSeverity]] = None
    source_services: Optional[List[str]] = None
    source_components: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    custom_filters: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, event: Event) -> bool:
        """Check if event matches this filter"""
        if self.event_types and event.type not in self.event_types:
            return False
        
        if self.event_categories and event.category not in self.event_categories:
            return False
        
        if self.priorities and event.priority not in self.priorities:
            return False
        
        if self.severities and event.severity not in self.severities:
            return False
        
        if self.source_services and event.metadata.source_service not in self.source_services:
            return False
        
        if self.source_components and event.metadata.source_component not in self.source_components:
            return False
        
        if self.user_ids and event.source_user_id not in self.user_ids:
            return False
        
        if self.tags:
            if not any(tag in event.metadata.tags for tag in self.tags):
                return False
        
        # Check custom filters
        for key, expected_value in self.custom_filters.items():
            if key in event.data:
                if event.data[key] != expected_value:
                    return False
            elif key in event.metadata.custom_fields:
                if event.metadata.custom_fields[key] != expected_value:
                    return False
            else:
                return False
        
        return True


@dataclass
class BatchedMessage:
    """Batched message container for optimized delivery"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    events: List[Event] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    compressed: bool = False
    compression_ratio: Optional[float] = None
    
    def add_event(self, event: Event) -> None:
        """Add an event to the batch"""
        self.events.append(event)
        # Update batch priority to highest priority event
        if event.priority.value == EventPriority.CRITICAL.value or event.priority.value == EventPriority.URGENT.value:
            self.priority = event.priority
        elif event.priority.value == EventPriority.HIGH.value and self.priority.value not in [EventPriority.CRITICAL.value, EventPriority.URGENT.value]:
            self.priority = event.priority
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert batched message to WebSocket format"""
        return {
            "id": self.id,
            "type": "batched_events",
            "batch_size": len(self.events),
            "priority": self.priority.value,
            "compressed": self.compressed,
            "compression_ratio": self.compression_ratio,
            "created_at": self.created_at.isoformat(),
            "events": [event.to_websocket_message() for event in self.events]
        }
    
    def get_size_bytes(self) -> int:
        """Get approximate size of batch in bytes"""
        import json
        return len(json.dumps(self.to_websocket_message()).encode('utf-8'))
    
    def is_full(self, max_size: int = 50, max_bytes: int = 64 * 1024) -> bool:
        """Check if batch is full based on size limits"""
        return len(self.events) >= max_size or self.get_size_bytes() >= max_bytes
    
    def should_send_immediately(self) -> bool:
        """Check if batch should be sent immediately due to priority"""
        return any(event.priority in [EventPriority.CRITICAL, EventPriority.URGENT] for event in self.events)


# Event type categorization for default subscriptions and permissions
EVENT_CATEGORIES_MAP = {
    EventCategory.HEALTH: [
        EventType.HEALTH_UPDATE,
        EventType.HEALTH_ALERT,
        EventType.FORWARDER_STATUS_CHANGE,
        EventType.FORWARDER_HEALTH_CHECK,
        EventType.SYSTEM_STATUS,
        EventType.SYSTEM_METRICS,
        EventType.PERFORMANCE_ALERT,
        EventType.RESOURCE_USAGE,
        EventType.BIND_STATUS_UPDATE,
        EventType.NETWORK_INTERFACE_METRICS,
        EventType.NETWORK_METRICS,
        EventType.DISK_METRICS,
    ],
    EventCategory.DNS: [
        EventType.ZONE_CREATED,
        EventType.ZONE_UPDATED,
        EventType.ZONE_DELETED,
        EventType.ZONE_IMPORTED,
        EventType.ZONE_EXPORTED,
        EventType.RECORD_CREATED,
        EventType.RECORD_UPDATED,
        EventType.RECORD_DELETED,
        EventType.RECORD_BULK_OPERATION,
        EventType.BIND_RELOAD,
        EventType.BIND_CONFIG_CHANGE,
        EventType.CONFIG_CHANGE,
        EventType.CONFIG_BACKUP,
        EventType.CONFIG_RESTORE,
        EventType.DNS_QUERY_LOG,
        EventType.DNS_QUERY_BATCH,
        EventType.DNS_QUERY_STATISTICS,
        EventType.DNS_QUERY_STATS,
        EventType.DNS_QUERY_BLOCKED,
        EventType.DNS_QUERY_ALLOWED,
        EventType.DNS_ANALYTICS_UPDATE,
        EventType.DNS_QUERY_STREAM,
        EventType.DNS_QUERY_REALTIME,
    ],
    EventCategory.SECURITY: [
        EventType.SECURITY_ALERT,
        EventType.SECURITY_THREAT_DETECTED,
        EventType.RPZ_UPDATE,
        EventType.RPZ_RULE_CREATED,
        EventType.RPZ_RULE_UPDATED,
        EventType.RPZ_RULE_DELETED,
        EventType.THREAT_DETECTED,
        EventType.THREAT_FEED_UPDATE,
        EventType.MALWARE_BLOCKED,
        EventType.PHISHING_BLOCKED,
        EventType.SUSPICIOUS_ACTIVITY,
    ],
    EventCategory.USER: [
        EventType.USER_LOGIN,
        EventType.USER_LOGOUT,
        EventType.USER_CREATED,
        EventType.USER_UPDATED,
        EventType.USER_DELETED,
        EventType.SESSION_EXPIRED,
        EventType.SESSION_CREATED,
        EventType.AUTHENTICATION_FAILED,
        EventType.PERMISSION_DENIED,
    ],
    EventCategory.SYSTEM: [
        EventType.BACKUP_STARTED,
        EventType.BACKUP_COMPLETED,
        EventType.BACKUP_FAILED,
        EventType.RESTORE_STARTED,
        EventType.RESTORE_COMPLETED,
        EventType.RESTORE_FAILED,
        EventType.MAINTENANCE_STARTED,
        EventType.MAINTENANCE_COMPLETED,
        EventType.SERVICE_STARTED,
        EventType.SERVICE_STOPPED,
        EventType.SERVICE_RESTARTED,
    ],
    EventCategory.CONNECTION: [
        EventType.CONNECTION_ESTABLISHED,
        EventType.CONNECTION_CLOSED,
        EventType.CONNECTION_ERROR,
        EventType.SUBSCRIPTION_UPDATED,
        EventType.SUBSCRIPTION_CREATED,
        EventType.SUBSCRIPTION_DELETED,
        EventType.PING,
        EventType.PONG,
        EventType.HEARTBEAT,
    ],
    EventCategory.BULK_OPERATION: [
        EventType.BULK_OPERATION_STARTED,
        EventType.BULK_OPERATION_PROGRESS,
        EventType.BULK_OPERATION_COMPLETED,
        EventType.BULK_OPERATION_FAILED,
        EventType.IMPORT_STARTED,
        EventType.IMPORT_PROGRESS,
        EventType.IMPORT_COMPLETED,
        EventType.IMPORT_FAILED,
        EventType.EXPORT_STARTED,
        EventType.EXPORT_PROGRESS,
        EventType.EXPORT_COMPLETED,
        EventType.EXPORT_FAILED,
    ],
    EventCategory.ERROR: [
        EventType.ERROR_OCCURRED,
        EventType.WARNING_ISSUED,
        EventType.DEBUG_INFO,
    ],
    EventCategory.AUDIT: [
        EventType.AUDIT_LOG,
    ],
    EventCategory.CUSTOM: [
        EventType.CUSTOM_EVENT,
        EventType.WEBHOOK_TRIGGERED,
        EventType.API_CALL_MADE,
        EventType.NOTIFICATION_SENT,
        EventType.NOTIFICATION_ACKNOWLEDGED,
        EventType.NOTIFICATION_STATISTICS,
    ],
}

# Admin-only event types
ADMIN_ONLY_EVENTS = {
    EventType.USER_CREATED,
    EventType.USER_UPDATED,
    EventType.USER_DELETED,
    EventType.SESSION_CREATED,
    EventType.AUTHENTICATION_FAILED,
    EventType.PERMISSION_DENIED,
    EventType.SERVICE_STARTED,
    EventType.SERVICE_STOPPED,
    EventType.SERVICE_RESTARTED,
    EventType.MAINTENANCE_STARTED,
    EventType.MAINTENANCE_COMPLETED,
    EventType.DEBUG_INFO,
    EventType.AUDIT_LOG,
}

# Critical events that bypass batching
CRITICAL_EVENTS = {
    EventType.SECURITY_ALERT,
    EventType.SECURITY_THREAT_DETECTED,
    EventType.THREAT_DETECTED,
    EventType.MALWARE_BLOCKED,
    EventType.PHISHING_BLOCKED,
    EventType.SUSPICIOUS_ACTIVITY,
    EventType.HEALTH_ALERT,
    EventType.PERFORMANCE_ALERT,
    EventType.ERROR_OCCURRED,
    EventType.CONNECTION_ERROR,
    EventType.BACKUP_FAILED,
    EventType.RESTORE_FAILED,
    EventType.SERVICE_STOPPED,
}


def get_event_category(event_type: EventType) -> EventCategory:
    """Get the category for a given event type"""
    for category, event_types in EVENT_CATEGORIES_MAP.items():
        if event_type in event_types:
            return category
    return EventCategory.CUSTOM


def is_admin_only_event(event_type: EventType) -> bool:
    """Check if event type is admin-only"""
    return event_type in ADMIN_ONLY_EVENTS


def is_critical_event(event_type: EventType) -> bool:
    """Check if event type is critical and should bypass batching"""
    return event_type in CRITICAL_EVENTS


def create_event(
    event_type: EventType,
    data: Dict[str, Any],
    source_user_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    priority: Optional[EventPriority] = None,
    severity: Optional[EventSeverity] = None,
    metadata: Optional[EventMetadata] = None,
    **kwargs
) -> Event:
    """Factory function to create events with proper defaults"""
    category = get_event_category(event_type)
    
    # Set default priority based on event type
    if priority is None:
        if is_critical_event(event_type):
            priority = EventPriority.CRITICAL
        else:
            priority = EventPriority.NORMAL
    
    # Set default severity based on event type
    if severity is None:
        if event_type in {EventType.ERROR_OCCURRED, EventType.BACKUP_FAILED, EventType.RESTORE_FAILED}:
            severity = EventSeverity.ERROR
        elif event_type in {EventType.WARNING_ISSUED, EventType.PERFORMANCE_ALERT}:
            severity = EventSeverity.WARNING
        elif is_critical_event(event_type):
            severity = EventSeverity.CRITICAL
        else:
            severity = EventSeverity.INFO
    
    if metadata is None:
        metadata = EventMetadata()
    
    return Event(
        type=event_type,
        category=category,
        priority=priority,
        severity=severity,
        data=data,
        source_user_id=source_user_id,
        target_user_id=target_user_id,
        metadata=metadata,
        **kwargs
    )