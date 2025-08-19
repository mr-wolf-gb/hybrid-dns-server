"""
Health monitoring service for DNS forwarders and system health
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import get_settings
from ..core.database import get_database_session
from ..core.logging_config import get_health_logger
from ..models.dns import Forwarder, ForwarderHealth
from .forwarder_service import ForwarderService


class HealthService:
    """Health monitoring for DNS forwarders and system components"""
    
    def __init__(self):
        self.running = False
        self._health_check_task = None
        self._logger = get_health_logger()
    
    async def start(self) -> None:
        """Start health monitoring service"""
        if self.running:
            self._logger.warning("Health monitoring service is already running")
            return
            
        self.running = True
        self._logger.info("Starting health monitoring service")
        
        # Start background health checks
        self._health_check_task = asyncio.create_task(self._monitor_forwarders())
        
        self._logger.info("Health monitoring service started")
    
    async def start_health_checks(self) -> None:
        """Start health checks (alias for install script compatibility)"""
        await self.start()
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self._logger.info("Health check service cancelled")
            await self.stop()
    
    async def stop(self) -> None:
        """Stop health monitoring service"""
        if not self.running:
            return
            
        self.running = False
        
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        self._logger.info("Health monitoring service stopped")
    
    async def _monitor_forwarders(self):
        """Monitor forwarder health continuously"""
        settings = get_settings()
        check_interval = getattr(settings, 'HEALTH_CHECK_INTERVAL', 300)  # Default 5 minutes
        
        self._logger.info(f"Starting forwarder health monitoring with {check_interval}s interval")
        
        while self.running:
            try:
                await self._check_all_forwarders()
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                self._logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                self._logger.error(f"Error in health monitoring loop: {e}")
                # Wait a bit before retrying to avoid rapid error loops
                await asyncio.sleep(60)
    
    async def _check_all_forwarders(self):
        """Check health of all configured forwarders"""
        try:
            # Get database session
            async for db in get_database_session():
                try:
                    forwarder_service = ForwarderService(db)
                    
                    # Get all active forwarders with health checking enabled
                    result = await forwarder_service.get_forwarders(
                        active_only=True,
                        limit=1000  # Get all forwarders
                    )
                    forwarders = result["items"]
                    
                    health_check_count = 0
                    for forwarder in forwarders:
                        if forwarder.health_check_enabled:
                            try:
                                await forwarder_service.perform_health_check(forwarder.id)
                                health_check_count += 1
                            except Exception as e:
                                self._logger.error(f"Error checking health for forwarder {forwarder.name}: {e}")
                    
                    if health_check_count > 0:
                        self._logger.debug(f"Completed health checks for {health_check_count} forwarders")
                    
                    break  # Exit the async for loop after successful execution
                    
                except Exception as e:
                    self._logger.error(f"Error in forwarder health check cycle: {e}")
                    # Continue to next iteration
                    
        except Exception as e:
            self._logger.warning(f"Error accessing database for health checks: {e}")
    
    async def get_forwarder_health_summary(self, db: Session | AsyncSession) -> Dict:
        """Get comprehensive health summary for all forwarders"""
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all forwarders
            result = await forwarder_service.get_forwarders(limit=1000)
            forwarders = result["items"]
            
            summary = {
                "total_forwarders": len(forwarders),
                "active_forwarders": 0,
                "health_check_enabled": 0,
                "healthy_forwarders": 0,
                "unhealthy_forwarders": 0,
                "degraded_forwarders": 0,
                "unknown_forwarders": 0,
                "last_updated": datetime.utcnow(),
                "forwarder_details": []
            }
            
            for forwarder in forwarders:
                if forwarder.is_active:
                    summary["active_forwarders"] += 1
                
                if forwarder.health_check_enabled:
                    summary["health_check_enabled"] += 1
                    
                    # Get current health status
                    health_status = await forwarder_service.get_current_health_status(forwarder.id)
                    status = health_status.get("overall_status", "unknown")
                    
                    if status == "healthy":
                        summary["healthy_forwarders"] += 1
                    elif status == "unhealthy":
                        summary["unhealthy_forwarders"] += 1
                    elif status == "degraded":
                        summary["degraded_forwarders"] += 1
                    else:
                        summary["unknown_forwarders"] += 1
                    
                    summary["forwarder_details"].append({
                        "id": forwarder.id,
                        "name": forwarder.name,
                        "type": forwarder.forwarder_type,
                        "is_active": forwarder.is_active,
                        "health_check_enabled": forwarder.health_check_enabled,
                        "status": status,
                        "healthy_servers": health_status.get("healthy_servers", 0),
                        "total_servers": health_status.get("total_servers", 0),
                        "last_checked": health_status.get("last_checked")
                    })
                else:
                    summary["unknown_forwarders"] += 1
                    summary["forwarder_details"].append({
                        "id": forwarder.id,
                        "name": forwarder.name,
                        "type": forwarder.forwarder_type,
                        "is_active": forwarder.is_active,
                        "health_check_enabled": forwarder.health_check_enabled,
                        "status": "disabled",
                        "healthy_servers": 0,
                        "total_servers": len(forwarder.servers) if forwarder.servers else 0,
                        "last_checked": None
                    })
            
            return summary
            
        except Exception as e:
            self._logger.error(f"Error getting forwarder health summary: {e}")
            return {
                "total_forwarders": 0,
                "active_forwarders": 0,
                "health_check_enabled": 0,
                "healthy_forwarders": 0,
                "unhealthy_forwarders": 0,
                "degraded_forwarders": 0,
                "unknown_forwarders": 0,
                "last_updated": datetime.utcnow(),
                "forwarder_details": [],
                "error": str(e)
            }
    
    async def get_unhealthy_forwarders(self, db: Session | AsyncSession) -> List[Dict]:
        """Get list of forwarders that are currently unhealthy"""
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all active forwarders with health checking enabled
            result = await forwarder_service.get_forwarders(active_only=True, limit=1000)
            forwarders = result["items"]
            
            unhealthy_forwarders = []
            
            for forwarder in forwarders:
                if forwarder.health_check_enabled:
                    health_status = await forwarder_service.get_current_health_status(forwarder.id)
                    status = health_status.get("overall_status", "unknown")
                    
                    if status in ["unhealthy", "degraded"]:
                        unhealthy_forwarders.append({
                            "id": forwarder.id,
                            "name": forwarder.name,
                            "type": forwarder.forwarder_type,
                            "status": status,
                            "healthy_servers": health_status.get("healthy_servers", 0),
                            "total_servers": health_status.get("total_servers", 0),
                            "last_checked": health_status.get("last_checked"),
                            "server_statuses": health_status.get("server_statuses", {})
                        })
            
            return unhealthy_forwarders
            
        except Exception as e:
            self._logger.error(f"Error getting unhealthy forwarders: {e}")
            return []
    
    async def trigger_health_check_for_all(self, db: Session | AsyncSession) -> Dict:
        """Manually trigger health checks for all forwarders"""
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all active forwarders with health checking enabled
            result = await forwarder_service.get_forwarders(active_only=True, limit=1000)
            forwarders = result["items"]
            
            triggered_count = 0
            errors = []
            
            for forwarder in forwarders:
                if forwarder.health_check_enabled:
                    try:
                        await forwarder_service.perform_health_check(forwarder.id)
                        triggered_count += 1
                    except Exception as e:
                        errors.append(f"Error checking {forwarder.name}: {str(e)}")
            
            return {
                "triggered_count": triggered_count,
                "total_eligible": len([f for f in forwarders if f.health_check_enabled]),
                "errors": errors,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            self._logger.error(f"Error triggering health checks: {e}")
            return {
                "triggered_count": 0,
                "total_eligible": 0,
                "errors": [str(e)],
                "timestamp": datetime.utcnow()
            }
    
    async def cleanup_old_health_records(self, db: Session | AsyncSession, days_to_keep: int = 30) -> int:
        """Clean up old health check records to prevent database bloat"""
        try:
            from ..models.dns import ForwarderHealth
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            if hasattr(db, 'execute'):  # AsyncSession
                from sqlalchemy import delete
                result = await db.execute(
                    delete(ForwarderHealth).where(ForwarderHealth.checked_at < cutoff_date)
                )
                await db.commit()
                deleted_count = result.rowcount
            else:  # Regular Session
                deleted_count = db.query(ForwarderHealth).filter(
                    ForwarderHealth.checked_at < cutoff_date
                ).delete()
                db.commit()
            
            if deleted_count > 0:
                self._logger.info(f"Cleaned up {deleted_count} old health check records")
            
            return deleted_count
            
        except Exception as e:
            self._logger.error(f"Error cleaning up old health records: {e}")
            return 0
    
    async def get_health_status_tracking_metrics(self, db: Session | AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive health status tracking metrics"""
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all forwarders health tracking data
            tracking_data = await forwarder_service.get_all_forwarders_health_tracking()
            
            # Calculate additional metrics
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get health check frequency metrics
            if hasattr(db, 'execute'):  # AsyncSession
                from sqlalchemy import func
                result = await db.execute(
                    select(
                        func.count(ForwarderHealth.id).label('total_checks'),
                        func.count(func.distinct(ForwarderHealth.forwarder_id)).label('forwarders_checked'),
                        func.avg(ForwarderHealth.response_time).label('avg_response_time')
                    ).filter(ForwarderHealth.checked_at >= since)
                )
                metrics = result.first()
            else:
                from ..models.dns import ForwarderHealth
                metrics = db.query(
                    func.count(ForwarderHealth.id).label('total_checks'),
                    func.count(func.distinct(ForwarderHealth.forwarder_id)).label('forwarders_checked'),
                    func.avg(ForwarderHealth.response_time).label('avg_response_time')
                ).filter(ForwarderHealth.checked_at >= since).first()
            
            tracking_metrics = {
                **tracking_data,
                "period_metrics": {
                    "period_hours": hours,
                    "total_health_checks": metrics.total_checks if metrics else 0,
                    "forwarders_checked": metrics.forwarders_checked if metrics else 0,
                    "average_response_time": float(metrics.avg_response_time) if metrics and metrics.avg_response_time else None,
                    "checks_per_hour": (metrics.total_checks / hours) if metrics and metrics.total_checks else 0
                },
                "health_score": self._calculate_overall_health_score(tracking_data)
            }
            
            return tracking_metrics
            
        except Exception as e:
            self._logger.error(f"Error getting health status tracking metrics: {e}")
            return {
                "total_forwarders": 0,
                "health_enabled_count": 0,
                "status_summary": {"healthy": 0, "unhealthy": 0, "degraded": 0, "unknown": 0},
                "forwarder_tracking": [],
                "period_metrics": {"period_hours": hours, "total_health_checks": 0, "forwarders_checked": 0},
                "health_score": 0.0,
                "last_updated": datetime.utcnow(),
                "error": str(e)
            }
    
    def _calculate_overall_health_score(self, tracking_data: Dict[str, Any]) -> float:
        """Calculate an overall health score (0-100) based on forwarder health status"""
        status_summary = tracking_data.get("status_summary", {})
        total_with_health_check = tracking_data.get("health_enabled_count", 0)
        
        if total_with_health_check == 0:
            return 100.0  # No forwarders to monitor = perfect score
        
        # Weight different statuses
        healthy_weight = 1.0
        degraded_weight = 0.5
        unhealthy_weight = 0.0
        unknown_weight = 0.3  # Unknown gets some credit
        
        weighted_score = (
            status_summary.get("healthy", 0) * healthy_weight +
            status_summary.get("degraded", 0) * degraded_weight +
            status_summary.get("unhealthy", 0) * unhealthy_weight +
            status_summary.get("unknown", 0) * unknown_weight
        )
        
        return (weighted_score / total_with_health_check) * 100.0
    
    async def get_health_alerts_with_tracking(self, db: Session | AsyncSession) -> Dict[str, Any]:
        """Get health alerts with additional tracking information"""
        try:
            unhealthy_forwarders = await self.get_unhealthy_forwarders(db)
            forwarder_service = ForwarderService(db)
            
            enhanced_alerts = []
            
            for forwarder in unhealthy_forwarders:
                # Get health trends for context
                trends = await forwarder_service.get_health_status_trends(forwarder["id"], hours=24)
                
                alert = {
                    **forwarder,
                    "alert_severity": "critical" if forwarder["status"] == "unhealthy" else "warning",
                    "uptime_24h": trends.get("uptime_percentage", 0.0),
                    "recent_status_changes": len(trends.get("status_changes", [])),
                    "avg_response_time": trends.get("average_response_time"),
                    "total_checks_24h": trends.get("total_checks", 0)
                }
                
                enhanced_alerts.append(alert)
            
            return {
                "alerts": enhanced_alerts,
                "total_alerts": len(enhanced_alerts),
                "critical_alerts": len([a for a in enhanced_alerts if a["alert_severity"] == "critical"]),
                "warning_alerts": len([a for a in enhanced_alerts if a["alert_severity"] == "warning"]),
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            self._logger.error(f"Error getting health alerts with tracking: {e}")
            return {
                "alerts": [],
                "total_alerts": 0,
                "critical_alerts": 0,
                "warning_alerts": 0,
                "generated_at": datetime.utcnow(),
                "error": str(e)
            }
    
    def is_running(self) -> bool:
        """Check if the health monitoring service is running"""
        return self.running and (self._health_check_task is None or not self._health_check_task.done())


# Global health service instance
_health_service_instance = None

def get_health_service() -> HealthService:
    """Get the global health service instance"""
    global _health_service_instance
    if _health_service_instance is None:
        _health_service_instance = HealthService()
    return _health_service_instance