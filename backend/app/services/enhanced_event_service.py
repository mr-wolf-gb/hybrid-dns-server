"""
Enhanced event broadcasting service with message batching and optimization
Integrates with the unified WebSocket system and message batcher
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update, delete
import uuid

from ..core.logging_config import get_logger
from ..core.database import get_database_session
from ..models.events import Event as DBEvent, EventSubscription, EventDelivery
from ..websocket.event_types import (
    Event, EventType, EventPriority, EventCategory, EventSeverity, 
    EventMetadata, EventFilter, create_event, is_critical_event
)
from ..websocket.message_batcher import MessageBatcher, BatchingConfig, get_message_batcher
from ..websocket.unified_manager import get_unified_websocket_manager

logger = get_logger(__name__)


class EnhancedEventBroadcastingService:
    """
    Enhanced event broadcasting service with batching, filtering, and optimization
    """
    
    def __init__(self, 
                 websocket_manager=None, 
                 message_batcher: Optional[MessageBatcher] = None,
                 batching_config: Optional[BatchingConfig] = None):
        self.websocket_manager = websocket_manager or get_unified_websocket_manager()
        self.message_batcher = message_batcher or get_message_batcher(batching_config)
        
        # Event processors and handlers
        self.event_processors: Dict[EventType, List[Callable]] = {}
        self.event_filters: List[EventFilter] = []
        self.global_filters: List[Callable[[Event], bool]] = []
        
        # Background tasks
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._processor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_filtered": 0,
            "events_failed": 0,
            "events_batched": 0,
            "events_immediate": 0,
            "start_time": datetime.utcnow()
        }
        
        # Setup message batcher callbacks
        self._setup_batcher_callbacks()
    
    def _setup_batcher_callbacks(self):
        """Setup callbacks for message batcher"""
        self.message_batcher.set_send_callback(self._send_to_user)
        self.message_batcher.set_broadcast_callback(self._broadcast_to_all)
    
    async def start(self):
        """Start the enhanced event broadcasting service"""
        if self._running:
            return
        
        self._running = True
        
        # Start message batcher
        await self.message_batcher.start()
        
        # Start background tasks
        self._processor_task = asyncio.create_task(self._process_event_queue())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
        
        logger.info("Enhanced event broadcasting service started")
    
    async def stop(self):
        """Stop the enhanced event broadcasting service"""
        if not self._running:
            return
        
        self._running = False
        
        # Process remaining events
        await self._flush_event_queue()
        
        # Stop message batcher
        await self.message_batcher.stop()
        
        # Cancel background tasks
        for task in [self._processor_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Enhanced event broadcasting service stopped")
    
    async def emit_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source_user_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        priority: Optional[EventPriority] = None,
        severity: Optional[EventSeverity] = None,
        metadata: Optional[EventMetadata] = None,
        persist: bool = True,
        broadcast_immediately: bool = None,
        **kwargs
    ) -> Event:
        """
        Emit an event with enhanced processing and batching
        """
        try:
            # Create event
            event = create_event(
                event_type=event_type,
                data=data,
                source_user_id=source_user_id,
                target_user_id=target_user_id,
                priority=priority,
                severity=severity,
                metadata=metadata,
                **kwargs
            )
            
            # Determine if should broadcast immediately
            if broadcast_immediately is None:
                broadcast_immediately = is_critical_event(event_type) or event.priority in [
                    EventPriority.CRITICAL, EventPriority.URGENT
                ]
            
            # Add to processing queue
            try:
                self._event_queue.put_nowait({
                    "event": event,
                    "persist": persist,
                    "broadcast_immediately": broadcast_immediately
                })
                self.stats["events_emitted"] += 1
            except asyncio.QueueFull:
                logger.error("Event queue full, dropping event")
                self.stats["events_failed"] += 1
                # Process immediately as fallback
                await self._process_single_event(event, persist, broadcast_immediately)
            
            return event
            
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
            self.stats["events_failed"] += 1
            raise
    
    async def _process_event_queue(self):
        """Background task to process event queue"""
        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event_data = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._process_single_event(**event_data)
                    self._event_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                await asyncio.sleep(1)
    
    async def _process_single_event(self, event: Event, persist: bool, broadcast_immediately: bool):
        """Process a single event"""
        try:
            # Apply global filters
            if not self._apply_global_filters(event):
                self.stats["events_filtered"] += 1
                return
            
            # Persist event if requested
            if persist:
                await self._persist_event(event)
            
            # Process event with registered processors
            await self._call_event_processors(event)
            
            # Broadcast event
            if broadcast_immediately:
                await self._broadcast_immediate(event)
                self.stats["events_immediate"] += 1
            else:
                await self._broadcast_batched(event)
                self.stats["events_batched"] += 1
            
            self.stats["events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
            self.stats["events_failed"] += 1
    
    def _apply_global_filters(self, event: Event) -> bool:
        """Apply global event filters"""
        for filter_func in self.global_filters:
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                logger.error(f"Error in global filter: {e}")
        return True
    
    async def _persist_event(self, event: Event):
        """Persist event to database"""
        async for db in get_database_session():
            try:
                db_event = DBEvent(
                    event_id=uuid.UUID(event.id),
                    event_type=event.type.value,
                    event_category=event.category.value,
                    event_source=event.metadata.source_service or "websocket_service",
                    event_data=event.data,
                    user_id=event.source_user_id,
                    session_id=event.metadata.session_id,
                    severity=event.severity.value,
                    tags=event.metadata.tags,
                    event_metadata=event.metadata.custom_fields
                )
                
                db.add(db_event)
                await db.commit()
                break
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error persisting event {event.id}: {e}")
                break
    
    async def _call_event_processors(self, event: Event):
        """Call registered event processors"""
        processors = self.event_processors.get(event.type, [])
        for processor in processors:
            try:
                if asyncio.iscoroutinefunction(processor):
                    await processor(event)
                else:
                    processor(event)
            except Exception as e:
                logger.error(f"Error in event processor for {event.type}: {e}")
    
    async def _broadcast_immediate(self, event: Event):
        """Broadcast event immediately without batching"""
        if event.target_user_id:
            # Send to specific user
            await self._send_to_user(event.target_user_id, event.to_websocket_message())
        else:
            # Broadcast to all users
            await self._broadcast_to_all(event.to_websocket_message())
    
    async def _broadcast_batched(self, event: Event):
        """Broadcast event through message batcher"""
        if event.target_user_id:
            # Add to user-specific batch
            await self.message_batcher.add_event(event, event.target_user_id)
        else:
            # Add to broadcast batch
            await self.message_batcher.add_event(event, None)
    
    async def _send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        try:
            await self.websocket_manager.send_to_user(user_id, message)
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def _broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all users"""
        try:
            await self.websocket_manager.broadcast_event(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
    async def _flush_event_queue(self):
        """Flush remaining events in queue"""
        while not self._event_queue.empty():
            try:
                event_data = self._event_queue.get_nowait()
                await self._process_single_event(**event_data)
                self._event_queue.task_done()
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error flushing event queue: {e}")
    
    async def _cleanup_old_data(self):
        """Background task to clean up old data"""
        while self._running:
            try:
                # Clean up old persisted events (older than 30 days)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                async for db in get_database_session():
                    try:
                        # Delete old events
                        delete_query = delete(DBEvent).where(
                            DBEvent.created_at < cutoff_date
                        )
                        result = await db.execute(delete_query)
                        await db.commit()
                        
                        if result.rowcount > 0:
                            logger.info(f"Cleaned up {result.rowcount} old events")
                        
                        break
                        
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Error cleaning up old events: {e}")
                        break
                
                # Wait 24 hours before next cleanup
                await asyncio.sleep(24 * 60 * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour on error
    
    def register_event_processor(self, event_type: EventType, processor: Callable):
        """Register an event processor for specific event type"""
        if event_type not in self.event_processors:
            self.event_processors[event_type] = []
        self.event_processors[event_type].append(processor)
        logger.info(f"Registered processor for event type {event_type.value}")
    
    def unregister_event_processor(self, event_type: EventType, processor: Callable):
        """Unregister an event processor"""
        if event_type in self.event_processors:
            try:
                self.event_processors[event_type].remove(processor)
                if not self.event_processors[event_type]:
                    del self.event_processors[event_type]
                logger.info(f"Unregistered processor for event type {event_type.value}")
            except ValueError:
                pass
    
    def add_global_filter(self, filter_func: Callable[[Event], bool]):
        """Add a global event filter"""
        self.global_filters.append(filter_func)
        logger.info("Added global event filter")
    
    def remove_global_filter(self, filter_func: Callable[[Event], bool]):
        """Remove a global event filter"""
        try:
            self.global_filters.remove(filter_func)
            logger.info("Removed global event filter")
        except ValueError:
            pass
    
    async def create_subscription(
        self,
        user_id: str,
        event_filter: EventFilter,
        connection_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Create an event subscription with enhanced filtering"""
        async for db in get_database_session():
            try:
                subscription = EventSubscription(
                    user_id=user_id,
                    connection_id=connection_id,
                    event_type=event_filter.event_types[0].value if event_filter.event_types else None,
                    event_category=event_filter.event_categories[0].value if event_filter.event_categories else None,
                    severity_filter=[s.value for s in event_filter.severities] if event_filter.severities else None,
                    tag_filters=event_filter.tags,
                    expires_at=expires_at
                )
                
                db.add(subscription)
                await db.commit()
                await db.refresh(subscription)
                
                logger.info(f"Created subscription {subscription.subscription_id} for user {user_id}")
                return str(subscription.subscription_id)
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error creating subscription: {e}")
                raise
            finally:
                break
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        uptime = datetime.utcnow() - self.stats["start_time"]
        batcher_metrics = self.message_batcher.get_metrics()
        
        return {
            "service_stats": {
                **self.stats,
                "uptime_seconds": uptime.total_seconds(),
                "events_per_second": self.stats["events_processed"] / max(uptime.total_seconds(), 1),
                "queue_size": self._event_queue.qsize(),
                "running": self._running
            },
            "batcher_metrics": batcher_metrics,
            "websocket_stats": self.websocket_manager.get_connection_stats() if hasattr(self.websocket_manager, 'get_connection_stats') else {}
        }
    
    def reset_statistics(self):
        """Reset service statistics"""
        self.stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_filtered": 0,
            "events_failed": 0,
            "events_batched": 0,
            "events_immediate": 0,
            "start_time": datetime.utcnow()
        }
        self.message_batcher.reset_metrics()
    
    # Convenience methods for common event types
    async def emit_health_update(self, data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit health update event"""
        return await self.emit_event(EventType.HEALTH_UPDATE, data, target_user_id=user_id)
    
    async def emit_security_alert(self, data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit security alert event"""
        return await self.emit_event(
            EventType.SECURITY_ALERT, 
            data, 
            target_user_id=user_id,
            priority=EventPriority.CRITICAL,
            severity=EventSeverity.CRITICAL
        )
    
    async def emit_dns_change(self, event_type: EventType, data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit DNS change event"""
        return await self.emit_event(event_type, data, source_user_id=user_id)
    
    async def emit_system_status(self, data: Dict[str, Any]):
        """Emit system status event"""
        return await self.emit_event(EventType.SYSTEM_STATUS, data)
    
    async def emit_bulk_operation_progress(self, operation_id: str, progress: int, total: int, user_id: str):
        """Emit bulk operation progress event"""
        return await self.emit_event(
            EventType.BULK_OPERATION_PROGRESS,
            {
                "operation_id": operation_id,
                "progress": progress,
                "total": total,
                "percentage": (progress / total * 100) if total > 0 else 0
            },
            target_user_id=user_id
        )


# Global enhanced event service instance
_enhanced_event_service: Optional[EnhancedEventBroadcastingService] = None


def get_enhanced_event_service(
    websocket_manager=None,
    message_batcher: Optional[MessageBatcher] = None,
    batching_config: Optional[BatchingConfig] = None
) -> EnhancedEventBroadcastingService:
    """Get the global enhanced event service instance"""
    global _enhanced_event_service
    if _enhanced_event_service is None:
        _enhanced_event_service = EnhancedEventBroadcastingService(
            websocket_manager, message_batcher, batching_config
        )
    return _enhanced_event_service


async def initialize_enhanced_event_service(
    websocket_manager=None,
    batching_config: Optional[BatchingConfig] = None
) -> EnhancedEventBroadcastingService:
    """Initialize and start the enhanced event service"""
    service = get_enhanced_event_service(websocket_manager=websocket_manager, batching_config=batching_config)
    await service.start()
    return service


async def shutdown_enhanced_event_service():
    """Shutdown the enhanced event service"""
    global _enhanced_event_service
    if _enhanced_event_service:
        await _enhanced_event_service.stop()
        _enhanced_event_service = None