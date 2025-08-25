"""
Message batching and optimization system for WebSocket events
Implements time-based and size-based batching with compression and priority handling
"""

import asyncio
import json
import gzip
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from enum import Enum

from .event_types import Event, EventPriority, EventType, BatchedMessage, is_critical_event
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BatchingStrategy(Enum):
    """Batching strategies for different scenarios"""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"
    PRIORITY_BASED = "priority_based"
    ADAPTIVE = "adaptive"


@dataclass
class BatchingConfig:
    """Configuration for message batching"""
    strategy: BatchingStrategy = BatchingStrategy.HYBRID
    max_batch_size: int = 50
    max_batch_bytes: int = 64 * 1024  # 64KB
    batch_timeout_ms: int = 1000  # 1 second
    compression_enabled: bool = True
    compression_threshold: int = 1024  # Compress if > 1KB
    priority_bypass: bool = True  # Critical events bypass batching
    adaptive_sizing: bool = True
    max_queue_size: int = 1000
    
    # Adaptive batching parameters
    min_batch_size: int = 5
    max_batch_timeout_ms: int = 5000
    load_threshold: float = 0.8  # Adjust batching when queue > 80% full


@dataclass
class BatchingMetrics:
    """Metrics for batching performance monitoring"""
    total_events_processed: int = 0
    total_batches_sent: int = 0
    total_bytes_sent: int = 0
    total_bytes_saved: int = 0  # Through compression
    average_batch_size: float = 0.0
    average_compression_ratio: float = 0.0
    critical_events_bypassed: int = 0
    queue_overflows: int = 0
    processing_time_ms: float = 0.0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def reset(self):
        """Reset metrics"""
        self.total_events_processed = 0
        self.total_batches_sent = 0
        self.total_bytes_sent = 0
        self.total_bytes_saved = 0
        self.average_batch_size = 0.0
        self.average_compression_ratio = 0.0
        self.critical_events_bypassed = 0
        self.queue_overflows = 0
        self.processing_time_ms = 0.0
        self.last_reset = datetime.utcnow()


class MessageBatcher:
    """
    Advanced message batching system with multiple strategies and optimization
    """
    
    def __init__(self, config: Optional[BatchingConfig] = None):
        self.config = config or BatchingConfig()
        self.metrics = BatchingMetrics()
        
        # Batching queues per user
        self.user_queues: Dict[str, deque] = defaultdict(deque)
        self.user_batches: Dict[str, BatchedMessage] = {}
        self.user_timers: Dict[str, asyncio.Task] = {}
        
        # Priority queues for immediate delivery
        self.priority_queue: deque = deque()
        
        # Compression cache
        self.compression_cache: Dict[str, Tuple[bytes, float]] = {}
        self.cache_max_size = 100
        
        # Adaptive batching state
        self.load_history: deque = deque(maxlen=100)
        self.current_load: float = 0.0
        
        # Background tasks
        self._running = False
        self._batch_processor_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.send_callback: Optional[Callable[[str, Dict[str, Any]], asyncio.Task]] = None
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], asyncio.Task]] = None
    
    async def start(self):
        """Start the message batcher"""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._batch_processor_task = asyncio.create_task(self._process_batches())
        self._metrics_task = asyncio.create_task(self._update_metrics())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        
        logger.info("Message batcher started")
    
    async def stop(self):
        """Stop the message batcher and flush all pending messages"""
        if not self._running:
            return
        
        self._running = False
        
        # Flush all pending batches
        await self._flush_all_batches()
        
        # Cancel background tasks
        for task in [self._batch_processor_task, self._metrics_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Cancel user timers
        for timer in self.user_timers.values():
            if not timer.done():
                timer.cancel()
        
        self.user_timers.clear()
        logger.info("Message batcher stopped")
    
    def set_send_callback(self, callback: Callable[[str, Dict[str, Any]], asyncio.Task]):
        """Set callback for sending messages to specific users"""
        self.send_callback = callback
    
    def set_broadcast_callback(self, callback: Callable[[Dict[str, Any]], asyncio.Task]):
        """Set callback for broadcasting messages to all users"""
        self.broadcast_callback = callback
    
    async def add_event(self, event: Event, user_id: Optional[str] = None) -> bool:
        """
        Add an event to the batching system
        Returns True if event was queued, False if it was sent immediately
        """
        if not self._running:
            logger.warning("Message batcher not running, dropping event")
            return False
        
        start_time = time.time()
        
        try:
            # Check if event should bypass batching
            if self._should_bypass_batching(event):
                await self._send_immediate(event, user_id)
                self.metrics.critical_events_bypassed += 1
                return False
            
            # Add to appropriate queue
            if user_id:
                await self._add_to_user_queue(event, user_id)
            else:
                await self._add_to_broadcast_queue(event)
            
            self.metrics.total_events_processed += 1
            return True
            
        except Exception as e:
            logger.error(f"Error adding event to batcher: {e}")
            # Fallback to immediate send
            await self._send_immediate(event, user_id)
            return False
        finally:
            processing_time = (time.time() - start_time) * 1000
            self.metrics.processing_time_ms = (
                self.metrics.processing_time_ms * 0.9 + processing_time * 0.1
            )
    
    def _should_bypass_batching(self, event: Event) -> bool:
        """Check if event should bypass batching"""
        if not self.config.priority_bypass:
            return False
        
        # Critical and urgent events bypass batching
        if event.priority in [EventPriority.CRITICAL, EventPriority.URGENT]:
            return True
        
        # Specific critical event types
        if is_critical_event(event.type):
            return True
        
        # Connection events should be immediate
        if event.type in [EventType.PING, EventType.PONG, EventType.CONNECTION_ESTABLISHED]:
            return True
        
        return False
    
    async def _add_to_user_queue(self, event: Event, user_id: str):
        """Add event to user-specific queue"""
        queue = self.user_queues[user_id]
        
        # Check queue size limit
        if len(queue) >= self.config.max_queue_size:
            # Remove oldest event
            queue.popleft()
            self.metrics.queue_overflows += 1
            logger.warning(f"Queue overflow for user {user_id}, dropping oldest event")
        
        queue.append(event)
        
        # Create or update batch for user
        if user_id not in self.user_batches:
            self.user_batches[user_id] = BatchedMessage()
            # Start timer for this user
            self._start_user_timer(user_id)
        
        # Check if batch should be sent immediately
        await self._check_user_batch(user_id)
    
    async def _add_to_broadcast_queue(self, event: Event):
        """Add event to broadcast queue"""
        self.priority_queue.append(('broadcast', event, None))
    
    def _start_user_timer(self, user_id: str):
        """Start timer for user batch"""
        if user_id in self.user_timers:
            # Cancel existing timer
            self.user_timers[user_id].cancel()
        
        timeout = self._get_adaptive_timeout()
        self.user_timers[user_id] = asyncio.create_task(
            self._user_batch_timeout(user_id, timeout)
        )
    
    async def _user_batch_timeout(self, user_id: str, timeout_ms: int):
        """Handle user batch timeout"""
        try:
            await asyncio.sleep(timeout_ms / 1000.0)
            await self._flush_user_batch(user_id)
        except asyncio.CancelledError:
            pass
    
    async def _check_user_batch(self, user_id: str):
        """Check if user batch should be sent"""
        if user_id not in self.user_batches:
            return
        
        batch = self.user_batches[user_id]
        queue = self.user_queues[user_id]
        
        # Add events from queue to batch
        batch_size = self._get_adaptive_batch_size()
        while queue and len(batch.events) < batch_size:
            event = queue.popleft()
            batch.add_event(event)
        
        # Check if batch should be sent
        if (batch.is_full(batch_size, self.config.max_batch_bytes) or 
            batch.should_send_immediately()):
            await self._flush_user_batch(user_id)
    
    async def _flush_user_batch(self, user_id: str):
        """Flush user batch"""
        if user_id not in self.user_batches:
            return
        
        batch = self.user_batches[user_id]
        if not batch.events:
            return
        
        try:
            # Prepare message
            message = await self._prepare_batch_message(batch)
            
            # Send message
            if self.send_callback:
                await self.send_callback(user_id, message)
            
            # Update metrics
            self.metrics.total_batches_sent += 1
            self.metrics.total_bytes_sent += batch.get_size_bytes()
            
            # Update average batch size
            total_events = self.metrics.total_events_processed
            if total_events > 0:
                self.metrics.average_batch_size = (
                    self.metrics.average_batch_size * (self.metrics.total_batches_sent - 1) + 
                    len(batch.events)
                ) / self.metrics.total_batches_sent
            
        except Exception as e:
            logger.error(f"Error flushing batch for user {user_id}: {e}")
        finally:
            # Clean up
            del self.user_batches[user_id]
            if user_id in self.user_timers:
                self.user_timers[user_id].cancel()
                del self.user_timers[user_id]
    
    async def _flush_all_batches(self):
        """Flush all pending batches"""
        # Flush user batches
        user_ids = list(self.user_batches.keys())
        for user_id in user_ids:
            await self._flush_user_batch(user_id)
        
        # Process priority queue
        while self.priority_queue:
            queue_type, event, user_id = self.priority_queue.popleft()
            if queue_type == 'broadcast':
                await self._send_immediate(event, None)
            else:
                await self._send_immediate(event, user_id)
    
    async def _prepare_batch_message(self, batch: BatchedMessage) -> Dict[str, Any]:
        """Prepare batch message with optional compression"""
        message = batch.to_websocket_message()
        
        if self.config.compression_enabled:
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            
            if len(message_bytes) > self.config.compression_threshold:
                # Check compression cache
                cache_key = str(hash(message_str))
                if cache_key in self.compression_cache:
                    compressed_data, compression_ratio = self.compression_cache[cache_key]
                else:
                    # Compress message
                    compressed_data = gzip.compress(message_bytes)
                    compression_ratio = len(compressed_data) / len(message_bytes)
                    
                    # Cache compression result
                    if len(self.compression_cache) < self.cache_max_size:
                        self.compression_cache[cache_key] = (compressed_data, compression_ratio)
                
                # Update batch with compression info
                batch.compressed = True
                batch.compression_ratio = compression_ratio
                
                # Update metrics
                bytes_saved = len(message_bytes) - len(compressed_data)
                self.metrics.total_bytes_saved += bytes_saved
                self.metrics.average_compression_ratio = (
                    self.metrics.average_compression_ratio * 0.9 + compression_ratio * 0.1
                )
                
                # Return compressed message
                return {
                    "compressed": True,
                    "compression_ratio": compression_ratio,
                    "data": compressed_data.hex()  # Hex encode for JSON transport
                }
        
        return message
    
    async def _send_immediate(self, event: Event, user_id: Optional[str]):
        """Send event immediately without batching"""
        try:
            message = event.to_websocket_message()
            
            if user_id and self.send_callback:
                await self.send_callback(user_id, message)
            elif self.broadcast_callback:
                await self.broadcast_callback(message)
            
        except Exception as e:
            logger.error(f"Error sending immediate event: {e}")
    
    def _get_adaptive_batch_size(self) -> int:
        """Get adaptive batch size based on current load"""
        if not self.config.adaptive_sizing:
            return self.config.max_batch_size
        
        # Adjust batch size based on queue load
        if self.current_load > self.config.load_threshold:
            # High load: use larger batches
            return self.config.max_batch_size
        else:
            # Low load: use smaller batches for lower latency
            return max(self.config.min_batch_size, 
                      int(self.config.max_batch_size * self.current_load))
    
    def _get_adaptive_timeout(self) -> int:
        """Get adaptive timeout based on current load"""
        if not self.config.adaptive_sizing:
            return self.config.batch_timeout_ms
        
        # Adjust timeout based on load
        if self.current_load > self.config.load_threshold:
            # High load: shorter timeout for faster processing
            return self.config.batch_timeout_ms
        else:
            # Low load: longer timeout to allow batches to fill
            return min(self.config.max_batch_timeout_ms,
                      int(self.config.batch_timeout_ms * (1 + (1 - self.current_load))))
    
    async def _process_batches(self):
        """Background task to process batches"""
        while self._running:
            try:
                # Process priority queue
                if self.priority_queue:
                    queue_type, event, user_id = self.priority_queue.popleft()
                    if queue_type == 'broadcast':
                        await self._send_immediate(event, None)
                    else:
                        await self._send_immediate(event, user_id)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)
    
    async def _update_metrics(self):
        """Background task to update metrics"""
        while self._running:
            try:
                # Calculate current load
                total_queue_size = sum(len(queue) for queue in self.user_queues.values())
                total_capacity = len(self.user_queues) * self.config.max_queue_size
                
                if total_capacity > 0:
                    self.current_load = total_queue_size / total_capacity
                else:
                    self.current_load = 0.0
                
                self.load_history.append(self.current_load)
                
                # Clean up empty queues
                empty_users = [user_id for user_id, queue in self.user_queues.items() 
                              if not queue and user_id not in self.user_batches]
                for user_id in empty_users:
                    del self.user_queues[user_id]
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_expired(self):
        """Background task to clean up expired data"""
        while self._running:
            try:
                # Clean up compression cache
                if len(self.compression_cache) > self.cache_max_size:
                    # Remove oldest entries
                    items_to_remove = len(self.compression_cache) - self.cache_max_size
                    keys_to_remove = list(self.compression_cache.keys())[:items_to_remove]
                    for key in keys_to_remove:
                        del self.compression_cache[key]
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current batching metrics"""
        return {
            "total_events_processed": self.metrics.total_events_processed,
            "total_batches_sent": self.metrics.total_batches_sent,
            "total_bytes_sent": self.metrics.total_bytes_sent,
            "total_bytes_saved": self.metrics.total_bytes_saved,
            "average_batch_size": self.metrics.average_batch_size,
            "average_compression_ratio": self.metrics.average_compression_ratio,
            "critical_events_bypassed": self.metrics.critical_events_bypassed,
            "queue_overflows": self.metrics.queue_overflows,
            "processing_time_ms": self.metrics.processing_time_ms,
            "current_load": self.current_load,
            "active_user_queues": len(self.user_queues),
            "active_user_batches": len(self.user_batches),
            "priority_queue_size": len(self.priority_queue),
            "compression_cache_size": len(self.compression_cache),
            "config": {
                "strategy": self.config.strategy.value,
                "max_batch_size": self.config.max_batch_size,
                "max_batch_bytes": self.config.max_batch_bytes,
                "batch_timeout_ms": self.config.batch_timeout_ms,
                "compression_enabled": self.config.compression_enabled,
                "priority_bypass": self.config.priority_bypass,
                "adaptive_sizing": self.config.adaptive_sizing
            }
        }
    
    def reset_metrics(self):
        """Reset batching metrics"""
        self.metrics.reset()
    
    async def force_flush_user(self, user_id: str):
        """Force flush batch for specific user"""
        if user_id in self.user_batches:
            await self._flush_user_batch(user_id)
    
    async def force_flush_all(self):
        """Force flush all batches"""
        await self._flush_all_batches()


class NetworkOptimizer:
    """
    Network optimization utilities for WebSocket messages
    """
    
    @staticmethod
    def compress_message(message: Dict[str, Any], threshold: int = 1024) -> Tuple[Dict[str, Any], bool]:
        """
        Compress message if it exceeds threshold
        Returns (message, was_compressed)
        """
        message_str = json.dumps(message)
        message_bytes = message_str.encode('utf-8')
        
        if len(message_bytes) <= threshold:
            return message, False
        
        try:
            compressed_data = gzip.compress(message_bytes)
            compression_ratio = len(compressed_data) / len(message_bytes)
            
            # Only use compression if it saves significant space
            if compression_ratio < 0.8:
                return {
                    "compressed": True,
                    "compression_ratio": compression_ratio,
                    "original_size": len(message_bytes),
                    "compressed_size": len(compressed_data),
                    "data": compressed_data.hex()
                }, True
        except Exception as e:
            logger.error(f"Compression failed: {e}")
        
        return message, False
    
    @staticmethod
    def decompress_message(compressed_message: Dict[str, Any]) -> Dict[str, Any]:
        """Decompress a compressed message"""
        if not compressed_message.get("compressed"):
            return compressed_message
        
        try:
            compressed_data = bytes.fromhex(compressed_message["data"])
            decompressed_data = gzip.decompress(compressed_data)
            return json.loads(decompressed_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise
    
    @staticmethod
    def estimate_message_size(message: Dict[str, Any]) -> int:
        """Estimate message size in bytes"""
        return len(json.dumps(message).encode('utf-8'))
    
    @staticmethod
    def optimize_message_for_transport(message: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize message for network transport"""
        # Remove null values
        def remove_nulls(obj):
            if isinstance(obj, dict):
                return {k: remove_nulls(v) for k, v in obj.items() if v is not None}
            elif isinstance(obj, list):
                return [remove_nulls(item) for item in obj if item is not None]
            return obj
        
        optimized = remove_nulls(message)
        
        # Compress timestamps to shorter format if possible
        if "timestamp" in optimized:
            try:
                # Convert to Unix timestamp if it's an ISO string
                dt = datetime.fromisoformat(optimized["timestamp"].replace('Z', '+00:00'))
                optimized["timestamp"] = int(dt.timestamp())
                optimized["_timestamp_format"] = "unix"
            except:
                pass
        
        return optimized


# Global message batcher instance
_message_batcher: Optional[MessageBatcher] = None


def get_message_batcher(config: Optional[BatchingConfig] = None) -> MessageBatcher:
    """Get the global message batcher instance"""
    global _message_batcher
    if _message_batcher is None:
        _message_batcher = MessageBatcher(config)
    return _message_batcher


async def initialize_message_batcher(config: Optional[BatchingConfig] = None):
    """Initialize and start the global message batcher"""
    batcher = get_message_batcher(config)
    await batcher.start()
    return batcher


async def shutdown_message_batcher():
    """Shutdown the global message batcher"""
    global _message_batcher
    if _message_batcher:
        await _message_batcher.stop()
        _message_batcher = None