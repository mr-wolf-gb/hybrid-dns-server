"""
Event models for event broadcasting, persistence, and replay functionality
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

from ..core.database import Base


class Event(Base):
    """
    Event model for storing all system events for persistence and replay
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)  # health, dns, security, system, user
    event_source = Column(String(100), nullable=False)  # service or component that generated the event
    event_data = Column(JSON, nullable=False)
    user_id = Column(String(100), nullable=True, index=True)  # User who triggered the event (if applicable)
    session_id = Column(String(100), nullable=True, index=True)  # Session that triggered the event
    severity = Column(String(20), nullable=False, default="info")  # debug, info, warning, error, critical
    tags = Column(JSON, nullable=True)  # Additional tags for filtering
    event_metadata = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    is_processed = Column(Boolean, default=False, index=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    subscriptions = relationship("EventSubscription", back_populates="event", cascade="all, delete-orphan")
    deliveries = relationship("EventDelivery", back_populates="event", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_events_type_created', 'event_type', 'created_at'),
        Index('idx_events_category_created', 'event_category', 'created_at'),
        Index('idx_events_user_created', 'user_id', 'created_at'),
        Index('idx_events_severity_created', 'severity', 'created_at'),
        Index('idx_events_processed', 'is_processed', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_category": self.event_category,
            "event_source": self.event_source,
            "event_data": self.event_data,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "severity": self.severity,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "is_processed": self.is_processed,
            "retry_count": self.retry_count
        }


class EventSubscription(Base):
    """
    Event subscription model for managing user/connection subscriptions to specific events
    """
    __tablename__ = "event_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    connection_id = Column(String(100), nullable=True, index=True)  # WebSocket connection ID
    event_type = Column(String(100), nullable=True, index=True)  # Specific event type (null = all)
    event_category = Column(String(50), nullable=True, index=True)  # Event category filter
    event_source = Column(String(100), nullable=True, index=True)  # Event source filter
    severity_filter = Column(JSON, nullable=True)  # Array of severity levels to include
    tag_filters = Column(JSON, nullable=True)  # Tag-based filters
    user_filters = Column(JSON, nullable=True)  # User-based filters
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)  # Optional expiration
    
    # Foreign key to events (for specific event subscriptions)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    event = relationship("Event", back_populates="subscriptions")
    
    # Relationships
    deliveries = relationship("EventDelivery", back_populates="subscription", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscriptions_user_active', 'user_id', 'is_active'),
        Index('idx_subscriptions_connection_active', 'connection_id', 'is_active'),
        Index('idx_subscriptions_type_active', 'event_type', 'is_active'),
        Index('idx_subscriptions_expires', 'expires_at'),
    )
    
    def matches_event(self, event: Event) -> bool:
        """Check if this subscription matches the given event"""
        # Check if subscription is active and not expired
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        # Check event type filter
        if self.event_type and self.event_type != event.event_type:
            return False
        
        # Check event category filter
        if self.event_category and self.event_category != event.event_category:
            return False
        
        # Check event source filter
        if self.event_source and self.event_source != event.event_source:
            return False
        
        # Check severity filter
        if self.severity_filter and event.severity not in self.severity_filter:
            return False
        
        # Check tag filters
        if self.tag_filters and event.tags:
            for tag_filter in self.tag_filters:
                if tag_filter not in event.tags:
                    return False
        
        # Check user filters
        if self.user_filters and event.user_id:
            if event.user_id not in self.user_filters:
                return False
        
        return True


class EventDelivery(Base):
    """
    Event delivery tracking for reliable message delivery and replay functionality
    """
    __tablename__ = "event_deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("event_subscriptions.id"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    connection_id = Column(String(100), nullable=True, index=True)
    delivery_method = Column(String(50), nullable=False, default="websocket")  # websocket, webhook, email, etc.
    delivery_status = Column(String(20), nullable=False, default="pending", index=True)  # pending, delivered, failed, retrying
    delivery_attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_after = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    event = relationship("Event", back_populates="deliveries")
    subscription = relationship("EventSubscription", back_populates="deliveries")
    
    # Indexes
    __table_args__ = (
        Index('idx_deliveries_status_created', 'delivery_status', 'created_at'),
        Index('idx_deliveries_user_status', 'user_id', 'delivery_status'),
        Index('idx_deliveries_retry', 'retry_after', 'delivery_status'),
        Index('idx_deliveries_event_user', 'event_id', 'user_id'),
    )


class EventFilter(Base):
    """
    Reusable event filters for complex event routing and subscription management
    """
    __tablename__ = "event_filters"
    
    id = Column(Integer, primary_key=True, index=True)
    filter_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    filter_config = Column(JSON, nullable=False)  # Complex filter configuration
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def matches_event(self, event: Event) -> bool:
        """Check if this filter matches the given event"""
        if not self.is_active or not self.filter_config:
            return False
        
        config = self.filter_config
        
        # Check event types
        if "event_types" in config:
            if event.event_type not in config["event_types"]:
                return False
        
        # Check event categories
        if "event_categories" in config:
            if event.event_category not in config["event_categories"]:
                return False
        
        # Check event sources
        if "event_sources" in config:
            if event.event_source not in config["event_sources"]:
                return False
        
        # Check severity levels
        if "severity_levels" in config:
            if event.severity not in config["severity_levels"]:
                return False
        
        # Check user filters
        if "user_ids" in config:
            if event.user_id not in config["user_ids"]:
                return False
        
        # Check tag filters (all tags must match)
        if "required_tags" in config and event.tags:
            for required_tag in config["required_tags"]:
                if required_tag not in event.tags:
                    return False
        
        # Check excluded tags (none should match)
        if "excluded_tags" in config and event.tags:
            for excluded_tag in config["excluded_tags"]:
                if excluded_tag in event.tags:
                    return False
        
        # Check time-based filters
        if "time_range" in config:
            time_range = config["time_range"]
            if "start_time" in time_range:
                start_time = datetime.fromisoformat(time_range["start_time"])
                if event.created_at < start_time:
                    return False
            if "end_time" in time_range:
                end_time = datetime.fromisoformat(time_range["end_time"])
                if event.created_at > end_time:
                    return False
        
        # Check custom data filters
        if "data_filters" in config and event.event_data:
            for data_filter in config["data_filters"]:
                field_path = data_filter.get("field")
                operator = data_filter.get("operator", "equals")
                value = data_filter.get("value")
                
                if not self._check_data_filter(event.event_data, field_path, operator, value):
                    return False
        
        return True
    
    def _check_data_filter(self, data: Dict[str, Any], field_path: str, operator: str, value: Any) -> bool:
        """Check a data filter against event data"""
        try:
            # Navigate to the field using dot notation
            current_data = data
            for field in field_path.split('.'):
                if isinstance(current_data, dict) and field in current_data:
                    current_data = current_data[field]
                else:
                    return False
            
            # Apply operator
            if operator == "equals":
                return current_data == value
            elif operator == "not_equals":
                return current_data != value
            elif operator == "contains":
                return value in str(current_data)
            elif operator == "not_contains":
                return value not in str(current_data)
            elif operator == "greater_than":
                return float(current_data) > float(value)
            elif operator == "less_than":
                return float(current_data) < float(value)
            elif operator == "in":
                return current_data in value if isinstance(value, list) else False
            elif operator == "not_in":
                return current_data not in value if isinstance(value, list) else True
            else:
                return False
        except (KeyError, ValueError, TypeError):
            return False


class EventReplay(Base):
    """
    Event replay sessions for replaying historical events
    """
    __tablename__ = "event_replays"
    
    id = Column(Integer, primary_key=True, index=True)
    replay_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=False, index=True)
    filter_config = Column(JSON, nullable=False)  # Filter configuration for events to replay
    replay_speed = Column(Integer, default=1)  # Speed multiplier (1 = real-time, 2 = 2x speed, etc.)
    start_time = Column(DateTime, nullable=False)  # Start time for event range
    end_time = Column(DateTime, nullable=False)  # End time for event range
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    total_events = Column(Integer, default=0)
    processed_events = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_replays_user_status', 'user_id', 'status'),
        Index('idx_replays_status_created', 'status', 'created_at'),
    )