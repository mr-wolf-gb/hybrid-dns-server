"""
Event Routing and Filtering Logic - Intelligent event routing with permission checking
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.logging_config import get_logger
from .models import WSUser, Event, EventType, EventPriority
from .subscription_manager import get_subscription_manager, EventSubscriptionManager
from .event_filters import get_event_filter_chain, EventFilterChain

logger = get_logger(__name__)


class RoutingDecision(Enum):
    """Event routing decisions"""
    ROUTE = "route"
    SKIP = "skip"
    DEFER = "defer"
    ERROR = "error"


@dataclass
class RoutingResult:
    """Result of event routing"""
    decision: RoutingDecision
    target_users: Set[str] = field(default_factory=set)
    filtered_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # user_id -> filtered_data
    routing_metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class EventRoutingRule:
    """Custom routing rule for events"""
    id: str
    name: str
    event_types: Set[EventType]
    priority: int = 100
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventRouter:
    """
    Intelligent event routing system with subscription management and filtering
    """
    
    def __init__(self):
        self.subscription_manager: EventSubscriptionManager = get_subscription_manager()
        self.filter_chain: EventFilterChain = get_event_filter_chain()
        
        # Custom routing rules
        self.routing_rules: Dict[str, EventRoutingRule] = {}
        
        # Routing statistics
        self.stats = {
            "total_events_processed": 0,
            "events_routed": 0,
            "events_skipped": 0,
            "events_deferred": 0,
            "routing_errors": 0,
            "users_reached": 0,
            "filter_applications": 0,
            "subscription_checks": 0
        }
        
        # Performance tracking
        self.performance_metrics = {
            "avg_routing_time_ms": 0.0,
            "max_routing_time_ms": 0.0,
            "total_routing_time_ms": 0.0,
            "routing_operations": 0
        }
        
        # Event queue for deferred processing
        self.deferred_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._deferred_processor_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the event router"""
        if self._running:
            return
        
        self._running = True
        
        # Start subscription manager
        await self.subscription_manager.start()
        
        # Start rate limit filter if present
        for event_filter in self.filter_chain.filters:
            if hasattr(event_filter, 'start'):
                await event_filter.start()
        
        # Start deferred event processor
        self._deferred_processor_task = asyncio.create_task(self._process_deferred_events())
        
        logger.info("Event router started")
    
    async def stop(self):
        """Stop the event router"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop deferred processor
        if self._deferred_processor_task and not self._deferred_processor_task.done():
            self._deferred_processor_task.cancel()
            try:
                await self._deferred_processor_task
            except asyncio.CancelledError:
                pass
        
        # Stop filters
        for event_filter in self.filter_chain.filters:
            if hasattr(event_filter, 'stop'):
                await event_filter.stop()
        
        # Stop subscription manager
        await self.subscription_manager.stop()
        
        logger.info("Event router stopped")
    
    async def route_event(self, event: Event, available_users: Dict[str, WSUser]) -> RoutingResult:
        """
        Route event to appropriate users with filtering and permission checking
        """
        start_time = datetime.utcnow()
        self.stats["total_events_processed"] += 1
        
        try:
            # Step 1: Apply custom routing rules
            routing_result = await self._apply_routing_rules(event, available_users)
            if routing_result.decision != RoutingDecision.ROUTE:
                return routing_result
            
            # Step 2: Get subscribed users
            subscribed_users = await self._get_subscribed_users(event, available_users)
            if not subscribed_users:
                self.stats["events_skipped"] += 1
                return RoutingResult(
                    decision=RoutingDecision.SKIP,
                    routing_metadata={"reason": "No subscribed users"}
                )
            
            # Step 3: Apply filters and permission checks
            filtered_result = await self._apply_filters_and_permissions(event, subscribed_users)
            
            # Step 4: Update statistics
            self._update_routing_stats(filtered_result, start_time)
            
            return filtered_result
            
        except Exception as e:
            logger.error(f"Error routing event {event.id}: {e}")
            self.stats["routing_errors"] += 1
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                errors=[f"Routing error: {str(e)}"]
            )
    
    async def _apply_routing_rules(self, event: Event, available_users: Dict[str, WSUser]) -> RoutingResult:
        """Apply custom routing rules to event"""
        # Check if event should be deferred based on priority and system load
        if event.priority == EventPriority.LOW and len(available_users) > 100:
            try:
                await self.deferred_queue.put((event, available_users))
                self.stats["events_deferred"] += 1
                return RoutingResult(
                    decision=RoutingDecision.DEFER,
                    routing_metadata={"reason": "Deferred due to system load"}
                )
            except asyncio.QueueFull:
                logger.warning("Deferred queue full, processing event immediately")
        
        # Apply custom routing rules
        for rule in self.routing_rules.values():
            if not rule.is_active:
                continue
            
            if event.type in rule.event_types:
                # Check rule conditions
                if await self._check_rule_conditions(event, rule, available_users):
                    # Apply rule actions
                    return await self._apply_rule_actions(event, rule, available_users)
        
        # Default: proceed with normal routing
        return RoutingResult(decision=RoutingDecision.ROUTE)
    
    async def _get_subscribed_users(self, event: Event, available_users: Dict[str, WSUser]) -> Dict[str, WSUser]:
        """Get users subscribed to the event type"""
        subscribed_users = {}
        self.stats["subscription_checks"] += 1
        
        for user_id, user in available_users.items():
            if self.subscription_manager.is_user_subscribed_to_event(user_id, event.type):
                subscribed_users[user_id] = user
        
        logger.debug(f"Found {len(subscribed_users)} users subscribed to {event.type.value}")
        return subscribed_users
    
    async def _apply_filters_and_permissions(self, event: Event, users: Dict[str, WSUser]) -> RoutingResult:
        """Apply event filters and permission checks to users"""
        target_users = set()
        filtered_data = {}
        errors = []
        
        self.stats["filter_applications"] += len(users)
        
        for user_id, user in users.items():
            try:
                # Apply filter chain
                should_send, user_filtered_data = await self.filter_chain.filter_event(event, user)
                
                if should_send:
                    target_users.add(user_id)
                    filtered_data[user_id] = user_filtered_data
                else:
                    logger.debug(f"Event {event.type.value} filtered out for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error filtering event for user {user_id}: {e}")
                errors.append(f"Filter error for user {user_id}: {str(e)}")
        
        if target_users:
            self.stats["events_routed"] += 1
            self.stats["users_reached"] += len(target_users)
            return RoutingResult(
                decision=RoutingDecision.ROUTE,
                target_users=target_users,
                filtered_data=filtered_data,
                routing_metadata={
                    "original_user_count": len(users),
                    "filtered_user_count": len(target_users),
                    "filter_efficiency": len(target_users) / len(users) if users else 0
                },
                errors=errors
            )
        else:
            self.stats["events_skipped"] += 1
            return RoutingResult(
                decision=RoutingDecision.SKIP,
                routing_metadata={"reason": "All users filtered out"},
                errors=errors
            )
    
    async def _check_rule_conditions(self, event: Event, rule: EventRoutingRule, users: Dict[str, WSUser]) -> bool:
        """Check if routing rule conditions are met"""
        conditions = rule.conditions
        
        # Check event priority condition
        if "min_priority" in conditions:
            min_priority = EventPriority(conditions["min_priority"])
            if event.priority.value < min_priority.value:
                return False
        
        # Check user count condition
        if "min_users" in conditions:
            if len(users) < conditions["min_users"]:
                return False
        
        # Check time-based conditions
        if "time_range" in conditions:
            current_hour = datetime.utcnow().hour
            time_range = conditions["time_range"]
            if not (time_range["start"] <= current_hour <= time_range["end"]):
                return False
        
        # Check event data conditions
        if "data_conditions" in conditions:
            for condition in conditions["data_conditions"]:
                field = condition.get("field")
                operator = condition.get("operator", "equals")
                value = condition.get("value")
                
                if not self._check_data_condition(event.data, field, operator, value):
                    return False
        
        return True
    
    async def _apply_rule_actions(self, event: Event, rule: EventRoutingRule, users: Dict[str, WSUser]) -> RoutingResult:
        """Apply routing rule actions"""
        actions = rule.actions
        
        # Skip action
        if actions.get("skip", False):
            return RoutingResult(
                decision=RoutingDecision.SKIP,
                routing_metadata={"reason": f"Skipped by rule {rule.name}"}
            )
        
        # Defer action
        if actions.get("defer", False):
            try:
                await self.deferred_queue.put((event, users))
                return RoutingResult(
                    decision=RoutingDecision.DEFER,
                    routing_metadata={"reason": f"Deferred by rule {rule.name}"}
                )
            except asyncio.QueueFull:
                logger.warning(f"Deferred queue full, ignoring defer action for rule {rule.name}")
        
        # Filter users action
        if "filter_users" in actions:
            filter_config = actions["filter_users"]
            filtered_users = self._filter_users_by_config(users, filter_config)
            users = filtered_users
        
        # Modify event data action
        if "modify_data" in actions:
            modifications = actions["modify_data"]
            event.data.update(modifications)
        
        # Continue with normal routing
        return RoutingResult(decision=RoutingDecision.ROUTE)
    
    def _check_data_condition(self, data: Dict[str, Any], field: str, operator: str, value: Any) -> bool:
        """Check data condition"""
        try:
            # Navigate to field using dot notation
            current_data = data
            for field_part in field.split('.'):
                if isinstance(current_data, dict) and field_part in current_data:
                    current_data = current_data[field_part]
                else:
                    return False
            
            # Apply operator
            if operator == "equals":
                return current_data == value
            elif operator == "not_equals":
                return current_data != value
            elif operator == "contains":
                return value in str(current_data)
            elif operator == "greater_than":
                return float(current_data) > float(value)
            elif operator == "less_than":
                return float(current_data) < float(value)
            elif operator == "in":
                return current_data in value if isinstance(value, list) else False
            else:
                return False
        except (KeyError, ValueError, TypeError):
            return False
    
    def _filter_users_by_config(self, users: Dict[str, WSUser], filter_config: Dict[str, Any]) -> Dict[str, WSUser]:
        """Filter users based on configuration"""
        filtered_users = {}
        
        for user_id, user in users.items():
            include_user = True
            
            # Admin only filter
            if filter_config.get("admin_only", False) and not user.is_admin:
                include_user = False
            
            # Active users only filter
            if filter_config.get("active_only", False) and not user.is_active:
                include_user = False
            
            # User ID whitelist
            if "user_whitelist" in filter_config:
                if user_id not in filter_config["user_whitelist"]:
                    include_user = False
            
            # User ID blacklist
            if "user_blacklist" in filter_config:
                if user_id in filter_config["user_blacklist"]:
                    include_user = False
            
            if include_user:
                filtered_users[user_id] = user
        
        return filtered_users
    
    async def _process_deferred_events(self):
        """Background task to process deferred events"""
        while self._running:
            try:
                # Wait for deferred event
                event, users = await asyncio.wait_for(self.deferred_queue.get(), timeout=1.0)
                
                # Process the deferred event
                logger.debug(f"Processing deferred event {event.id}")
                result = await self.route_event(event, users)
                
                # Mark task as done
                self.deferred_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing deferred event: {e}")
    
    def _update_routing_stats(self, result: RoutingResult, start_time: datetime):
        """Update routing performance statistics"""
        end_time = datetime.utcnow()
        routing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Update performance metrics
        self.performance_metrics["routing_operations"] += 1
        self.performance_metrics["total_routing_time_ms"] += routing_time_ms
        self.performance_metrics["avg_routing_time_ms"] = (
            self.performance_metrics["total_routing_time_ms"] / 
            self.performance_metrics["routing_operations"]
        )
        
        if routing_time_ms > self.performance_metrics["max_routing_time_ms"]:
            self.performance_metrics["max_routing_time_ms"] = routing_time_ms
    
    def add_routing_rule(self, rule: EventRoutingRule):
        """Add a custom routing rule"""
        self.routing_rules[rule.id] = rule
        logger.info(f"Added routing rule: {rule.name}")
    
    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule"""
        if rule_id in self.routing_rules:
            rule = self.routing_rules.pop(rule_id)
            logger.info(f"Removed routing rule: {rule.name}")
            return True
        return False
    
    def get_routing_rule(self, rule_id: str) -> Optional[EventRoutingRule]:
        """Get a routing rule by ID"""
        return self.routing_rules.get(rule_id)
    
    def list_routing_rules(self) -> List[EventRoutingRule]:
        """List all routing rules"""
        return list(self.routing_rules.values())
    
    async def get_user_event_preview(self, user: WSUser, event: Event) -> Dict[str, Any]:
        """Preview how an event would be filtered for a specific user"""
        try:
            should_send, filtered_data = await self.filter_chain.filter_event(event, user)
            
            return {
                "user_id": user.username,
                "event_type": event.type.value,
                "would_receive": should_send,
                "is_subscribed": self.subscription_manager.is_user_subscribed_to_event(user.username, event.type),
                "filtered_data": filtered_data if should_send else None,
                "original_data_size": len(str(event.data)),
                "filtered_data_size": len(str(filtered_data)) if should_send else 0,
                "filter_chain_stats": self.filter_chain.get_chain_stats()
            }
        except Exception as e:
            return {
                "user_id": user.username,
                "event_type": event.type.value,
                "error": str(e)
            }
    
    def get_router_stats(self) -> Dict[str, Any]:
        """Get comprehensive router statistics"""
        return {
            "routing_stats": self.stats.copy(),
            "performance_metrics": self.performance_metrics.copy(),
            "subscription_manager_stats": self.subscription_manager.get_manager_stats(),
            "filter_chain_stats": self.filter_chain.get_chain_stats(),
            "routing_rules": {
                "total_rules": len(self.routing_rules),
                "active_rules": sum(1 for rule in self.routing_rules.values() if rule.is_active),
                "rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "event_types": [et.value for et in rule.event_types],
                        "priority": rule.priority,
                        "is_active": rule.is_active,
                        "created_at": rule.created_at.isoformat()
                    }
                    for rule in self.routing_rules.values()
                ]
            },
            "deferred_queue_size": self.deferred_queue.qsize(),
            "is_running": self._running
        }


# Global event router instance
_event_router = None


def get_event_router() -> EventRouter:
    """Get the global event router instance"""
    global _event_router
    if _event_router is None:
        _event_router = EventRouter()
    return _event_router