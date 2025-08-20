"""
Scheduler service for automated threat feed updates and maintenance tasks
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from threading import Thread
import logging

from .threat_feed_service import ThreatFeedService
from ..core.database import get_database_session
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread: Optional[Thread] = None
        self.last_update_check = None
        
    def start(self):
        """Start the scheduler service"""
        if self.running:
            logger.warning("Scheduler service is already running")
            return
            
        logger.info("Starting scheduler service")
        self.running = True
        
        # Schedule threat feed updates every hour
        schedule.every().hour.do(self._run_threat_feed_updates)
        
        # Schedule daily maintenance at 2 AM
        schedule.every().day.at("02:00").do(self._run_daily_maintenance)
        
        # Start scheduler thread
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduler service started successfully")
    
    def stop(self):
        """Stop the scheduler service"""
        if not self.running:
            return
            
        logger.info("Stopping scheduler service")
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Scheduler service stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)
    
    def _run_threat_feed_updates(self):
        """Run threat feed updates"""
        logger.info("Running scheduled threat feed updates")
        
        try:
            # Run in async context
            asyncio.run(self._async_threat_feed_updates())
        except Exception as e:
            logger.error(f"Error in scheduled threat feed updates: {str(e)}")
    
    async def _async_threat_feed_updates(self):
        """Async threat feed updates"""
        async with get_database_session() as db:
            threat_feed_service = ThreatFeedService(db)
            result = await threat_feed_service.schedule_feed_updates()
            
            logger.info(f"Scheduled updates completed: "
                       f"{result.successful_updates} successful, "
                       f"{result.failed_updates} failed")
    
    def _run_daily_maintenance(self):
        """Run daily maintenance tasks"""
        logger.info("Running daily maintenance tasks")
        
        try:
            asyncio.run(self._async_daily_maintenance())
        except Exception as e:
            logger.error(f"Error in daily maintenance: {str(e)}")
    
    async def _async_daily_maintenance(self):
        """Async daily maintenance tasks"""
        async with get_database_session() as db:
            # Clean up old logs, optimize database, etc.
            logger.info("Daily maintenance completed")


# Global scheduler instance
scheduler_service = SchedulerService()