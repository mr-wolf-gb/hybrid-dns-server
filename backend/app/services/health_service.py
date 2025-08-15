"""
Health monitoring service for DNS forwarders and system health
"""

import asyncio
import json
import socket
from datetime import datetime
from typing import Dict, List

from ..core.config import get_settings
from ..core.database import database
from ..core.logging_config import get_health_logger


class HealthService:
    """Health monitoring for DNS forwarders and system components"""
    
    def __init__(self):
        self.running = False
    
    async def start(self) -> None:
        """Start health monitoring service"""
        self.running = True
        logger = get_health_logger()
        logger.info("Starting health monitoring service")
        
        # Start background health checks
        asyncio.create_task(self._monitor_forwarders())
        
        logger.info("Health monitoring service started")
    
    async def start_health_checks(self) -> None:
        """Start health checks (alias for install script compatibility)"""
        await self.start()
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop health monitoring service"""
        self.running = False
        logger = get_health_logger()
        logger.info("Health monitoring service stopped")
    
    async def _monitor_forwarders(self):
        """Monitor forwarder health"""
        while self.running:
            try:
                await self._check_all_forwarders()
                settings = get_settings()
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logger = get_health_logger()
                logger.error(f"Error monitoring forwarders: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_forwarders(self):
        """Check health of all configured forwarders"""
        try:
            # Get all active forwarders
            forwarders = await database.fetch_all("""
                SELECT id, domain, servers, forwarder_type
                FROM forwarders 
                WHERE is_active = true
            """)
            
            for forwarder in forwarders:
                servers = json.loads(forwarder["servers"])  # JSON array stored as string
                for server_ip in servers:
                    is_healthy = await self._check_dns_server(server_ip)
                    # TODO: Store health check results in database
                    
        except Exception as e:
            logger = get_health_logger()
            logger.warning(f"Error checking forwarders (table may not exist yet): {e}")
    
    async def _check_dns_server(self, server_ip: str, port: int = 53) -> bool:
        """Check if a DNS server is responding"""
        try:
            # Simple TCP connection test to DNS port
            settings = get_settings()
            future = asyncio.open_connection(server_ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=settings.DNS_QUERY_TIMEOUT)
            
            writer.close()
            await writer.wait_closed()
            
            return True
            
        except Exception:
            return False
    
    async def get_forwarder_health(self) -> List[Dict]:
        """Get health status of all forwarders"""
        try:
            # This is a placeholder - would return actual health check results
            forwarders = await database.fetch_all("""
                SELECT id, domain, servers, forwarder_type
                FROM forwarders 
                WHERE is_active = true
            """)
            
            health_status = []
            for forwarder in forwarders:
                health_status.append({
                    "id": forwarder["id"],
                    "domain": forwarder["domain"],
                    "type": forwarder["forwarder_type"],
                    "servers": json.loads(forwarder["servers"]),
                    "status": "healthy",  # Placeholder
                    "last_check": datetime.utcnow().isoformat(),
                    "response_time": 50  # Placeholder
                })
            
            return health_status
            
        except Exception as e:
            logger = get_health_logger()
            logger.warning(f"Error getting forwarder health (table may not exist yet): {e}")
            return []