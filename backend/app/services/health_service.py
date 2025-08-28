"""
Health monitoring service for DNS forwarders and system health with event broadcasting
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..core.config import get_settings
from ..core.database import get_database_session
from ..core.logging_config import get_health_logger
from ..models.dns import Forwarder, ForwarderHealth
from .forwarder_service import ForwarderService
from .enhanced_event_service import get_enhanced_event_service
from ..websocket.event_types import EventType, EventPriority, EventCategory, EventSeverity, EventMetadata, create_event


class HealthService:
    """Health monitoring for DNS forwarders and system components with event broadcasting"""
    
    def __init__(self):
        self.running = False
        self._health_check_task = None
        self._logger = get_health_logger()
        self._performance_metrics = {}
        self.event_service = get_enhanced_event_service()
        self._alert_thresholds = {
            "response_time_warning": 200,  # ms
            "response_time_critical": 500,  # ms
            "failure_rate_warning": 0.1,  # 10%
            "failure_rate_critical": 0.3,  # 30%
            "consecutive_failures_alert": 3
        }
    
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
                    status_changes = []
                    
                    for forwarder in forwarders:
                        if forwarder.health_check_enabled:
                            try:
                                # Get current health status before check
                                current_health = await forwarder_service.get_current_health_status(forwarder.id)
                                old_status = current_health.get("overall_status", "unknown")
                                await forwarder_service.perform_health_check(forwarder.id)
                                
                                # Check if status changed
                                updated_health = await forwarder_service.get_current_health_status(forwarder.id)
                                new_status = updated_health.get("overall_status", "unknown")
                                if new_status != old_status:
                                    status_changes.append({
                                        "forwarder_id": forwarder.id,
                                        "old_status": old_status,
                                        "new_status": new_status
                                    })
                                
                                health_check_count += 1
                            except Exception as e:
                                self._logger.error(f"Error checking health for forwarder {forwarder.name}: {e}")
                    
                    # Broadcast status changes via WebSocket
                    if status_changes:
                        from ..websocket.unified_manager import get_unified_websocket_manager
                        websocket_manager = get_unified_websocket_manager()
                        
                        for change in status_changes:
                            await websocket_manager.broadcast_forwarder_status_change(
                                change["forwarder_id"],
                                change["old_status"],
                                change["new_status"]
                            )
                    
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
    
    async def get_health_history_data(self, db: Session | AsyncSession, forwarder_id: Optional[int] = None, hours: int = 24) -> Dict[str, Any]:
        """Get health history data for charts"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            if hasattr(db, 'execute'):  # AsyncSession
                if forwarder_id:
                    # Get history for specific forwarder
                    result = await db.execute(
                        select(
                            ForwarderHealth.checked_at,
                            ForwarderHealth.status,
                            ForwarderHealth.response_time,
                            ForwarderHealth.server_ip,
                            ForwarderHealth.error_message
                        ).filter(
                            ForwarderHealth.forwarder_id == forwarder_id,
                            ForwarderHealth.checked_at >= since
                        ).order_by(ForwarderHealth.checked_at)
                    )
                    health_records = result.fetchall()
                else:
                    # Get aggregated history for all forwarders
                    result = await db.execute(
                        select(
                            ForwarderHealth.checked_at,
                            func.count(ForwarderHealth.id).label('total_checks'),
                            func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('healthy_checks'),
                            func.avg(ForwarderHealth.response_time).label('avg_response_time'),
                            func.min(ForwarderHealth.response_time).label('min_response_time'),
                            func.max(ForwarderHealth.response_time).label('max_response_time')
                        ).filter(
                            ForwarderHealth.checked_at >= since
                        ).group_by(
                            func.date_trunc('minute', ForwarderHealth.checked_at)
                        ).order_by(ForwarderHealth.checked_at)
                    )
                    health_records = result.fetchall()
            else:
                # Regular Session
                if forwarder_id:
                    health_records = db.query(ForwarderHealth).filter(
                        ForwarderHealth.forwarder_id == forwarder_id,
                        ForwarderHealth.checked_at >= since
                    ).order_by(ForwarderHealth.checked_at).all()
                else:
                    from sqlalchemy import func
                    health_records = db.query(
                        ForwarderHealth.checked_at,
                        func.count(ForwarderHealth.id).label('total_checks'),
                        func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('healthy_checks'),
                        func.avg(ForwarderHealth.response_time).label('avg_response_time'),
                        func.min(ForwarderHealth.response_time).label('min_response_time'),
                        func.max(ForwarderHealth.response_time).label('max_response_time')
                    ).filter(
                        ForwarderHealth.checked_at >= since
                    ).group_by(
                        func.date_trunc('minute', ForwarderHealth.checked_at)
                    ).order_by(ForwarderHealth.checked_at).all()
            
            # Process data for charts
            chart_data = []
            if forwarder_id:
                # Individual forwarder data
                for record in health_records:
                    chart_data.append({
                        "timestamp": record.checked_at.isoformat(),
                        "is_healthy": record.status == "healthy",
                        "status": record.status,
                        "response_time": record.response_time,
                        "server_ip": record.server_ip,
                        "error_message": record.error_message
                    })
            else:
                # Aggregated data
                for record in health_records:
                    success_rate = (record.healthy_checks / record.total_checks * 100) if record.total_checks > 0 else 0
                    chart_data.append({
                        "timestamp": record.checked_at.isoformat(),
                        "total_checks": record.total_checks,
                        "healthy_checks": record.healthy_checks,
                        "success_rate": success_rate,
                        "avg_response_time": float(record.avg_response_time) if record.avg_response_time else None,
                        "min_response_time": float(record.min_response_time) if record.min_response_time else None,
                        "max_response_time": float(record.max_response_time) if record.max_response_time else None
                    })
            
            return {
                "forwarder_id": forwarder_id,
                "period_hours": hours,
                "data_points": len(chart_data),
                "chart_data": chart_data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self._logger.error(f"Error getting health history data: {e}")
            return {
                "forwarder_id": forwarder_id,
                "period_hours": hours,
                "data_points": 0,
                "chart_data": [],
                "generated_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def get_performance_metrics(self, db: Session | AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            if hasattr(db, 'execute'):  # AsyncSession
                # Get overall performance metrics
                result = await db.execute(
                    select(
                        func.count(ForwarderHealth.id).label('total_checks'),
                        func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('successful_checks'),
                        func.avg(ForwarderHealth.response_time).label('avg_response_time'),
                        func.percentile_cont(0.5).within_group(ForwarderHealth.response_time).label('median_response_time'),
                        func.percentile_cont(0.95).within_group(ForwarderHealth.response_time).label('p95_response_time'),
                        func.percentile_cont(0.99).within_group(ForwarderHealth.response_time).label('p99_response_time'),
                        func.min(ForwarderHealth.response_time).label('min_response_time'),
                        func.max(ForwarderHealth.response_time).label('max_response_time')
                    ).filter(
                        ForwarderHealth.checked_at >= since,
                        ForwarderHealth.response_time.isnot(None)
                    )
                )
                metrics = result.first()
                
                # Get per-forwarder performance
                forwarder_result = await db.execute(
                    select(
                        ForwarderHealth.forwarder_id,
                        func.count(ForwarderHealth.id).label('checks'),
                        func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('successful'),
                        func.avg(ForwarderHealth.response_time).label('avg_response_time')
                    ).filter(
                        ForwarderHealth.checked_at >= since
                    ).group_by(ForwarderHealth.forwarder_id)
                )
                forwarder_metrics = forwarder_result.fetchall()
            else:
                # Regular Session
                from sqlalchemy import func
                metrics = db.query(
                    func.count(ForwarderHealth.id).label('total_checks'),
                    func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('successful_checks'),
                    func.avg(ForwarderHealth.response_time).label('avg_response_time'),
                    func.min(ForwarderHealth.response_time).label('min_response_time'),
                    func.max(ForwarderHealth.response_time).label('max_response_time')
                ).filter(
                    ForwarderHealth.checked_at >= since,
                    ForwarderHealth.response_time.isnot(None)
                ).first()
                
                forwarder_metrics = db.query(
                    ForwarderHealth.forwarder_id,
                    func.count(ForwarderHealth.id).label('checks'),
                    func.sum(func.case((ForwarderHealth.status == 'healthy', 1), else_=0)).label('successful'),
                    func.avg(ForwarderHealth.response_time).label('avg_response_time')
                ).filter(
                    ForwarderHealth.checked_at >= since
                ).group_by(ForwarderHealth.forwarder_id).all()
            
            # Calculate overall metrics
            total_checks = metrics.total_checks if metrics else 0
            successful_checks = metrics.successful_checks if metrics else 0
            success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            
            performance_data = {
                "period_hours": hours,
                "overall_metrics": {
                    "total_checks": total_checks,
                    "successful_checks": successful_checks,
                    "success_rate": success_rate,
                    "failure_rate": 100 - success_rate,
                    "avg_response_time": float(metrics.avg_response_time) if metrics and metrics.avg_response_time else None,
                    "min_response_time": float(metrics.min_response_time) if metrics and metrics.min_response_time else None,
                    "max_response_time": float(metrics.max_response_time) if metrics and metrics.max_response_time else None,
                },
                "forwarder_metrics": [],
                "performance_grade": self._calculate_performance_grade(success_rate, metrics.avg_response_time if metrics else None),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Add percentile data if available
            if hasattr(metrics, 'median_response_time') and metrics:
                performance_data["overall_metrics"].update({
                    "median_response_time": float(metrics.median_response_time) if metrics.median_response_time else None,
                    "p95_response_time": float(metrics.p95_response_time) if metrics.p95_response_time else None,
                    "p99_response_time": float(metrics.p99_response_time) if metrics.p99_response_time else None,
                })
            
            # Process per-forwarder metrics
            for fm in forwarder_metrics:
                forwarder_success_rate = (fm.successful / fm.checks * 100) if fm.checks > 0 else 0
                performance_data["forwarder_metrics"].append({
                    "forwarder_id": fm.forwarder_id,
                    "total_checks": fm.checks,
                    "successful_checks": fm.successful,
                    "success_rate": forwarder_success_rate,
                    "avg_response_time": float(fm.avg_response_time) if fm.avg_response_time else None,
                    "performance_grade": self._calculate_performance_grade(forwarder_success_rate, fm.avg_response_time)
                })
            
            return performance_data
            
        except Exception as e:
            self._logger.error(f"Error getting performance metrics: {e}")
            return {
                "period_hours": hours,
                "overall_metrics": {},
                "forwarder_metrics": [],
                "performance_grade": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def _calculate_performance_grade(self, success_rate: float, avg_response_time: Optional[float]) -> str:
        """Calculate a performance grade based on success rate and response time"""
        if success_rate >= 99 and (avg_response_time is None or avg_response_time < 50):
            return "excellent"
        elif success_rate >= 95 and (avg_response_time is None or avg_response_time < 100):
            return "good"
        elif success_rate >= 90 and (avg_response_time is None or avg_response_time < 200):
            return "fair"
        elif success_rate >= 80:
            return "poor"
        else:
            return "critical"
    
    async def generate_health_alerts(self, db: Session | AsyncSession) -> List[Dict[str, Any]]:
        """Generate health alerts based on current status and thresholds"""
        try:
            alerts = []
            
            # Get unhealthy forwarders
            unhealthy_forwarders = await self.get_unhealthy_forwarders(db)
            
            for forwarder in unhealthy_forwarders:
                alert_level = "critical" if forwarder["status"] == "unhealthy" else "warning"
                
                # Check for consecutive failures
                consecutive_failures = await self._get_consecutive_failures(db, forwarder["id"])
                
                alert = {
                    "id": f"health_{forwarder['id']}_{int(datetime.utcnow().timestamp())}",
                    "type": "health_status",
                    "level": alert_level,
                    "forwarder_id": forwarder["id"],
                    "forwarder_name": forwarder["name"],
                    "message": f"Forwarder '{forwarder['name']}' is {forwarder['status']}",
                    "details": {
                        "status": forwarder["status"],
                        "healthy_servers": forwarder["healthy_servers"],
                        "total_servers": forwarder["total_servers"],
                        "consecutive_failures": consecutive_failures,
                        "last_checked": forwarder["last_checked"]
                    },
                    "created_at": datetime.utcnow().isoformat(),
                    "acknowledged": False
                }
                
                # Add severity based on consecutive failures
                if consecutive_failures >= self._alert_thresholds["consecutive_failures_alert"]:
                    alert["level"] = "critical"
                    alert["message"] += f" ({consecutive_failures} consecutive failures)"
                
                alerts.append(alert)
            
            # Check for performance alerts
            performance_metrics = await self.get_performance_metrics(db, hours=1)  # Last hour
            overall_metrics = performance_metrics.get("overall_metrics", {})
            
            # Response time alerts
            avg_response_time = overall_metrics.get("avg_response_time")
            if avg_response_time:
                if avg_response_time >= self._alert_thresholds["response_time_critical"]:
                    alerts.append({
                        "id": f"performance_response_time_{int(datetime.utcnow().timestamp())}",
                        "type": "performance",
                        "level": "critical",
                        "message": f"Average response time is critically high: {avg_response_time:.1f}ms",
                        "details": {
                            "metric": "response_time",
                            "value": avg_response_time,
                            "threshold": self._alert_thresholds["response_time_critical"]
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "acknowledged": False
                    })
                elif avg_response_time >= self._alert_thresholds["response_time_warning"]:
                    alerts.append({
                        "id": f"performance_response_time_{int(datetime.utcnow().timestamp())}",
                        "type": "performance",
                        "level": "warning",
                        "message": f"Average response time is elevated: {avg_response_time:.1f}ms",
                        "details": {
                            "metric": "response_time",
                            "value": avg_response_time,
                            "threshold": self._alert_thresholds["response_time_warning"]
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "acknowledged": False
                    })
            
            # Failure rate alerts
            failure_rate = overall_metrics.get("failure_rate", 0) / 100  # Convert to decimal
            if failure_rate >= self._alert_thresholds["failure_rate_critical"]:
                alerts.append({
                    "id": f"performance_failure_rate_{int(datetime.utcnow().timestamp())}",
                    "type": "performance",
                    "level": "critical",
                    "message": f"Failure rate is critically high: {failure_rate*100:.1f}%",
                    "details": {
                        "metric": "failure_rate",
                        "value": failure_rate,
                        "threshold": self._alert_thresholds["failure_rate_critical"]
                    },
                    "created_at": datetime.utcnow().isoformat(),
                    "acknowledged": False
                })
            elif failure_rate >= self._alert_thresholds["failure_rate_warning"]:
                alerts.append({
                    "id": f"performance_failure_rate_{int(datetime.utcnow().timestamp())}",
                    "type": "performance",
                    "level": "warning",
                    "message": f"Failure rate is elevated: {failure_rate*100:.1f}%",
                    "details": {
                        "metric": "failure_rate",
                        "value": failure_rate,
                        "threshold": self._alert_thresholds["failure_rate_warning"]
                    },
                    "created_at": datetime.utcnow().isoformat(),
                    "acknowledged": False
                })
            
            return alerts
            
        except Exception as e:
            self._logger.error(f"Error generating health alerts: {e}")
            return []
    
    async def _get_consecutive_failures(self, db: Session | AsyncSession, forwarder_id: int) -> int:
        """Get the number of consecutive failures for a forwarder"""
        try:
            if hasattr(db, 'execute'):  # AsyncSession
                result = await db.execute(
                    select(ForwarderHealth.status)
                    .filter(ForwarderHealth.forwarder_id == forwarder_id)
                    .order_by(ForwarderHealth.checked_at.desc())
                    .limit(10)
                )
                recent_checks = [row.status == 'healthy' for row in result.fetchall()]
            else:
                recent_checks = [
                    check.status == 'healthy' for check in 
                    db.query(ForwarderHealth.status)
                    .filter(ForwarderHealth.forwarder_id == forwarder_id)
                    .order_by(ForwarderHealth.checked_at.desc())
                    .limit(10)
                    .all()
                ]
            
            consecutive_failures = 0
            for is_healthy in recent_checks:
                if not is_healthy:
                    consecutive_failures += 1
                else:
                    break
            
            return consecutive_failures
            
        except Exception as e:
            self._logger.error(f"Error getting consecutive failures: {e}")
            return 0

    async def _emit_health_event(self, event_type: EventType, forwarder_id: Optional[int], 
                                 action: str, details: Dict[str, Any]):
        """Helper method to emit health-related events"""
        try:
            # Create event data
            event_data = {
                "action": action,
                "forwarder_id": forwarder_id,
                "timestamp": datetime.utcnow().isoformat(),
                **details
            }
            
            # Determine event priority and severity based on health status
            health_status = details.get("status", "unknown")
            if health_status == "unhealthy":
                priority = EventPriority.HIGH
                severity = EventSeverity.ERROR
            elif health_status == "degraded":
                priority = EventPriority.NORMAL
                severity = EventSeverity.MEDIUM
            else:
                priority = EventPriority.LOW
                severity = EventSeverity.LOW
            
            # Emit the event directly with parameters
            await self.event_service.emit_event(
                event_type=event_type,
                data=event_data,
                priority=priority,
                severity=severity,
                metadata=EventMetadata(
                    source_service="health_service",
                    source_component=action,
                    custom_fields={
                        "forwarder_id": forwarder_id,
                        "health_status": health_status
                    }
                )
            )
            
        except Exception as e:
            self._logger.error(f"Failed to emit health event: {e}")
            # Don't raise the exception to avoid breaking the main operation
    
    async def _emit_system_metrics_event(self, metrics: Dict[str, Any]):
        """Helper method to emit system metrics events"""
        try:
            # Create event data
            event_data = {
                "action": "metrics_update",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics
            }
            
            # Determine priority based on metrics
            success_rate = metrics.get("success_rate", 100)
            avg_response_time = metrics.get("avg_response_time", 0)
            
            if success_rate < 90 or (avg_response_time and avg_response_time > 500):
                priority = EventPriority.HIGH
                severity = EventSeverity.ERROR
            elif success_rate < 95 or (avg_response_time and avg_response_time > 200):
                priority = EventPriority.NORMAL
                severity = EventSeverity.MEDIUM
            else:
                priority = EventPriority.LOW
                severity = EventSeverity.LOW
            
            # Emit the event directly with parameters
            await self.event_service.emit_event(
                event_type=EventType.SYSTEM_METRICS_UPDATED,
                data=event_data,
                priority=priority,
                severity=severity,
                metadata=EventMetadata(
                    source_service="health_service",
                    source_component="metrics_update",
                    custom_fields={
                        "success_rate": success_rate,
                        "avg_response_time": avg_response_time
                    }
                )
            )
            
        except Exception as e:
            self._logger.error(f"Failed to emit system metrics event: {e}")
            # Don't raise the exception to avoid breaking the main operation


# Global health service instance
_health_service_instance = None

def get_health_service() -> HealthService:
    """Get the global health service instance"""
    global _health_service_instance
    if _health_service_instance is None:
        _health_service_instance = HealthService()
    return _health_service_instance