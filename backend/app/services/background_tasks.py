"""
Background task service for periodic health checks and maintenance
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from ..core.config import get_settings
from ..core.database import get_database_session
from ..core.logging_config import get_logger
from .health_service import get_health_service

logger = get_logger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks like health checks and maintenance"""
    
    def __init__(self):
        self.running = False
        self._tasks = []
        self._health_service = get_health_service()
    
    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Background task service is already running")
            return
        
        self.running = True
        logger.info("Starting background task service")
        
        # Start health monitoring
        await self._health_service.start()
        
        # Start periodic cleanup task
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._tasks.append(cleanup_task)
        
        logger.info("Background task service started")
    
    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping background task service")
        
        # Stop health monitoring
        await self._health_service.stop()
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("Background task service stopped")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old health records and logs"""
        settings = get_settings()
        cleanup_interval = getattr(settings, 'CLEANUP_INTERVAL', 3600)  # Default 1 hour
        
        logger.info(f"Starting periodic cleanup with {cleanup_interval}s interval")
        
        while self.running:
            try:
                await self._run_cleanup_tasks()
                await asyncio.sleep(cleanup_interval)
                
            except asyncio.CancelledError:
                logger.info("Periodic cleanup cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _run_cleanup_tasks(self):
        """Run cleanup tasks"""
        try:
            async for db in get_database_session():
                try:
                    # Clean up old health records (keep 30 days)
                    deleted_count = await self._health_service.cleanup_old_health_records(db, days_to_keep=30)
                    
                    if deleted_count > 0:
                        logger.info(f"Cleanup: Removed {deleted_count} old health check records")
                    
                    break  # Exit the async for loop after successful execution
                    
                except Exception as e:
                    logger.error(f"Error in cleanup tasks: {e}")
                    
        except Exception as e:
            logger.error(f"Error accessing database for cleanup: {e}")
    
    async def trigger_immediate_health_check(self):
        """Trigger an immediate health check for all forwarders"""
        try:
            async for db in get_database_session():
                try:
                    result = await self._health_service.trigger_health_check_for_all(db)
                    logger.info(f"Triggered health check for {result['triggered_count']} forwarders")
                    return result
                    
                except Exception as e:
                    logger.error(f"Error triggering immediate health check: {e}")
                    return {"error": str(e)}
                    
        except Exception as e:
            logger.error(f"Error accessing database for health check: {e}")
            return {"error": str(e)}
    
    def is_running(self) -> bool:
        """Check if the background task service is running"""
        return self.running
    
    async def get_service_status(self) -> dict:
        """Get status of background services"""
        return {
            "background_tasks_running": self.running,
            "health_service_running": self._health_service.is_running(),
            "active_tasks": len([t for t in self._tasks if not t.done()]),
            "total_tasks": len(self._tasks),
            "timestamp": datetime.utcnow()
        }


# Global background task service instance
_background_task_service = None

def get_background_task_service() -> BackgroundTaskService:
    """Get the global background task service instance"""
    global _background_task_service
    if _background_task_service is None:
        _background_task_service = BackgroundTaskService()
    return _background_task_service


@asynccontextmanager
async def background_task_lifespan():
    """Context manager for background task service lifecycle"""
    service = get_background_task_service()
    try:
        await service.start()
        yield service
    finally:
        await service.stop()