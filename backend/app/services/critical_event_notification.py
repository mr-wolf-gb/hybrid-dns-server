"""
Critical event notification system with immediate delivery and escalation
Implements priority-based routing, bypass mechanisms, and escalation for unacknowledged events
"""

import asyncio
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..core.logging_config import get_logger
from ..core.database import get_database_session
from ..websocket.event_types import (
    Event, EventType, EventPriority, EventSeverity, EventCategory,
    create_event, is_critical_event, CRITICAL_EVENTS
)
from ..services.enhanced_event_service import get_enhanced_event_service

logger = get_logger(__name__)


class EscalationLevel(Enum):
    """Escalation levels for critical events"""
    NONE = "none"
    LEVEL_1 = "level_1"  # Immediate notification
    LEVEL_2 = "level_2"  # Repeat notification after 5 minutes
    LEVEL_3 = "level_3"  # Escalate to admin after 15 minutes
    LEVEL_4 = "level_4"  # External notification after 30 minutes


class NotificationChannel(Enum):
    """Notification delivery channels"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"
    SLACK = "slack"


@dataclass
class CriticalEventRule:
    """Rule for handling critical events"""
    id: str
    name: str
    event_types: Set[EventType]
    event_categories: Set[EventCategory]
    severity_levels: Set[EventSeverity]
    priority_levels: Set[EventPriority]
    immediate_delivery: bool = True
    bypass_batching: bool = True
    escalation_enabled: bool = True
    escalation_timeout: int = 300  # seconds (5 minutes)
    max_escalation_level: EscalationLevel = EscalationLevel.LEVEL_3
    notification_channels: Set[NotificationChannel] = field(default_factory=lambda: {NotificationChannel.WEBSOCKET})
    target_users: Optional[Set[str]] = None  # None means all admin users
    custom_filters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def matches_event(self, event: Event) -> bool:
        """Check if this rule matches the given event"""
        if not self.enabled:
            return False
        
        # Check event type
        if self.event_types and event.type not in self.event_types:
            return False
        
        # Check event category
        if self.event_categories and event.category not in self.event_categories:
            return False
        
        # Check severity
        if self.severity_levels and event.severity not in self.severity_levels:
            return False
        
        # Check priority
        if self.priority_levels and event.priority not in self.priority_levels:
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
class CriticalEventNotification:
    """Critical event notification tracking"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: Event = None
    rule: CriticalEventRule = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    first_sent_at: Optional[datetime] = None
    last_sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.NONE
    escalation_count: int = 0
    delivery_attempts: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    channels_attempted: Set[NotificationChannel] = field(default_factory=set)
    channels_successful: Set[NotificationChannel] = field(default_factory=set)
    target_users: Set[str] = field(default_factory=set)
    notified_users: Set[str] = field(default_factory=set)
    error_messages: List[str] = field(default_factory=list)
    
    def is_acknowledged(self) -> bool:
        """Check if notification has been acknowledged"""
        return self.acknowledged_at is not None
    
    def should_escalate(self) -> bool:
        """Check if notification should be escalated"""
        if not self.rule.escalation_enabled or self.is_acknowledged():
            return False
        
        if self.escalation_level >= self.rule.max_escalation_level:
            return False
        
        if not self.first_sent_at:
            return False
        
        time_since_first = (datetime.utcnow() - self.first_sent_at).total_seconds()
        escalation_timeout = self.rule.escalation_timeout * (self.escalation_count + 1)
        
        return time_since_first >= escalation_timeout
    
    def get_next_escalation_level(self) -> EscalationLevel:
        """Get the next escalation level"""
        current_level = self.escalation_level
        
        if current_level == EscalationLevel.NONE:
            return EscalationLevel.LEVEL_1
        elif current_level == EscalationLevel.LEVEL_1:
            return EscalationLevel.LEVEL_2
        elif current_level == EscalationLevel.LEVEL_2:
            return EscalationLevel.LEVEL_3
        elif current_level == EscalationLevel.LEVEL_3:
            return EscalationLevel.LEVEL_4
        else:
            return current_level  # Max level reached


@dataclass
class NotificationStats:
    """Statistics for critical event notifications"""
    total_notifications: int = 0
    acknowledged_notifications: int = 0
    escalated_notifications: int = 0
    failed_notifications: int = 0
    avg_acknowledgment_time: float = 0.0
    notifications_by_type: Dict[str, int] = field(default_factory=dict)
    notifications_by_severity: Dict[str, int] = field(default_factory=dict)
    escalations_by_level: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "total_notifications": self.total_notifications,
            "acknowledged_notifications": self.acknowledged_notifications,
            "escalated_notifications": self.escalated_notifications,
            "failed_notifications": self.failed_notifications,
            "acknowledgment_rate": (self.acknowledged_notifications / max(self.total_notifications, 1)) * 100,
            "avg_acknowledgment_time_seconds": self.avg_acknowledgment_time,
            "notifications_by_type": self.notifications_by_type,
            "notifications_by_severity": self.notifications_by_severity,
            "escalations_by_level": self.escalations_by_level
        }


class CriticalEventNotificationService:
    """Critical event notification service with escalation and priority routing"""
    
    def __init__(self):
        self.event_service = get_enhanced_event_service()
        
        # Notification tracking
        self.active_notifications: Dict[str, CriticalEventNotification] = {}
        self.notification_history = deque(maxlen=10000)
        
        # Rules and configuration
        self.rules: Dict[str, CriticalEventRule] = {}
        self.default_admin_users: Set[str] = set()
        self.notification_channels: Dict[NotificationChannel, Callable] = {}
        
        # Background tasks
        self._running = False
        self._escalation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = NotificationStats()
        
        # Event handlers
        self.acknowledgment_handlers: List[Callable] = []
        self.escalation_handlers: List[Callable] = []
        
        # Setup default rules
        self._setup_default_rules()
        
        # Setup default notification channels
        self._setup_default_channels()
    
    def _setup_default_rules(self):
        """Setup default critical event rules"""
        # Security alerts rule
        security_rule = CriticalEventRule(
            id="security_alerts",
            name="Security Alerts",
            event_types={
                EventType.SECURITY_ALERT,
                EventType.SECURITY_THREAT_DETECTED,
                EventType.THREAT_DETECTED,
                EventType.MALWARE_BLOCKED,
                EventType.PHISHING_BLOCKED,
                EventType.SUSPICIOUS_ACTIVITY
            },
            event_categories={EventCategory.SECURITY},
            severity_levels={EventSeverity.WARNING, EventSeverity.ERROR, EventSeverity.CRITICAL},
            priority_levels={EventPriority.HIGH, EventPriority.CRITICAL, EventPriority.URGENT},
            escalation_timeout=300,  # 5 minutes
            max_escalation_level=EscalationLevel.LEVEL_3
        )
        self.rules[security_rule.id] = security_rule
        
        # System health alerts rule
        health_rule = CriticalEventRule(
            id="health_alerts",
            name="System Health Alerts",
            event_types={
                EventType.HEALTH_ALERT,
                EventType.PERFORMANCE_ALERT,
                EventType.SERVICE_STOPPED
            },
            event_categories={EventCategory.HEALTH, EventCategory.SYSTEM},
            severity_levels={EventSeverity.WARNING, EventSeverity.ERROR, EventSeverity.CRITICAL},
            priority_levels={EventPriority.HIGH, EventPriority.CRITICAL, EventPriority.URGENT},
            escalation_timeout=600,  # 10 minutes
            max_escalation_level=EscalationLevel.LEVEL_2
        )
        self.rules[health_rule.id] = health_rule
        
        # Error events rule
        error_rule = CriticalEventRule(
            id="error_events",
            name="Error Events",
            event_types={
                EventType.ERROR_OCCURRED,
                EventType.CONNECTION_ERROR,
                EventType.BACKUP_FAILED,
                EventType.RESTORE_FAILED
            },
            event_categories={EventCategory.ERROR, EventCategory.SYSTEM},
            severity_levels={EventSeverity.ERROR, EventSeverity.CRITICAL},
            priority_levels={EventPriority.HIGH, EventPriority.CRITICAL, EventPriority.URGENT},
            escalation_timeout=900,  # 15 minutes
            max_escalation_level=EscalationLevel.LEVEL_2
        )
        self.rules[error_rule.id] = error_rule
    
    def _setup_default_channels(self):
        """Setup default notification channels"""
        # WebSocket channel (always available)
        self.notification_channels[NotificationChannel.WEBSOCKET] = self._send_websocket_notification
        
        # Other channels can be added as needed
        # self.notification_channels[NotificationChannel.EMAIL] = self._send_email_notification
        # self.notification_channels[NotificationChannel.WEBHOOK] = self._send_webhook_notification
    
    async def start(self):
        """Start the critical event notification service"""
        if self._running:
            return
        
        self._running = True
        
        # Register event processor for critical events
        for event_type in CRITICAL_EVENTS:
            self.event_service.register_event_processor(event_type, self._process_critical_event)
        
        # Start background tasks
        self._escalation_task = asyncio.create_task(self._escalation_monitor())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_notifications())
        self._stats_task = asyncio.create_task(self._update_statistics())
        
        logger.info("Critical event notification service started")
    
    async def stop(self):
        """Stop the critical event notification service"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        for task in [self._escalation_task, self._cleanup_task, self._stats_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Critical event notification service stopped")
    
    async def _process_critical_event(self, event: Event):
        """Process a critical event and create notifications"""
        try:
            # Find matching rules
            matching_rules = []
            for rule in self.rules.values():
                if rule.matches_event(event):
                    matching_rules.append(rule)
            
            if not matching_rules:
                # No rules match, but it's a critical event type
                # Create a default notification
                default_rule = CriticalEventRule(
                    id="default_critical",
                    name="Default Critical Event",
                    event_types={event.type},
                    event_categories={event.category},
                    severity_levels={event.severity},
                    priority_levels={event.priority}
                )
                matching_rules = [default_rule]
            
            # Create notifications for each matching rule
            for rule in matching_rules:
                await self._create_notification(event, rule)
                
        except Exception as e:
            logger.error(f"Error processing critical event {event.id}: {e}")
    
    async def _create_notification(self, event: Event, rule: CriticalEventRule):
        """Create a critical event notification"""
        try:
            # Determine target users
            target_users = rule.target_users or self.default_admin_users
            if not target_users:
                # If no specific users, broadcast to all admin connections
                target_users = {"*"}  # Special marker for broadcast
            
            # Create notification
            notification = CriticalEventNotification(
                event=event,
                rule=rule,
                target_users=target_users
            )
            
            # Store notification
            self.active_notifications[notification.id] = notification
            
            # Send immediate notification
            await self._send_notification(notification)
            
            # Update statistics
            self.stats.total_notifications += 1
            self.stats.notifications_by_type[event.type.value] = \
                self.stats.notifications_by_type.get(event.type.value, 0) + 1
            self.stats.notifications_by_severity[event.severity.value] = \
                self.stats.notifications_by_severity.get(event.severity.value, 0) + 1
            
            logger.info(f"Created critical notification {notification.id} for event {event.id}")
            
        except Exception as e:
            logger.error(f"Error creating notification for event {event.id}: {e}")
    
    async def _send_notification(self, notification: CriticalEventNotification):
        """Send a critical event notification"""
        try:
            notification.delivery_attempts += 1
            
            if not notification.first_sent_at:
                notification.first_sent_at = datetime.utcnow()
            
            notification.last_sent_at = datetime.utcnow()
            
            # Send via configured channels
            successful_channels = 0
            
            for channel in notification.rule.notification_channels:
                notification.channels_attempted.add(channel)
                
                try:
                    if channel in self.notification_channels:
                        await self.notification_channels[channel](notification)
                        notification.channels_successful.add(channel)
                        successful_channels += 1
                    else:
                        logger.warning(f"Notification channel {channel} not configured")
                        
                except Exception as e:
                    error_msg = f"Failed to send via {channel}: {e}"
                    notification.error_messages.append(error_msg)
                    logger.error(error_msg)
            
            if successful_channels > 0:
                notification.successful_deliveries += 1
            else:
                notification.failed_deliveries += 1
                self.stats.failed_notifications += 1
            
            # Emit notification sent event
            await self.event_service.emit_event(
                event_type=EventType.NOTIFICATION_SENT,
                data={
                    "notification_id": notification.id,
                    "event_id": notification.event.id,
                    "event_type": notification.event.type.value,
                    "rule_id": notification.rule.id,
                    "escalation_level": notification.escalation_level.value,
                    "channels_attempted": [c.value for c in notification.channels_attempted],
                    "channels_successful": [c.value for c in notification.channels_successful],
                    "target_users": list(notification.target_users),
                    "delivery_attempts": notification.delivery_attempts
                },
                priority=EventPriority.NORMAL,
                severity=EventSeverity.INFO
            )
            
        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            notification.error_messages.append(str(e))
    
    async def _send_websocket_notification(self, notification: CriticalEventNotification):
        """Send notification via WebSocket"""
        message_data = {
            "notification_id": notification.id,
            "event": notification.event.to_websocket_message(),
            "rule": {
                "id": notification.rule.id,
                "name": notification.rule.name
            },
            "escalation_level": notification.escalation_level.value,
            "created_at": notification.created_at.isoformat(),
            "delivery_attempts": notification.delivery_attempts,
            "requires_acknowledgment": notification.rule.escalation_enabled
        }
        
        # Create critical notification event
        critical_event = create_event(
            event_type=EventType.SECURITY_ALERT if notification.event.category == EventCategory.SECURITY else EventType.HEALTH_ALERT,
            data=message_data,
            priority=EventPriority.URGENT,  # Force immediate delivery
            severity=EventSeverity.CRITICAL
        )
        
        # Send to specific users or broadcast
        if "*" in notification.target_users:
            # Broadcast to all admin users
            await self.event_service._broadcast_immediate(critical_event)
        else:
            # Send to specific users
            for user_id in notification.target_users:
                critical_event.target_user_id = user_id
                await self.event_service._broadcast_immediate(critical_event)
                notification.notified_users.add(user_id)
    
    async def _escalation_monitor(self):
        """Monitor notifications for escalation"""
        while self._running:
            try:
                current_time = datetime.utcnow()
                notifications_to_escalate = []
                
                # Check for notifications that need escalation
                for notification in list(self.active_notifications.values()):
                    if notification.should_escalate():
                        notifications_to_escalate.append(notification)
                
                # Process escalations
                for notification in notifications_to_escalate:
                    await self._escalate_notification(notification)
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
                await asyncio.sleep(60)
    
    async def _escalate_notification(self, notification: CriticalEventNotification):
        """Escalate a notification to the next level"""
        try:
            old_level = notification.escalation_level
            notification.escalation_level = notification.get_next_escalation_level()
            notification.escalation_count += 1
            
            # Update statistics
            self.stats.escalated_notifications += 1
            self.stats.escalations_by_level[notification.escalation_level.value] = \
                self.stats.escalations_by_level.get(notification.escalation_level.value, 0) + 1
            
            # Send escalated notification
            await self._send_notification(notification)
            
            # Call escalation handlers
            for handler in self.escalation_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(notification, old_level, notification.escalation_level)
                    else:
                        handler(notification, old_level, notification.escalation_level)
                except Exception as e:
                    logger.error(f"Error in escalation handler: {e}")
            
            logger.warning(f"Escalated notification {notification.id} from {old_level.value} to {notification.escalation_level.value}")
            
        except Exception as e:
            logger.error(f"Error escalating notification {notification.id}: {e}")
    
    async def acknowledge_notification(self, notification_id: str, user_id: str) -> bool:
        """Acknowledge a critical event notification"""
        try:
            if notification_id not in self.active_notifications:
                return False
            
            notification = self.active_notifications[notification_id]
            
            if notification.is_acknowledged():
                return True  # Already acknowledged
            
            # Mark as acknowledged
            notification.acknowledged_at = datetime.utcnow()
            notification.acknowledged_by = user_id
            
            # Update statistics
            self.stats.acknowledged_notifications += 1
            
            # Calculate acknowledgment time
            if notification.first_sent_at:
                ack_time = (notification.acknowledged_at - notification.first_sent_at).total_seconds()
                # Update running average
                total_acks = self.stats.acknowledged_notifications
                self.stats.avg_acknowledgment_time = (
                    (self.stats.avg_acknowledgment_time * (total_acks - 1) + ack_time) / total_acks
                )
            
            # Call acknowledgment handlers
            for handler in self.acknowledgment_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(notification, user_id)
                    else:
                        handler(notification, user_id)
                except Exception as e:
                    logger.error(f"Error in acknowledgment handler: {e}")
            
            # Emit acknowledgment event
            await self.event_service.emit_event(
                event_type=EventType.NOTIFICATION_ACKNOWLEDGED,
                data={
                    "notification_id": notification_id,
                    "event_id": notification.event.id,
                    "acknowledged_by": user_id,
                    "acknowledged_at": notification.acknowledged_at.isoformat(),
                    "escalation_level": notification.escalation_level.value,
                    "acknowledgment_time_seconds": ack_time if notification.first_sent_at else 0
                },
                source_user_id=user_id,
                priority=EventPriority.NORMAL,
                severity=EventSeverity.INFO
            )
            
            logger.info(f"Notification {notification_id} acknowledged by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging notification {notification_id}: {e}")
            return False
    
    async def _cleanup_old_notifications(self):
        """Clean up old acknowledged notifications"""
        while self._running:
            try:
                # Clean up every hour
                await asyncio.sleep(3600)
                
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=24)  # Keep for 24 hours
                
                # Move old notifications to history
                notifications_to_remove = []
                
                for notification_id, notification in self.active_notifications.items():
                    # Remove if acknowledged and older than cutoff
                    if (notification.is_acknowledged() and 
                        notification.acknowledged_at < cutoff_time):
                        notifications_to_remove.append(notification_id)
                        self.notification_history.append(notification)
                    
                    # Also remove very old unacknowledged notifications (7 days)
                    elif notification.created_at < current_time - timedelta(days=7):
                        notifications_to_remove.append(notification_id)
                        self.notification_history.append(notification)
                
                # Remove from active notifications
                for notification_id in notifications_to_remove:
                    del self.active_notifications[notification_id]
                
                if notifications_to_remove:
                    logger.info(f"Cleaned up {len(notifications_to_remove)} old notifications")
                
            except Exception as e:
                logger.error(f"Error in notification cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _update_statistics(self):
        """Update and broadcast notification statistics"""
        while self._running:
            try:
                # Update statistics every 5 minutes
                await asyncio.sleep(300)
                
                # Broadcast statistics
                await self.event_service.emit_event(
                    event_type=EventType.NOTIFICATION_STATISTICS,
                    data=self.stats.to_dict(),
                    priority=EventPriority.LOW,
                    severity=EventSeverity.INFO
                )
                
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)
    
    def add_rule(self, rule: CriticalEventRule):
        """Add a critical event rule"""
        self.rules[rule.id] = rule
        logger.info(f"Added critical event rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a critical event rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed critical event rule: {rule_id}")
            return True
        return False
    
    def update_rule(self, rule_id: str, **updates) -> bool:
        """Update a critical event rule"""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        logger.info(f"Updated critical event rule: {rule_id}")
        return True
    
    def get_active_notifications(self) -> List[Dict[str, Any]]:
        """Get all active notifications"""
        return [
            {
                "id": notification.id,
                "event_id": notification.event.id,
                "event_type": notification.event.type.value,
                "severity": notification.event.severity.value,
                "rule_id": notification.rule.id,
                "rule_name": notification.rule.name,
                "created_at": notification.created_at.isoformat(),
                "escalation_level": notification.escalation_level.value,
                "acknowledged": notification.is_acknowledged(),
                "acknowledged_by": notification.acknowledged_by,
                "delivery_attempts": notification.delivery_attempts,
                "target_users": list(notification.target_users),
                "notified_users": list(notification.notified_users)
            }
            for notification in self.active_notifications.values()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return self.stats.to_dict()
    
    def add_acknowledgment_handler(self, handler: Callable):
        """Add an acknowledgment event handler"""
        self.acknowledgment_handlers.append(handler)
    
    def add_escalation_handler(self, handler: Callable):
        """Add an escalation event handler"""
        self.escalation_handlers.append(handler)
    
    def set_default_admin_users(self, user_ids: Set[str]):
        """Set default admin users for notifications"""
        self.default_admin_users = user_ids
        logger.info(f"Set default admin users: {len(user_ids)} users")
    
    def add_notification_channel(self, channel: NotificationChannel, handler: Callable):
        """Add a notification channel handler"""
        self.notification_channels[channel] = handler
        logger.info(f"Added notification channel: {channel.value}")


# Add new event types for critical notifications
CRITICAL_NOTIFICATION_EVENTS = [
    "NOTIFICATION_SENT",
    "NOTIFICATION_ACKNOWLEDGED", 
    "NOTIFICATION_STATISTICS"
]


# Global service instance
_critical_notification_service: Optional[CriticalEventNotificationService] = None


def get_critical_notification_service() -> CriticalEventNotificationService:
    """Get the global critical event notification service instance"""
    global _critical_notification_service
    if _critical_notification_service is None:
        _critical_notification_service = CriticalEventNotificationService()
    return _critical_notification_service


async def initialize_critical_notification_service() -> CriticalEventNotificationService:
    """Initialize and start the critical event notification service"""
    service = get_critical_notification_service()
    await service.start()
    return service


async def shutdown_critical_notification_service():
    """Shutdown the critical event notification service"""
    global _critical_notification_service
    if _critical_notification_service:
        await _critical_notification_service.stop()
        _critical_notification_service = None