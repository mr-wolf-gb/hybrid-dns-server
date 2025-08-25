"""
Event Filter System - Permission-based and data sensitivity filtering
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import json

from ..core.logging_config import get_logger
from .models import WSUser, Event, EventType, EventPriority

logger = get_logger(__name__)


class FilterResult(Enum):
    """Filter result types"""
    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


@dataclass
class FilterDecision:
    """Result of event filtering"""
    result: FilterResult
    filtered_data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitState:
    """Rate limiting state for a user"""
    user_id: str
    event_type: EventType
    count: int = 0
    window_start: datetime = field(default_factory=datetime.utcnow)
    last_event: datetime = field(default_factory=datetime.utcnow)
    blocked_until: Optional[datetime] = None


class EventFilter(ABC):
    """
    Base class for event filtering
    """
    
    def __init__(self, name: str, priority: int = 100):
        self.name = name
        self.priority = priority  # Lower number = higher priority
        self.is_enabled = True
        self.stats = {
            "total_processed": 0,
            "allowed": 0,
            "denied": 0,
            "modified": 0,
            "errors": 0
        }
    
    @abstractmethod
    async def filter_event(self, event: Event, user: WSUser) -> FilterDecision:
        """Filter an event for a specific user"""
        pass
    
    async def should_send_to_user(self, event: Event, user: WSUser) -> bool:
        """Check if event should be sent to user (convenience method)"""
        try:
            decision = await self.filter_event(event, user)
            self.stats["total_processed"] += 1
            
            if decision.result == FilterResult.ALLOW:
                self.stats["allowed"] += 1
                return True
            elif decision.result == FilterResult.DENY:
                self.stats["denied"] += 1
                return False
            else:  # MODIFY
                self.stats["modified"] += 1
                return True
        except Exception as e:
            logger.error(f"Error in filter {self.name}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def filter_event_data(self, event: Event, user: WSUser) -> Dict[str, Any]:
        """Filter event data for a specific user"""
        try:
            decision = await self.filter_event(event, user)
            
            if decision.result == FilterResult.DENY:
                return {}
            elif decision.result == FilterResult.MODIFY and decision.filtered_data:
                return decision.filtered_data
            else:
                return event.data
        except Exception as e:
            logger.error(f"Error filtering data in {self.name}: {e}")
            return event.data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            "name": self.name,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "stats": self.stats.copy()
        }


class PermissionEventFilter(EventFilter):
    """
    Filters events based on user permissions
    """
    
    def __init__(self):
        super().__init__("PermissionFilter", priority=10)  # High priority
        
        # Define admin-only events
        self.admin_only_events = {
            EventType.USER_LOGIN,
            EventType.USER_LOGOUT,
            EventType.SESSION_EXPIRED
        }
        
        # Define sensitive events that require special permissions
        self.sensitive_events = {
            EventType.SECURITY_ALERT,
            EventType.THREAT_DETECTED,
            EventType.RPZ_UPDATE
        }
    
    async def filter_event(self, event: Event, user: WSUser) -> FilterDecision:
        """Filter based on user permissions"""
        # Check admin-only events
        if event.type in self.admin_only_events and not user.is_admin:
            return FilterDecision(
                result=FilterResult.DENY,
                reason=f"Admin permission required for {event.type.value}"
            )
        
        # Check if user has general permission for event type
        if not user.has_permission(event.type):
            return FilterDecision(
                result=FilterResult.DENY,
                reason=f"User lacks permission for {event.type.value}"
            )
        
        # Check sensitive events - may require data filtering
        if event.type in self.sensitive_events and not user.is_admin:
            # Filter sensitive data for non-admin users
            filtered_data = self._filter_sensitive_data(event.data, user)
            if filtered_data != event.data:
                return FilterDecision(
                    result=FilterResult.MODIFY,
                    filtered_data=filtered_data,
                    reason="Sensitive data filtered for non-admin user"
                )
        
        return FilterDecision(result=FilterResult.ALLOW)
    
    def _filter_sensitive_data(self, data: Dict[str, Any], user: WSUser) -> Dict[str, Any]:
        """Filter sensitive data from event"""
        filtered_data = data.copy()
        
        # Remove sensitive fields for non-admin users
        sensitive_fields = {
            "internal_ip", "source_ip", "user_agent", "session_id",
            "api_key", "token", "password", "secret", "private_key"
        }
        
        def remove_sensitive_fields(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: remove_sensitive_fields(v) 
                    for k, v in obj.items() 
                    if k.lower() not in sensitive_fields
                }
            elif isinstance(obj, list):
                return [remove_sensitive_fields(item) for item in obj]
            else:
                return obj
        
        return remove_sensitive_fields(filtered_data)


class DataSensitivityFilter(EventFilter):
    """
    Filters sensitive data from events based on user roles
    """
    
    def __init__(self):
        super().__init__("DataSensitivityFilter", priority=20)
        
        # Define data sensitivity levels
        self.sensitivity_rules = {
            "high": {
                "fields": ["password", "api_key", "secret", "private_key", "token"],
                "patterns": [r".*password.*", r".*secret.*", r".*key.*", r".*token.*"],
                "admin_only": True
            },
            "medium": {
                "fields": ["email", "phone", "address", "ssn", "credit_card"],
                "patterns": [r".*email.*", r".*phone.*", r".*address.*"],
                "admin_only": False
            },
            "low": {
                "fields": ["internal_ip", "user_agent", "session_id"],
                "patterns": [r".*_ip$", r".*session.*"],
                "admin_only": False
            }
        }
    
    async def filter_event(self, event: Event, user: WSUser) -> FilterDecision:
        """Filter sensitive data based on user role"""
        if user.is_admin:
            # Admin users see all data
            return FilterDecision(result=FilterResult.ALLOW)
        
        filtered_data = self._apply_sensitivity_filtering(event.data, user)
        
        if filtered_data != event.data:
            return FilterDecision(
                result=FilterResult.MODIFY,
                filtered_data=filtered_data,
                reason="Sensitive data filtered based on user role"
            )
        
        return FilterDecision(result=FilterResult.ALLOW)
    
    def _apply_sensitivity_filtering(self, data: Dict[str, Any], user: WSUser) -> Dict[str, Any]:
        """Apply sensitivity filtering to data"""
        filtered_data = json.loads(json.dumps(data))  # Deep copy
        
        def filter_object(obj: Any, path: str = "") -> Any:
            if isinstance(obj, dict):
                filtered_obj = {}
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if field should be filtered
                    if self._should_filter_field(key, current_path, user):
                        filtered_obj[key] = "[FILTERED]"
                    else:
                        filtered_obj[key] = filter_object(value, current_path)
                
                return filtered_obj
            elif isinstance(obj, list):
                return [filter_object(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            elif isinstance(obj, str):
                return self._filter_string_value(obj, path, user)
            else:
                return obj
        
        return filter_object(filtered_data)
    
    def _should_filter_field(self, field_name: str, field_path: str, user: WSUser) -> bool:
        """Check if field should be filtered"""
        field_lower = field_name.lower()
        path_lower = field_path.lower()
        
        for level, rules in self.sensitivity_rules.items():
            # Check if admin-only and user is not admin
            if rules["admin_only"] and not user.is_admin:
                # Check exact field matches
                if field_lower in [f.lower() for f in rules["fields"]]:
                    return True
                
                # Check pattern matches
                for pattern in rules["patterns"]:
                    if re.match(pattern, field_lower) or re.match(pattern, path_lower):
                        return True
        
        return False
    
    def _filter_string_value(self, value: str, path: str, user: WSUser) -> str:
        """Filter string values that might contain sensitive data"""
        if user.is_admin:
            return value
        
        # Pattern-based filtering for string values
        sensitive_patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),  # Credit card
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]'),  # IP address
        ]
        
        filtered_value = value
        for pattern, replacement in sensitive_patterns:
            filtered_value = re.sub(pattern, replacement, filtered_value)
        
        return filtered_value


class RateLimitFilter(EventFilter):
    """
    Rate limiting filter to prevent event flooding
    """
    
    def __init__(self):
        super().__init__("RateLimitFilter", priority=5)  # Very high priority
        
        # Rate limit states: (user_id, event_type) -> RateLimitState
        self.rate_limits: Dict[Tuple[str, EventType], RateLimitState] = {}
        
        # Rate limit configuration
        self.limits = {
            # Events per minute for different event types
            EventType.HEALTH_UPDATE: {"limit": 10, "window": 60},
            EventType.SYSTEM_STATUS: {"limit": 5, "window": 60},
            EventType.ZONE_CREATED: {"limit": 20, "window": 60},
            EventType.ZONE_UPDATED: {"limit": 50, "window": 60},
            EventType.ZONE_DELETED: {"limit": 10, "window": 60},
            EventType.RECORD_CREATED: {"limit": 100, "window": 60},
            EventType.RECORD_UPDATED: {"limit": 200, "window": 60},
            EventType.RECORD_DELETED: {"limit": 50, "window": 60},
            EventType.SECURITY_ALERT: {"limit": 5, "window": 60},
            EventType.THREAT_DETECTED: {"limit": 10, "window": 60},
            EventType.RPZ_UPDATE: {"limit": 20, "window": 60},
        }
        
        # Default limits for events not specified above
        self.default_limit = {"limit": 30, "window": 60}
        
        # Admin multiplier (admins get higher limits)
        self.admin_multiplier = 5
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the rate limit filter"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Rate limit filter started")
    
    async def stop(self):
        """Stop the rate limit filter"""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rate limit filter stopped")
    
    async def filter_event(self, event: Event, user: WSUser) -> FilterDecision:
        """Apply rate limiting to event"""
        key = (user.username, event.type)
        now = datetime.utcnow()
        
        # Get or create rate limit state
        if key not in self.rate_limits:
            self.rate_limits[key] = RateLimitState(
                user_id=user.username,
                event_type=event.type,
                window_start=now
            )
        
        state = self.rate_limits[key]
        
        # Check if user is currently blocked
        if state.blocked_until and now < state.blocked_until:
            return FilterDecision(
                result=FilterResult.DENY,
                reason=f"Rate limited until {state.blocked_until.isoformat()}"
            )
        
        # Get rate limit configuration
        limit_config = self.limits.get(event.type, self.default_limit)
        limit = limit_config["limit"]
        window = limit_config["window"]
        
        # Apply admin multiplier
        if user.is_admin:
            limit *= self.admin_multiplier
        
        # Check if we need to reset the window
        if (now - state.window_start).total_seconds() >= window:
            state.count = 0
            state.window_start = now
            state.blocked_until = None
        
        # Check rate limit
        if state.count >= limit:
            # Block user for the remaining window time
            remaining_window = window - (now - state.window_start).total_seconds()
            state.blocked_until = now + timedelta(seconds=max(remaining_window, 60))
            
            logger.warning(f"Rate limit exceeded for user {user.username}, event {event.type.value}")
            return FilterDecision(
                result=FilterResult.DENY,
                reason=f"Rate limit exceeded: {limit} events per {window} seconds"
            )
        
        # Update state
        state.count += 1
        state.last_event = now
        
        return FilterDecision(result=FilterResult.ALLOW)
    
    async def _cleanup_loop(self):
        """Background task to clean up old rate limit states"""
        while self._running:
            try:
                now = datetime.utcnow()
                expired_keys = []
                
                for key, state in self.rate_limits.items():
                    # Remove states that haven't been used in the last hour
                    if (now - state.last_event).total_seconds() > 3600:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.rate_limits[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit states")
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limit cleanup: {e}")
                await asyncio.sleep(300)
    
    def get_user_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get rate limit status for a user"""
        user_states = {
            event_type.value: {
                "count": state.count,
                "limit": self.limits.get(event_type, self.default_limit)["limit"],
                "window_start": state.window_start.isoformat(),
                "last_event": state.last_event.isoformat(),
                "blocked_until": state.blocked_until.isoformat() if state.blocked_until else None
            }
            for (uid, event_type), state in self.rate_limits.items()
            if uid == user_id
        }
        
        return {
            "user_id": user_id,
            "rate_limit_states": user_states,
            "total_tracked_events": len(user_states)
        }


class EventFilterChain:
    """
    Chain of event filters that processes events in priority order
    """
    
    def __init__(self):
        self.filters: List[EventFilter] = []
        self.is_enabled = True
        self.stats = {
            "total_processed": 0,
            "allowed": 0,
            "denied": 0,
            "modified": 0,
            "errors": 0
        }
    
    def add_filter(self, event_filter: EventFilter):
        """Add a filter to the chain"""
        self.filters.append(event_filter)
        # Sort by priority (lower number = higher priority)
        self.filters.sort(key=lambda f: f.priority)
        logger.info(f"Added filter {event_filter.name} with priority {event_filter.priority}")
    
    def remove_filter(self, filter_name: str) -> bool:
        """Remove a filter from the chain"""
        for i, f in enumerate(self.filters):
            if f.name == filter_name:
                del self.filters[i]
                logger.info(f"Removed filter {filter_name}")
                return True
        return False
    
    async def filter_event(self, event: Event, user: WSUser) -> Tuple[bool, Dict[str, Any]]:
        """
        Process event through filter chain
        Returns: (should_send, filtered_data)
        """
        if not self.is_enabled:
            return True, event.data
        
        self.stats["total_processed"] += 1
        current_data = event.data
        
        try:
            for event_filter in self.filters:
                if not event_filter.is_enabled:
                    continue
                
                # Create event with current data for filtering
                current_event = Event(
                    id=event.id,
                    type=event.type,
                    data=current_data,
                    timestamp=event.timestamp,
                    source_user_id=event.source_user_id,
                    priority=event.priority,
                    metadata=event.metadata
                )
                
                decision = await event_filter.filter_event(current_event, user)
                
                if decision.result == FilterResult.DENY:
                    self.stats["denied"] += 1
                    return False, {}
                elif decision.result == FilterResult.MODIFY and decision.filtered_data:
                    current_data = decision.filtered_data
                    self.stats["modified"] += 1
            
            self.stats["allowed"] += 1
            return True, current_data
            
        except Exception as e:
            logger.error(f"Error in filter chain: {e}")
            self.stats["errors"] += 1
            return False, {}
    
    def get_chain_stats(self) -> Dict[str, Any]:
        """Get statistics for the entire filter chain"""
        filter_stats = [f.get_stats() for f in self.filters]
        
        return {
            "is_enabled": self.is_enabled,
            "total_filters": len(self.filters),
            "chain_stats": self.stats.copy(),
            "filter_stats": filter_stats
        }


# Global filter chain instance
_filter_chain = None


def get_event_filter_chain() -> EventFilterChain:
    """Get the global event filter chain"""
    global _filter_chain
    if _filter_chain is None:
        _filter_chain = EventFilterChain()
        
        # Add default filters
        _filter_chain.add_filter(PermissionEventFilter())
        _filter_chain.add_filter(DataSensitivityFilter())
        _filter_chain.add_filter(RateLimitFilter())
    
    return _filter_chain