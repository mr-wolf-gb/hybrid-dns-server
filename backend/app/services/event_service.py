"""
Event broadcasting service with filtering, routing, persistence, and replay functionality
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update, delete
from sqlalchemy.orm import selectinload
import uuid

from ..core.logging_config import get_logger
from ..core.database import get_database_session
from ..models.events import Event, EventSubscription, EventDelivery, EventFilter, EventReplay
from ..websocket.manager import WebSocketManager, EventType, get_websocket_manager

logger = get_logger(__name__)


class EventBroadcastingService:
    """
    Enhanced event broadcasting service with persistence, filtering, routing, and replay
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        self.websocket_manager = websocket_manager or get_websocket_manager()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.active_replays: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._delivery_retry_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the event broadcasting service"""
        if self._running:
            return
        
        self._running = True
        
        # Start cleanup task for old events and deliveries
        self._cleanup_task = asyncio.create_task(self._cleanup_old_events())
        
        # Start delivery retry task
        self._delivery_retry_task = asyncio.create_task(self._retry_failed_deliveries())
        
        logger.info("Event broadcasting service started")
    
    async def stop(self):
        """Stop the event broadcasting service"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Stop delivery retry task
        if self._delivery_retry_task and not self._delivery_retry_task.done():
            self._delivery_retry_task.cancel()
            try:
                await self._delivery_retry_task
            except asyncio.CancelledError:
                pass
        
        # Cancel active replays
        for replay_id, task in self.active_replays.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.active_replays.clear()
        logger.info("Event broadcasting service stopped")
    
    async def emit_event(
        self,
        event_type: str,
        event_category: str,
        event_source: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
        broadcast_immediately: bool = True
    ) -> Event:
        """
        Emit an event with full persistence and broadcasting capabilities
        """
        async for db in get_database_session():
            try:
                # Create event record
                event = Event(
                    event_type=event_type,
                    event_category=event_category,
                    event_source=event_source,
                    event_data=event_data,
                    user_id=user_id,
                    session_id=session_id,
                    severity=severity,
                    tags=tags,
                    metadata=metadata
                )
                
                if persist:
                    db.add(event)
                    await db.commit()
                    await db.refresh(event)
                
                # Broadcast immediately if requested
                if broadcast_immediately:
                    await self._broadcast_event(event, db)
                
                # Call registered event handlers
                await self._call_event_handlers(event_type, event.to_dict())
                
                logger.debug(f"Event emitted: {event_type} from {event_source}")
                return event
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error emitting event {event_type}: {e}")
                raise
            finally:
                break
    
    async def _broadcast_event(self, event: Event, db: AsyncSession):
        """Broadcast an event to all matching subscriptions"""
        try:
            # Get all active subscriptions that match this event
            matching_subscriptions = await self._get_matching_subscriptions(event, db)
            
            # Create delivery records and broadcast
            for subscription in matching_subscriptions:
                # Create delivery record
                delivery = EventDelivery(
                    event_id=event.id,
                    subscription_id=subscription.id,
                    user_id=subscription.user_id,
                    connection_id=subscription.connection_id,
                    delivery_method="websocket"
                )
                db.add(delivery)
                
                # Attempt immediate delivery via WebSocket
                await self._attempt_websocket_delivery(event, subscription, delivery)
            
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error broadcasting event {event.id}: {e}")
    
    async def _get_matching_subscriptions(self, event: Event, db: AsyncSession) -> List[EventSubscription]:
        """Get all subscriptions that match the given event"""
        query = select(EventSubscription).where(
            and_(
                EventSubscription.is_active == True,
                or_(
                    EventSubscription.expires_at.is_(None),
                    EventSubscription.expires_at > datetime.utcnow()
                )
            )
        )
        
        result = await db.execute(query)
        all_subscriptions = result.scalars().all()
        
        # Filter subscriptions that match the event
        matching_subscriptions = []
        for subscription in all_subscriptions:
            if subscription.matches_event(event):
                matching_subscriptions.append(subscription)
        
        return matching_subscriptions
    
    async def _attempt_websocket_delivery(self, event: Event, subscription: EventSubscription, delivery: EventDelivery):
        """Attempt to deliver an event via WebSocket"""
        try:
            # Prepare message
            message = {
                "type": event.event_type,
                "category": event.event_category,
                "source": event.event_source,
                "data": event.event_data,
                "severity": event.severity,
                "tags": event.tags,
                "metadata": event.metadata,
                "timestamp": event.created_at.isoformat() if event.created_at else datetime.utcnow().isoformat(),
                "event_id": str(event.event_id)
            }
            
            # Send to user via WebSocket manager
            await self.websocket_manager.send_to_user(
                message,
                subscription.user_id,
                subscription.connection_id
            )
            
            # Mark delivery as successful
            delivery.delivery_status = "delivered"
            delivery.delivered_at = datetime.utcnow()
            delivery.delivery_attempts += 1
            delivery.last_attempt_at = datetime.utcnow()
            
        except Exception as e:
            # Mark delivery as failed
            delivery.delivery_status = "failed"
            delivery.failed_at = datetime.utcnow()
            delivery.delivery_attempts += 1
            delivery.last_attempt_at = datetime.utcnow()
            delivery.error_message = str(e)
            
            # Schedule retry if under max attempts
            if delivery.delivery_attempts < delivery.max_attempts:
                delivery.delivery_status = "retrying"
                delivery.retry_after = datetime.utcnow() + timedelta(minutes=5 * delivery.delivery_attempts)
            
            logger.error(f"Failed to deliver event {event.id} to user {subscription.user_id}: {e}")
    
    async def create_subscription(
        self,
        user_id: str,
        connection_id: Optional[str] = None,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        event_source: Optional[str] = None,
        severity_filter: Optional[List[str]] = None,
        tag_filters: Optional[List[str]] = None,
        user_filters: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> EventSubscription:
        """Create a new event subscription"""
        async for db in get_database_session():
            try:
                subscription = EventSubscription(
                    user_id=user_id,
                    connection_id=connection_id,
                    event_type=event_type,
                    event_category=event_category,
                    event_source=event_source,
                    severity_filter=severity_filter,
                    tag_filters=tag_filters,
                    user_filters=user_filters,
                    expires_at=expires_at
                )
                
                db.add(subscription)
                await db.commit()
                await db.refresh(subscription)
                
                logger.info(f"Created event subscription {subscription.subscription_id} for user {user_id}")
                return subscription
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error creating subscription for user {user_id}: {e}")
                raise
            finally:
                break
    
    async def update_subscription(
        self,
        subscription_id: str,
        **updates
    ) -> Optional[EventSubscription]:
        """Update an existing event subscription"""
        async for db in get_database_session():
            try:
                query = select(EventSubscription).where(
                    EventSubscription.subscription_id == subscription_id
                )
                result = await db.execute(query)
                subscription = result.scalar_one_or_none()
                
                if not subscription:
                    return None
                
                # Update fields
                for field, value in updates.items():
                    if hasattr(subscription, field):
                        setattr(subscription, field, value)
                
                subscription.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(subscription)
                
                return subscription
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error updating subscription {subscription_id}: {e}")
                raise
            finally:
                break
    
    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete an event subscription"""
        async for db in get_database_session():
            try:
                query = delete(EventSubscription).where(
                    EventSubscription.subscription_id == subscription_id
                )
                result = await db.execute(query)
                await db.commit()
                
                return result.rowcount > 0
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error deleting subscription {subscription_id}: {e}")
                raise
            finally:
                break
    
    async def get_user_subscriptions(self, user_id: str) -> List[EventSubscription]:
        """Get all subscriptions for a user"""
        async for db in get_database_session():
            try:
                query = select(EventSubscription).where(
                    and_(
                        EventSubscription.user_id == user_id,
                        EventSubscription.is_active == True
                    )
                ).order_by(EventSubscription.created_at.desc())
                
                result = await db.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"Error getting subscriptions for user {user_id}: {e}")
                return []
            finally:
                break
    
    async def create_event_filter(
        self,
        name: str,
        filter_config: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None
    ) -> EventFilter:
        """Create a reusable event filter"""
        async for db in get_database_session():
            try:
                event_filter = EventFilter(
                    name=name,
                    description=description,
                    filter_config=filter_config,
                    created_by=created_by
                )
                
                db.add(event_filter)
                await db.commit()
                await db.refresh(event_filter)
                
                logger.info(f"Created event filter {event_filter.filter_id}: {name}")
                return event_filter
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error creating event filter {name}: {e}")
                raise
            finally:
                break
    
    async def get_events(
        self,
        event_types: Optional[List[str]] = None,
        event_categories: Optional[List[str]] = None,
        event_sources: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        severity_levels: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """Get events with filtering"""
        async for db in get_database_session():
            try:
                query = select(Event)
                
                # Apply filters
                conditions = []
                
                if event_types:
                    conditions.append(Event.event_type.in_(event_types))
                
                if event_categories:
                    conditions.append(Event.event_category.in_(event_categories))
                
                if event_sources:
                    conditions.append(Event.event_source.in_(event_sources))
                
                if user_id:
                    conditions.append(Event.user_id == user_id)
                
                if severity_levels:
                    conditions.append(Event.severity.in_(severity_levels))
                
                if start_time:
                    conditions.append(Event.created_at >= start_time)
                
                if end_time:
                    conditions.append(Event.created_at <= end_time)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Apply ordering, limit, and offset
                query = query.order_by(desc(Event.created_at)).limit(limit).offset(offset)
                
                result = await db.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"Error getting events: {e}")
                return []
            finally:
                break
    
    async def start_event_replay(
        self,
        name: str,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        filter_config: Dict[str, Any],
        replay_speed: int = 1,
        description: Optional[str] = None
    ) -> EventReplay:
        """Start an event replay session"""
        async for db in get_database_session():
            try:
                # Create replay record
                replay = EventReplay(
                    name=name,
                    description=description,
                    user_id=user_id,
                    filter_config=filter_config,
                    replay_speed=replay_speed,
                    start_time=start_time,
                    end_time=end_time
                )
                
                db.add(replay)
                await db.commit()
                await db.refresh(replay)
                
                # Start replay task
                replay_task = asyncio.create_task(
                    self._execute_replay(str(replay.replay_id))
                )
                self.active_replays[str(replay.replay_id)] = replay_task
                
                logger.info(f"Started event replay {replay.replay_id}: {name}")
                return replay
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error starting event replay {name}: {e}")
                raise
            finally:
                break
    
    async def _execute_replay(self, replay_id: str):
        """Execute an event replay session"""
        async for db in get_database_session():
            try:
                # Get replay record
                query = select(EventReplay).where(EventReplay.replay_id == replay_id)
                result = await db.execute(query)
                replay = result.scalar_one_or_none()
                
                if not replay:
                    logger.error(f"Replay {replay_id} not found")
                    return
                
                # Update status to running
                replay.status = "running"
                replay.started_at = datetime.utcnow()
                await db.commit()
                
                # Get events to replay
                events = await self._get_replay_events(replay, db)
                replay.total_events = len(events)
                await db.commit()
                
                if not events:
                    replay.status = "completed"
                    replay.completed_at = datetime.utcnow()
                    replay.progress = 100
                    await db.commit()
                    return
                
                # Calculate time scaling
                if len(events) > 1:
                    original_duration = (events[-1].created_at - events[0].created_at).total_seconds()
                    scaled_duration = original_duration / replay.replay_speed
                    time_scale = scaled_duration / original_duration if original_duration > 0 else 1
                else:
                    time_scale = 1
                
                # Replay events
                start_replay_time = datetime.utcnow()
                first_event_time = events[0].created_at
                
                for i, event in enumerate(events):
                    if not self._running or str(replay.replay_id) not in self.active_replays:
                        break
                    
                    # Calculate when to send this event
                    event_offset = (event.created_at - first_event_time).total_seconds()
                    scaled_offset = event_offset * time_scale
                    target_time = start_replay_time + timedelta(seconds=scaled_offset)
                    
                    # Wait until it's time to send this event
                    now = datetime.utcnow()
                    if target_time > now:
                        wait_time = (target_time - now).total_seconds()
                        await asyncio.sleep(wait_time)
                    
                    # Broadcast the event
                    await self._broadcast_replay_event(event, replay, db)
                    
                    # Update progress
                    replay.processed_events = i + 1
                    replay.progress = int((i + 1) / len(events) * 100)
                    
                    # Commit progress every 10 events
                    if (i + 1) % 10 == 0:
                        await db.commit()
                
                # Mark replay as completed
                replay.status = "completed"
                replay.completed_at = datetime.utcnow()
                replay.progress = 100
                await db.commit()
                
                logger.info(f"Completed event replay {replay_id}")
                
            except asyncio.CancelledError:
                # Mark replay as cancelled
                replay.status = "cancelled"
                replay.completed_at = datetime.utcnow()
                await db.commit()
                logger.info(f"Cancelled event replay {replay_id}")
            except Exception as e:
                # Mark replay as failed
                replay.status = "failed"
                replay.error_message = str(e)
                replay.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Error in event replay {replay_id}: {e}")
            finally:
                # Clean up
                if replay_id in self.active_replays:
                    del self.active_replays[replay_id]
                break
    
    async def _get_replay_events(self, replay: EventReplay, db: AsyncSession) -> List[Event]:
        """Get events for replay based on filter configuration"""
        query = select(Event).where(
            and_(
                Event.created_at >= replay.start_time,
                Event.created_at <= replay.end_time
            )
        )
        
        # Apply filters from configuration
        config = replay.filter_config
        conditions = []
        
        if "event_types" in config:
            conditions.append(Event.event_type.in_(config["event_types"]))
        
        if "event_categories" in config:
            conditions.append(Event.event_category.in_(config["event_categories"]))
        
        if "event_sources" in config:
            conditions.append(Event.event_source.in_(config["event_sources"]))
        
        if "severity_levels" in config:
            conditions.append(Event.severity.in_(config["severity_levels"]))
        
        if "user_ids" in config:
            conditions.append(Event.user_id.in_(config["user_ids"]))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Event.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _broadcast_replay_event(self, event: Event, replay: EventReplay, db: AsyncSession):
        """Broadcast a replayed event"""
        # Create a replay-specific message
        message = {
            "type": "event_replay",
            "replay_id": str(replay.replay_id),
            "original_event": {
                "type": event.event_type,
                "category": event.event_category,
                "source": event.event_source,
                "data": event.event_data,
                "severity": event.severity,
                "tags": event.tags,
                "metadata": event.metadata,
                "timestamp": event.created_at.isoformat(),
                "event_id": str(event.event_id)
            },
            "replay_timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to the user who started the replay
        await self.websocket_manager.send_to_user(message, replay.user_id)
    
    async def stop_event_replay(self, replay_id: str) -> bool:
        """Stop an active event replay"""
        if replay_id in self.active_replays:
            task = self.active_replays[replay_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Update database status
            async for db in get_database_session():
                try:
                    query = update(EventReplay).where(
                        EventReplay.replay_id == replay_id
                    ).values(
                        status="cancelled",
                        completed_at=datetime.utcnow()
                    )
                    await db.execute(query)
                    await db.commit()
                    break
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error updating replay status: {e}")
                    break
            
            return True
        
        return False
    
    async def get_replay_status(self, replay_id: str) -> Optional[EventReplay]:
        """Get the status of an event replay"""
        async for db in get_database_session():
            try:
                query = select(EventReplay).where(EventReplay.replay_id == replay_id)
                result = await db.execute(query)
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Error getting replay status: {e}")
                return None
            finally:
                break
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for a specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _call_event_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """Call registered event handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
    
    async def _cleanup_old_events(self):
        """Background task to clean up old events and deliveries"""
        while self._running:
            try:
                async for db in get_database_session():
                    try:
                        # Clean up events older than 30 days
                        cutoff_date = datetime.utcnow() - timedelta(days=30)
                        
                        # Delete old deliveries first (foreign key constraint)
                        delivery_query = delete(EventDelivery).where(
                            EventDelivery.created_at < cutoff_date
                        )
                        delivery_result = await db.execute(delivery_query)
                        
                        # Delete old events
                        event_query = delete(Event).where(
                            Event.created_at < cutoff_date
                        )
                        event_result = await db.execute(event_query)
                        
                        await db.commit()
                        
                        if delivery_result.rowcount > 0 or event_result.rowcount > 0:
                            logger.info(f"Cleaned up {event_result.rowcount} old events and {delivery_result.rowcount} old deliveries")
                        
                        break
                        
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Error in cleanup task: {e}")
                        break
                
                # Wait 24 hours before next cleanup
                await asyncio.sleep(24 * 60 * 60)
                
            except asyncio.CancelledError:
                logger.info("Event cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour on error
    
    async def _retry_failed_deliveries(self):
        """Background task to retry failed event deliveries"""
        while self._running:
            try:
                async for db in get_database_session():
                    try:
                        # Get deliveries that need retry
                        query = select(EventDelivery).options(
                            selectinload(EventDelivery.event),
                            selectinload(EventDelivery.subscription)
                        ).where(
                            and_(
                                EventDelivery.delivery_status == "retrying",
                                EventDelivery.retry_after <= datetime.utcnow(),
                                EventDelivery.delivery_attempts < EventDelivery.max_attempts
                            )
                        ).limit(100)
                        
                        result = await db.execute(query)
                        deliveries = result.scalars().all()
                        
                        for delivery in deliveries:
                            try:
                                await self._attempt_websocket_delivery(
                                    delivery.event,
                                    delivery.subscription,
                                    delivery
                                )
                            except Exception as e:
                                logger.error(f"Error retrying delivery {delivery.id}: {e}")
                        
                        if deliveries:
                            await db.commit()
                            logger.info(f"Retried {len(deliveries)} failed deliveries")
                        
                        break
                        
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Error in delivery retry task: {e}")
                        break
                
                # Wait 5 minutes before next retry check
                await asyncio.sleep(5 * 60)
                
            except asyncio.CancelledError:
                logger.info("Delivery retry task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in delivery retry loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event broadcasting statistics"""
        async for db in get_database_session():
            try:
                # Get event counts by category
                event_counts_query = select(
                    Event.event_category,
                    func.count(Event.id).label('count')
                ).group_by(Event.event_category)
                
                event_counts_result = await db.execute(event_counts_query)
                event_counts = {row.event_category: row.count for row in event_counts_result}
                
                # Get delivery statistics
                delivery_stats_query = select(
                    EventDelivery.delivery_status,
                    func.count(EventDelivery.id).label('count')
                ).group_by(EventDelivery.delivery_status)
                
                delivery_stats_result = await db.execute(delivery_stats_query)
                delivery_stats = {row.delivery_status: row.count for row in delivery_stats_result}
                
                # Get subscription count
                subscription_count_query = select(func.count(EventSubscription.id)).where(
                    EventSubscription.is_active == True
                )
                subscription_count_result = await db.execute(subscription_count_query)
                subscription_count = subscription_count_result.scalar()
                
                # Get active replay count
                active_replay_count = len(self.active_replays)
                
                return {
                    "event_counts_by_category": event_counts,
                    "delivery_statistics": delivery_stats,
                    "active_subscriptions": subscription_count,
                    "active_replays": active_replay_count,
                    "service_running": self._running,
                    "total_events_today": await self._get_events_count_today(db),
                    "websocket_connections": self.websocket_manager.get_connection_stats()
                }
                
            except Exception as e:
                logger.error(f"Error getting event statistics: {e}")
                return {}
            finally:
                break
    
    async def _get_events_count_today(self, db: AsyncSession) -> int:
        """Get count of events created today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count(Event.id)).where(Event.created_at >= today_start)
        result = await db.execute(query)
        return result.scalar() or 0


# Global event broadcasting service instance
_event_service = None

def get_event_service() -> EventBroadcastingService:
    """Get the global event broadcasting service instance"""
    global _event_service
    if _event_service is None:
        _event_service = EventBroadcastingService()
    return _event_service