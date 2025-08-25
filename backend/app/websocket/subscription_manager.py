"""
Event Subscription Manager - Dynamic subscription management for WebSocket events
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.logging_config import get_logger
from .models import WSUser, EventType, EventPriority

logger = get_logger(__name__)


class SubscriptionType(Enum):
    """Types of event subscriptions"""
    EVENT_TYPE = "event_type"  # Subscribe to specific event types
    CATEGORY = "category"      # Subscribe to event categories
    USER_BASED = "user_based"  # Subscribe to events from specific users
    PRIORITY = "priority"      # Subscribe to events with specific priority
    PATTERN = "pattern"        # Subscribe to events matching patterns


@dataclass
class EventSubscription:
    """Individual event subscription"""
    id: str
    user_id: str
    subscription_type: SubscriptionType
    filter_criteria: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_event_type(self, event_type: EventType) -> bool:
        """Check if subscription matches event type"""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        if self.subscription_type == SubscriptionType.EVENT_TYPE:
            return event_type in self.filter_criteria.get("event_types", [])
        elif self.subscription_type == SubscriptionType.CATEGORY:
            return self._get_event_category(event_type) in self.filter_criteria.get("categories", [])
        elif self.subscription_type == SubscriptionType.PRIORITY:
            # Priority filtering is handled at event level, not subscription level
            return True
        elif self.subscription_type == SubscriptionType.PATTERN:
            pattern = self.filter_criteria.get("pattern", "")
            return pattern.lower() in event_type.value.lower()
        
        return False
    
    def _get_event_category(self, event_type: EventType) -> str:
        """Get category for event type"""
        health_events = {
            EventType.HEALTH_UPDATE, EventType.HEALTH_ALERT, 
            EventType.FORWARDER_STATUS_CHANGE, EventType.SYSTEM_STATUS
        }
        dns_events = {
            EventType.ZONE_CREATED, EventType.ZONE_UPDATED, EventType.ZONE_DELETED,
            EventType.RECORD_CREATED, EventType.RECORD_UPDATED, EventType.RECORD_DELETED,
            EventType.BIND_RELOAD, EventType.CONFIG_CHANGE
        }
        security_events = {
            EventType.SECURITY_ALERT, EventType.RPZ_UPDATE, EventType.THREAT_DETECTED
        }
        user_events = {
            EventType.USER_LOGIN, EventType.USER_LOGOUT, EventType.SESSION_EXPIRED
        }
        connection_events = {
            EventType.CONNECTION_ESTABLISHED, EventType.SUBSCRIPTION_UPDATED,
            EventType.PING, EventType.PONG
        }
        
        if event_type in health_events:
            return "health"
        elif event_type in dns_events:
            return "dns"
        elif event_type in security_events:
            return "security"
        elif event_type in user_events:
            return "user"
        elif event_type in connection_events:
            return "connection"
        else:
            return "system"


@dataclass
class UserSubscriptionProfile:
    """User's complete subscription profile"""
    user_id: str
    subscriptions: Dict[str, EventSubscription] = field(default_factory=dict)
    default_subscriptions: Set[EventType] = field(default_factory=set)
    subscription_limits: Dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def get_active_subscriptions(self) -> List[EventSubscription]:
        """Get all active subscriptions"""
        now = datetime.utcnow()
        return [
            sub for sub in self.subscriptions.values()
            if sub.is_active and (sub.expires_at is None or sub.expires_at > now)
        ]
    
    def get_subscribed_event_types(self) -> Set[EventType]:
        """Get all event types user is subscribed to"""
        subscribed_types = set(self.default_subscriptions)
        
        for subscription in self.get_active_subscriptions():
            if subscription.subscription_type == SubscriptionType.EVENT_TYPE:
                subscribed_types.update(subscription.filter_criteria.get("event_types", []))
            elif subscription.subscription_type == SubscriptionType.CATEGORY:
                # Add all event types in subscribed categories
                for category in subscription.filter_criteria.get("categories", []):
                    subscribed_types.update(self._get_events_by_category(category))
        
        return subscribed_types
    
    def _get_events_by_category(self, category: str) -> Set[EventType]:
        """Get all event types in a category"""
        category_map = {
            "health": {
                EventType.HEALTH_UPDATE, EventType.HEALTH_ALERT,
                EventType.FORWARDER_STATUS_CHANGE, EventType.SYSTEM_STATUS
            },
            "dns": {
                EventType.ZONE_CREATED, EventType.ZONE_UPDATED, EventType.ZONE_DELETED,
                EventType.RECORD_CREATED, EventType.RECORD_UPDATED, EventType.RECORD_DELETED,
                EventType.BIND_RELOAD, EventType.CONFIG_CHANGE
            },
            "security": {
                EventType.SECURITY_ALERT, EventType.RPZ_UPDATE, EventType.THREAT_DETECTED
            },
            "user": {
                EventType.USER_LOGIN, EventType.USER_LOGOUT, EventType.SESSION_EXPIRED
            },
            "connection": {
                EventType.CONNECTION_ESTABLISHED, EventType.SUBSCRIPTION_UPDATED,
                EventType.PING, EventType.PONG
            }
        }
        return category_map.get(category, set())


class EventSubscriptionManager:
    """
    Manages dynamic event subscriptions for WebSocket users
    """
    
    def __init__(self):
        # User subscription profiles: user_id -> UserSubscriptionProfile
        self.user_profiles: Dict[str, UserSubscriptionProfile] = {}
        
        # Subscription limits
        self.default_limits = {
            "max_subscriptions_per_user": 50,
            "max_pattern_subscriptions": 10,
            "max_category_subscriptions": 20,
            "subscription_ttl_hours": 24
        }
        
        # Admin limits (higher)
        self.admin_limits = {
            "max_subscriptions_per_user": 200,
            "max_pattern_subscriptions": 50,
            "max_category_subscriptions": 100,
            "subscription_ttl_hours": 168  # 1 week
        }
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self.stats = {
            "total_subscriptions": 0,
            "active_subscriptions": 0,
            "subscription_operations": 0,
            "validation_failures": 0,
            "cleanup_operations": 0
        }
    
    async def start(self):
        """Start the subscription manager"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Event subscription manager started")
    
    async def stop(self):
        """Stop the subscription manager"""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event subscription manager stopped")
    
    def get_user_profile(self, user_id: str) -> UserSubscriptionProfile:
        """Get or create user subscription profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserSubscriptionProfile(
                user_id=user_id,
                default_subscriptions=self._get_default_subscriptions_for_user(user_id)
            )
        
        return self.user_profiles[user_id]
    
    def _get_default_subscriptions_for_user(self, user_id: str) -> Set[EventType]:
        """Get default subscriptions based on user role"""
        # This would typically check user permissions from database
        # For now, return basic subscriptions
        return {
            EventType.HEALTH_UPDATE,
            EventType.SYSTEM_STATUS,
            EventType.CONNECTION_ESTABLISHED,
            EventType.SUBSCRIPTION_UPDATED,
            EventType.PING,
            EventType.PONG
        }
    
    async def subscribe_to_events(self, user: WSUser, event_types: List[EventType]) -> Tuple[Set[EventType], List[str]]:
        """
        Subscribe user to specific event types
        Returns: (allowed_events, validation_errors)
        """
        profile = self.get_user_profile(user.username)
        allowed_events = set()
        validation_errors = []
        
        # Validate subscription limits
        limits = self.admin_limits if user.is_admin else self.default_limits
        current_subscriptions = len(profile.get_active_subscriptions())
        
        if current_subscriptions >= limits["max_subscriptions_per_user"]:
            validation_errors.append(f"Maximum subscriptions limit reached: {limits['max_subscriptions_per_user']}")
            self.stats["validation_failures"] += 1
            return allowed_events, validation_errors
        
        # Validate each event type
        for event_type in event_types:
            if not self._validate_event_subscription(user, event_type):
                validation_errors.append(f"Permission denied for event type: {event_type.value}")
                continue
            
            # Check if already subscribed
            if event_type in profile.get_subscribed_event_types():
                validation_errors.append(f"Already subscribed to event type: {event_type.value}")
                continue
            
            # Create subscription
            subscription_id = f"{user.username}_{event_type.value}_{datetime.utcnow().timestamp()}"
            subscription = EventSubscription(
                id=subscription_id,
                user_id=user.username,
                subscription_type=SubscriptionType.EVENT_TYPE,
                filter_criteria={"event_types": [event_type]},
                expires_at=datetime.utcnow() + timedelta(hours=limits["subscription_ttl_hours"])
            )
            
            profile.subscriptions[subscription_id] = subscription
            allowed_events.add(event_type)
        
        if allowed_events:
            profile.last_updated = datetime.utcnow()
            self.stats["subscription_operations"] += 1
            self.stats["total_subscriptions"] += len(allowed_events)
            self._update_active_subscriptions_count()
        
        logger.info(f"User {user.username} subscribed to {len(allowed_events)} events")
        return allowed_events, validation_errors
    
    async def unsubscribe_from_events(self, user: WSUser, event_types: List[EventType]) -> Tuple[Set[EventType], List[str]]:
        """
        Unsubscribe user from specific event types
        Returns: (removed_events, validation_errors)
        """
        profile = self.get_user_profile(user.username)
        removed_events = set()
        validation_errors = []
        
        # Find and remove subscriptions
        subscriptions_to_remove = []
        
        for subscription_id, subscription in profile.subscriptions.items():
            if subscription.subscription_type == SubscriptionType.EVENT_TYPE:
                subscribed_types = set(subscription.filter_criteria.get("event_types", []))
                overlap = subscribed_types.intersection(event_types)
                
                if overlap:
                    # Remove overlapping event types
                    remaining_types = subscribed_types - overlap
                    
                    if remaining_types:
                        # Update subscription with remaining types
                        subscription.filter_criteria["event_types"] = list(remaining_types)
                        subscription.updated_at = datetime.utcnow()
                    else:
                        # Remove entire subscription
                        subscriptions_to_remove.append(subscription_id)
                    
                    removed_events.update(overlap)
        
        # Remove empty subscriptions
        for subscription_id in subscriptions_to_remove:
            del profile.subscriptions[subscription_id]
        
        if removed_events:
            profile.last_updated = datetime.utcnow()
            self.stats["subscription_operations"] += 1
            self._update_active_subscriptions_count()
        
        logger.info(f"User {user.username} unsubscribed from {len(removed_events)} events")
        return removed_events, validation_errors
    
    async def subscribe_to_category(self, user: WSUser, categories: List[str]) -> Tuple[Set[str], List[str]]:
        """
        Subscribe user to event categories
        Returns: (allowed_categories, validation_errors)
        """
        profile = self.get_user_profile(user.username)
        allowed_categories = set()
        validation_errors = []
        
        # Validate subscription limits
        limits = self.admin_limits if user.is_admin else self.default_limits
        current_category_subs = sum(
            1 for sub in profile.get_active_subscriptions()
            if sub.subscription_type == SubscriptionType.CATEGORY
        )
        
        if current_category_subs >= limits["max_category_subscriptions"]:
            validation_errors.append(f"Maximum category subscriptions limit reached: {limits['max_category_subscriptions']}")
            return allowed_categories, validation_errors
        
        # Validate each category
        valid_categories = {"health", "dns", "security", "user", "connection", "system"}
        
        for category in categories:
            if category not in valid_categories:
                validation_errors.append(f"Invalid category: {category}")
                continue
            
            # Check permissions for category
            if not self._validate_category_subscription(user, category):
                validation_errors.append(f"Permission denied for category: {category}")
                continue
            
            # Create subscription
            subscription_id = f"{user.username}_cat_{category}_{datetime.utcnow().timestamp()}"
            subscription = EventSubscription(
                id=subscription_id,
                user_id=user.username,
                subscription_type=SubscriptionType.CATEGORY,
                filter_criteria={"categories": [category]},
                expires_at=datetime.utcnow() + timedelta(hours=limits["subscription_ttl_hours"])
            )
            
            profile.subscriptions[subscription_id] = subscription
            allowed_categories.add(category)
        
        if allowed_categories:
            profile.last_updated = datetime.utcnow()
            self.stats["subscription_operations"] += 1
            self.stats["total_subscriptions"] += len(allowed_categories)
            self._update_active_subscriptions_count()
        
        logger.info(f"User {user.username} subscribed to {len(allowed_categories)} categories")
        return allowed_categories, validation_errors
    
    def _validate_event_subscription(self, user: WSUser, event_type: EventType) -> bool:
        """Validate if user can subscribe to event type"""
        return user.has_permission(event_type)
    
    def _validate_category_subscription(self, user: WSUser, category: str) -> bool:
        """Validate if user can subscribe to category"""
        # Admin users can subscribe to all categories
        if user.is_admin:
            return True
        
        # Regular users cannot subscribe to user category
        if category == "user":
            return False
        
        return True
    
    def get_user_subscriptions(self, user_id: str) -> Dict[str, Any]:
        """Get user's subscription information"""
        profile = self.get_user_profile(user_id)
        active_subscriptions = profile.get_active_subscriptions()
        
        return {
            "user_id": user_id,
            "total_subscriptions": len(profile.subscriptions),
            "active_subscriptions": len(active_subscriptions),
            "default_subscriptions": [event.value for event in profile.default_subscriptions],
            "subscribed_event_types": [event.value for event in profile.get_subscribed_event_types()],
            "subscription_details": [
                {
                    "id": sub.id,
                    "type": sub.subscription_type.value,
                    "criteria": sub.filter_criteria,
                    "created_at": sub.created_at.isoformat(),
                    "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                    "is_active": sub.is_active
                }
                for sub in active_subscriptions
            ],
            "last_updated": profile.last_updated.isoformat()
        }
    
    def is_user_subscribed_to_event(self, user_id: str, event_type: EventType) -> bool:
        """Check if user is subscribed to specific event type"""
        profile = self.get_user_profile(user_id)
        return event_type in profile.get_subscribed_event_types()
    
    def get_subscribed_users_for_event(self, event_type: EventType) -> List[str]:
        """Get list of users subscribed to specific event type"""
        subscribed_users = []
        
        for user_id, profile in self.user_profiles.items():
            if event_type in profile.get_subscribed_event_types():
                subscribed_users.append(user_id)
        
        return subscribed_users
    
    async def cleanup_expired_subscriptions(self) -> int:
        """Clean up expired subscriptions"""
        cleaned_count = 0
        now = datetime.utcnow()
        
        for profile in self.user_profiles.values():
            expired_subscriptions = []
            
            for subscription_id, subscription in profile.subscriptions.items():
                if subscription.expires_at and subscription.expires_at <= now:
                    expired_subscriptions.append(subscription_id)
            
            for subscription_id in expired_subscriptions:
                del profile.subscriptions[subscription_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.stats["cleanup_operations"] += 1
            self._update_active_subscriptions_count()
            logger.info(f"Cleaned up {cleaned_count} expired subscriptions")
        
        return cleaned_count
    
    def _update_active_subscriptions_count(self):
        """Update active subscriptions count in stats"""
        active_count = 0
        for profile in self.user_profiles.values():
            active_count += len(profile.get_active_subscriptions())
        
        self.stats["active_subscriptions"] = active_count
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup"""
        while self._running:
            try:
                await self.cleanup_expired_subscriptions()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in subscription cleanup loop: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get subscription manager statistics"""
        return {
            "total_users": len(self.user_profiles),
            "total_subscriptions": self.stats["total_subscriptions"],
            "active_subscriptions": self.stats["active_subscriptions"],
            "subscription_operations": self.stats["subscription_operations"],
            "validation_failures": self.stats["validation_failures"],
            "cleanup_operations": self.stats["cleanup_operations"],
            "is_running": self._running,
            "default_limits": self.default_limits,
            "admin_limits": self.admin_limits
        }


# Global subscription manager instance
_subscription_manager = None


def get_subscription_manager() -> EventSubscriptionManager:
    """Get the global subscription manager instance"""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = EventSubscriptionManager()
    return _subscription_manager