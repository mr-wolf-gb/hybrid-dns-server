"""
WebSocket Deployment Monitoring Service

This service provides production-grade monitoring for WebSocket system deployments,
including user adoption tracking, performance monitoring, and automatic alerting.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from ..core.logging_config import get_logger
from ..core.feature_flags import get_websocket_feature_flags
from ..websocket.router import get_websocket_router
from ..websocket.metrics import get_websocket_metrics
from ..websocket.health_monitor import get_websocket_health_monitor

logger = get_logger(__name__)


@dataclass
class DeploymentMetrics:
    """Metrics for deployment monitoring"""
    timestamp: datetime
    migration_mode: str
    rollout_percentage: int
    total_connections: int
    legacy_connections: int
    unified_connections: int
    routing_errors: int
    fallback_activations: int
    error_rate: float
    success_rate: float
    user_adoption_rate: float
    performance_score: float
    health_score: float


@dataclass
class AlertThresholds:
    """Thresholds for deployment alerts"""
    max_error_rate: float = 5.0
    min_success_rate: float = 95.0
    max_fallback_rate: float = 10.0
    min_user_adoption_rate: float = 80.0
    min_performance_score: float = 70.0
    min_health_score: float = 80.0
    consecutive_failures_threshold: int = 3


@dataclass
class DeploymentAlert:
    """Deployment alert information"""
    id: str
    severity: str  # critical, warning, info
    title: str
    message: str
    timestamp: datetime
    metrics: DeploymentMetrics
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class WebSocketDeploymentMonitoringService:
    """Service for monitoring WebSocket deployment in production"""
    
    def __init__(self):
        self.feature_flags = get_websocket_feature_flags()
        self.router = get_websocket_router()
        self.metrics = get_websocket_metrics()
        self.health_monitor = get_websocket_health_monitor()
        
        self.thresholds = AlertThresholds()
        self.metrics_history: List[DeploymentMetrics] = []
        self.active_alerts: Dict[str, DeploymentAlert] = {}
        self.alert_history: List[DeploymentAlert] = []
        
        self.monitoring_active = False
        self.consecutive_failures = 0
        
        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.metrics_retention_hours = 24
        self.alert_retention_days = 7
        
        # Initialize alerting service
        self.alerting_service = None
        self._initialize_alerting_service()
    
    def _initialize_alerting_service(self):
        """Initialize the alerting service"""
        try:
            from .websocket_alerting_service import get_websocket_alerting_service
            self.alerting_service = get_websocket_alerting_service()
        except Exception as e:
            logger.warning(f"Could not initialize alerting service: {e}")
            self.alerting_service = None
    
    async def start_monitoring(self):
        """Start continuous deployment monitoring"""
        if self.monitoring_active:
            logger.warning("Deployment monitoring is already active")
            return
        
        self.monitoring_active = True
        logger.info("Starting WebSocket deployment monitoring")
        
        try:
            while self.monitoring_active:
                await self._collect_and_analyze_metrics()
                await asyncio.sleep(self.monitoring_interval)
        except Exception as e:
            logger.error(f"Error in deployment monitoring loop: {e}")
        finally:
            self.monitoring_active = False
            logger.info("WebSocket deployment monitoring stopped")
    
    def stop_monitoring(self):
        """Stop deployment monitoring"""
        self.monitoring_active = False
        logger.info("Stopping WebSocket deployment monitoring")
    
    async def _collect_and_analyze_metrics(self):
        """Collect metrics and analyze for alerts"""
        try:
            # Collect current metrics
            metrics = await self._collect_deployment_metrics()
            self.metrics_history.append(metrics)
            
            # Clean up old metrics
            self._cleanup_old_metrics()
            
            # Analyze metrics for alerts
            await self._analyze_metrics_for_alerts(metrics)
            
            # Use alerting service if available
            if self.alerting_service:
                await self.alerting_service.evaluate_alerts(asdict(metrics))
            
            # Log metrics for debugging
            logger.debug(f"Deployment metrics: {asdict(metrics)}")
            
        except Exception as e:
            logger.error(f"Error collecting deployment metrics: {e}")
    
    async def _collect_deployment_metrics(self) -> DeploymentMetrics:
        """Collect current deployment metrics"""
        try:
            # Get feature flag statistics
            rollout_stats = self.feature_flags.get_rollout_statistics()
            
            # Get connection statistics
            connection_stats = self.router.get_connection_stats()
            router_stats = connection_stats.get("router_stats", {})
            
            # Get WebSocket metrics
            websocket_metrics = self.metrics.get_summary_stats()
            
            # Get health status
            health_status = self.health_monitor.get_health_status()
            
            # Calculate derived metrics
            legacy_connections = router_stats.get("legacy_connections", 0)
            unified_connections = router_stats.get("unified_connections", 0)
            total_connections = legacy_connections + unified_connections
            routing_errors = router_stats.get("routing_errors", 0)
            fallback_activations = router_stats.get("fallback_activations", 0)
            
            # Calculate rates
            error_rate = 0.0
            success_rate = 100.0
            user_adoption_rate = 0.0
            
            if total_connections > 0:
                error_rate = (routing_errors / total_connections) * 100
                success_rate = 100.0 - error_rate
                
                # User adoption rate based on rollout percentage and actual usage
                expected_unified = (rollout_stats["rollout_percentage"] / 100) * total_connections
                if expected_unified > 0:
                    user_adoption_rate = (unified_connections / expected_unified) * 100
                    user_adoption_rate = min(100.0, user_adoption_rate)
            
            # Calculate performance score (0-100)
            performance_score = self._calculate_performance_score(websocket_metrics)
            
            # Calculate health score (0-100)
            health_score = self._calculate_health_score(health_status)
            
            return DeploymentMetrics(
                timestamp=datetime.utcnow(),
                migration_mode=rollout_stats["migration_mode"],
                rollout_percentage=rollout_stats["rollout_percentage"],
                total_connections=total_connections,
                legacy_connections=legacy_connections,
                unified_connections=unified_connections,
                routing_errors=routing_errors,
                fallback_activations=fallback_activations,
                error_rate=error_rate,
                success_rate=success_rate,
                user_adoption_rate=user_adoption_rate,
                performance_score=performance_score,
                health_score=health_score
            )
            
        except Exception as e:
            logger.error(f"Error collecting deployment metrics: {e}")
            # Return default metrics on error
            return DeploymentMetrics(
                timestamp=datetime.utcnow(),
                migration_mode="error",
                rollout_percentage=0,
                total_connections=0,
                legacy_connections=0,
                unified_connections=0,
                routing_errors=0,
                fallback_activations=0,
                error_rate=0.0,
                success_rate=0.0,
                user_adoption_rate=0.0,
                performance_score=0.0,
                health_score=0.0
            )
    
    def _calculate_performance_score(self, websocket_metrics: Dict[str, Any]) -> float:
        """Calculate performance score based on WebSocket metrics"""
        try:
            score = 100.0
            
            # Deduct points for high error rates
            error_rate = websocket_metrics.get("error_rate", 0.0)
            if error_rate > 0.01:  # 1%
                score -= min(30, error_rate * 1000)  # Up to 30 points
            
            # Deduct points for high latency
            avg_latency = websocket_metrics.get("average_latency_ms", 0)
            if avg_latency > 100:  # 100ms
                score -= min(20, (avg_latency - 100) / 10)  # Up to 20 points
            
            # Deduct points for low throughput
            throughput = websocket_metrics.get("messages_per_second", 0)
            if throughput < 10:  # Less than 10 messages/second
                score -= min(15, (10 - throughput) * 1.5)  # Up to 15 points
            
            # Deduct points for memory issues
            memory_usage = websocket_metrics.get("memory_usage_mb", 0)
            if memory_usage > 500:  # More than 500MB
                score -= min(10, (memory_usage - 500) / 50)  # Up to 10 points
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 50.0  # Default middle score
    
    def _calculate_health_score(self, health_status: Dict[str, Any]) -> float:
        """Calculate health score based on health monitor status"""
        try:
            overall_status = health_status.get("overall_status", "unknown")
            active_alerts = health_status.get("active_alerts", 0)
            
            # Base score based on overall status
            if overall_status == "healthy":
                score = 100.0
            elif overall_status == "warning":
                score = 75.0
            elif overall_status == "critical":
                score = 25.0
            else:
                score = 50.0  # unknown
            
            # Deduct points for active alerts
            score -= min(25, active_alerts * 5)  # Up to 25 points
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 50.0  # Default middle score
    
    async def _analyze_metrics_for_alerts(self, metrics: DeploymentMetrics):
        """Analyze metrics and generate alerts if needed"""
        alerts_to_create = []
        
        # Check error rate threshold
        if metrics.error_rate > self.thresholds.max_error_rate:
            alerts_to_create.append({
                "id": "high_error_rate",
                "severity": "critical",
                "title": "High Error Rate Detected",
                "message": f"Error rate {metrics.error_rate:.1f}% exceeds threshold {self.thresholds.max_error_rate}%"
            })
        
        # Check success rate threshold
        if metrics.success_rate < self.thresholds.min_success_rate:
            alerts_to_create.append({
                "id": "low_success_rate",
                "severity": "critical",
                "title": "Low Success Rate Detected",
                "message": f"Success rate {metrics.success_rate:.1f}% below threshold {self.thresholds.min_success_rate}%"
            })
        
        # Check user adoption rate
        if metrics.user_adoption_rate < self.thresholds.min_user_adoption_rate and metrics.rollout_percentage > 0:
            alerts_to_create.append({
                "id": "low_adoption_rate",
                "severity": "warning",
                "title": "Low User Adoption Rate",
                "message": f"User adoption rate {metrics.user_adoption_rate:.1f}% below threshold {self.thresholds.min_user_adoption_rate}%"
            })
        
        # Check performance score
        if metrics.performance_score < self.thresholds.min_performance_score:
            alerts_to_create.append({
                "id": "low_performance_score",
                "severity": "warning",
                "title": "Low Performance Score",
                "message": f"Performance score {metrics.performance_score:.1f} below threshold {self.thresholds.min_performance_score}"
            })
        
        # Check health score
        if metrics.health_score < self.thresholds.min_health_score:
            alerts_to_create.append({
                "id": "low_health_score",
                "severity": "critical",
                "title": "Low Health Score",
                "message": f"Health score {metrics.health_score:.1f} below threshold {self.thresholds.min_health_score}"
            })
        
        # Create new alerts
        for alert_data in alerts_to_create:
            await self._create_alert(alert_data, metrics)
        
        # Check for resolved alerts
        await self._check_resolved_alerts(metrics)
        
        # Update consecutive failures counter
        if alerts_to_create:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
    
    async def _create_alert(self, alert_data: Dict[str, Any], metrics: DeploymentMetrics):
        """Create a new alert"""
        alert_id = alert_data["id"]
        
        # Check if alert already exists
        if alert_id in self.active_alerts:
            return
        
        alert = DeploymentAlert(
            id=alert_id,
            severity=alert_data["severity"],
            title=alert_data["title"],
            message=alert_data["message"],
            timestamp=datetime.utcnow(),
            metrics=metrics
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"Deployment alert created: {alert.title} - {alert.message}")
        
        # Send alert notification (implement based on your notification system)
        await self._send_alert_notification(alert)
    
    async def _check_resolved_alerts(self, metrics: DeploymentMetrics):
        """Check if any active alerts should be resolved"""
        alerts_to_resolve = []
        
        for alert_id, alert in self.active_alerts.items():
            should_resolve = False
            
            if alert_id == "high_error_rate" and metrics.error_rate <= self.thresholds.max_error_rate:
                should_resolve = True
            elif alert_id == "low_success_rate" and metrics.success_rate >= self.thresholds.min_success_rate:
                should_resolve = True
            elif alert_id == "low_adoption_rate" and metrics.user_adoption_rate >= self.thresholds.min_user_adoption_rate:
                should_resolve = True
            elif alert_id == "low_performance_score" and metrics.performance_score >= self.thresholds.min_performance_score:
                should_resolve = True
            elif alert_id == "low_health_score" and metrics.health_score >= self.thresholds.min_health_score:
                should_resolve = True
            
            if should_resolve:
                alerts_to_resolve.append(alert_id)
        
        # Resolve alerts
        for alert_id in alerts_to_resolve:
            await self._resolve_alert(alert_id)
    
    async def _resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id not in self.active_alerts:
            return
        
        alert = self.active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        
        del self.active_alerts[alert_id]
        
        logger.info(f"Deployment alert resolved: {alert.title}")
        
        # Send resolution notification
        await self._send_alert_resolution_notification(alert)
    
    async def _send_alert_notification(self, alert: DeploymentAlert):
        """Send alert notification through multiple channels"""
        try:
            # Log the alert
            logger.warning(f"DEPLOYMENT ALERT: {alert.severity.upper()} - {alert.title}: {alert.message}")
            
            # Send to configured notification channels
            await self._send_webhook_notification(alert)
            await self._send_email_notification(alert)
            await self._log_alert_to_file(alert)
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    async def _send_alert_resolution_notification(self, alert: DeploymentAlert):
        """Send alert resolution notification"""
        try:
            logger.info(f"DEPLOYMENT ALERT RESOLVED: {alert.title}")
            
            # Send resolution notifications
            await self._send_webhook_resolution(alert)
            await self._send_email_resolution(alert)
            await self._log_resolution_to_file(alert)
            
        except Exception as e:
            logger.error(f"Error sending alert resolution notification: {e}")
    
    async def _send_webhook_notification(self, alert: DeploymentAlert):
        """Send webhook notification for alert"""
        try:
            webhook_url = getattr(self.feature_flags.settings, 'WEBSOCKET_ALERT_WEBHOOK_URL', None)
            if not webhook_url:
                return
            
            import aiohttp
            
            payload = {
                "alert_id": alert.id,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metrics": asdict(alert.metrics),
                "deployment_info": {
                    "migration_mode": alert.metrics.migration_mode,
                    "rollout_percentage": alert.metrics.rollout_percentage,
                    "total_connections": alert.metrics.total_connections
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent for alert {alert.id}")
                    else:
                        logger.warning(f"Webhook notification failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    async def _send_email_notification(self, alert: DeploymentAlert):
        """Send email notification for alert"""
        try:
            # This would integrate with your email system
            # For now, just log the email content
            email_content = f"""
WebSocket Deployment Alert

Severity: {alert.severity.upper()}
Title: {alert.title}
Message: {alert.message}
Time: {alert.timestamp.isoformat()}

Deployment Status:
- Migration Mode: {alert.metrics.migration_mode}
- Rollout Percentage: {alert.metrics.rollout_percentage}%
- Total Connections: {alert.metrics.total_connections}
- Error Rate: {alert.metrics.error_rate:.2f}%
- Success Rate: {alert.metrics.success_rate:.2f}%

Please investigate immediately if this is a critical alert.
"""
            
            logger.info(f"Email notification content prepared for alert {alert.id}")
            # TODO: Implement actual email sending using SMTP or email service
            
        except Exception as e:
            logger.error(f"Error preparing email notification: {e}")
    
    async def _send_webhook_resolution(self, alert: DeploymentAlert):
        """Send webhook notification for alert resolution"""
        try:
            webhook_url = self.feature_flags.settings.WEBSOCKET_ALERT_WEBHOOK_URL
            if not webhook_url:
                return
            
            import aiohttp
            
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "status": "resolved",
                "resolution_time_minutes": (
                    (alert.resolved_at - alert.timestamp).total_seconds() / 60
                    if alert.resolved_at else None
                )
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{webhook_url}/resolved",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook resolution notification sent for alert {alert.id}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook resolution: {e}")
    
    async def _send_email_resolution(self, alert: DeploymentAlert):
        """Send email notification for alert resolution"""
        try:
            resolution_time = (
                (alert.resolved_at - alert.timestamp).total_seconds() / 60
                if alert.resolved_at else 0
            )
            
            email_content = f"""
WebSocket Deployment Alert Resolved

Alert: {alert.title}
Resolved At: {alert.resolved_at.isoformat() if alert.resolved_at else 'Unknown'}
Resolution Time: {resolution_time:.1f} minutes

The deployment alert has been automatically resolved.
"""
            
            logger.info(f"Email resolution notification prepared for alert {alert.id}")
            # TODO: Implement actual email sending
            
        except Exception as e:
            logger.error(f"Error preparing email resolution: {e}")
    
    async def _log_alert_to_file(self, alert: DeploymentAlert):
        """Log alert to dedicated alert file"""
        try:
            alert_log_file = Path("websocket_deployment_alerts.log")
            
            alert_entry = {
                "timestamp": alert.timestamp.isoformat(),
                "alert_id": alert.id,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "metrics": asdict(alert.metrics)
            }
            
            with open(alert_log_file, "a") as f:
                f.write(json.dumps(alert_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging alert to file: {e}")
    
    async def _log_resolution_to_file(self, alert: DeploymentAlert):
        """Log alert resolution to file"""
        try:
            alert_log_file = Path("websocket_deployment_alerts.log")
            
            resolution_entry = {
                "timestamp": alert.resolved_at.isoformat() if alert.resolved_at else datetime.utcnow().isoformat(),
                "alert_id": alert.id,
                "status": "resolved",
                "resolution_time_minutes": (
                    (alert.resolved_at - alert.timestamp).total_seconds() / 60
                    if alert.resolved_at else 0
                )
            }
            
            with open(alert_log_file, "a") as f:
                f.write(json.dumps(resolution_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging resolution to file: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove old metrics to prevent memory buildup"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        # Clean up old alert history
        alert_cutoff_time = datetime.utcnow() - timedelta(days=self.alert_retention_days)
        self.alert_history = [
            a for a in self.alert_history 
            if a.timestamp >= alert_cutoff_time
        ]
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        
        return {
            "status": "monitoring",
            "latest_metrics": asdict(latest_metrics),
            "active_alerts": [asdict(alert) for alert in self.active_alerts.values()],
            "consecutive_failures": self.consecutive_failures,
            "monitoring_active": self.monitoring_active,
            "thresholds": asdict(self.thresholds),
            "metrics_count": len(self.metrics_history),
            "alert_history_count": len(self.alert_history)
        }
    
    def get_deployment_report(self, hours: int = 1) -> Dict[str, Any]:
        """Generate deployment report for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate summary statistics
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
        avg_adoption_rate = sum(m.user_adoption_rate for m in recent_metrics) / len(recent_metrics)
        avg_performance_score = sum(m.performance_score for m in recent_metrics) / len(recent_metrics)
        avg_health_score = sum(m.health_score for m in recent_metrics) / len(recent_metrics)
        
        max_connections = max(m.total_connections for m in recent_metrics)
        total_routing_errors = sum(m.routing_errors for m in recent_metrics)
        total_fallback_activations = sum(m.fallback_activations for m in recent_metrics)
        
        # Get alerts in the period
        period_alerts = [
            a for a in self.alert_history 
            if a.timestamp >= cutoff_time
        ]
        
        # Calculate deployment health score
        deployment_health = self._calculate_deployment_health(recent_metrics)
        
        # Generate recommendations
        recommendations = self._generate_deployment_recommendations(recent_metrics, period_alerts)
        
        return {
            "period": {
                "start_time": cutoff_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_hours": hours,
                "sample_count": len(recent_metrics)
            },
            "summary_metrics": {
                "average_error_rate": round(avg_error_rate, 2),
                "average_success_rate": round(avg_success_rate, 2),
                "average_adoption_rate": round(avg_adoption_rate, 2),
                "average_performance_score": round(avg_performance_score, 2),
                "average_health_score": round(avg_health_score, 2),
                "max_concurrent_connections": max_connections,
                "total_routing_errors": total_routing_errors,
                "total_fallback_activations": total_fallback_activations
            },
            "alerts": {
                "total_alerts": len(period_alerts),
                "critical_alerts": len([a for a in period_alerts if a.severity == "critical"]),
                "warning_alerts": len([a for a in period_alerts if a.severity == "warning"]),
                "resolved_alerts": len([a for a in period_alerts if a.resolved])
            },
            "current_status": {
                "active_alerts": len(self.active_alerts),
                "consecutive_failures": self.consecutive_failures,
                "latest_metrics": asdict(recent_metrics[-1]) if recent_metrics else None
            },
            "deployment_health": deployment_health,
            "recommendations": recommendations,
            "performance_trends": self._calculate_performance_trends(recent_metrics),
            "resource_usage": self._get_resource_usage_summary()
        }
    
    def _calculate_deployment_health(self, metrics: List[DeploymentMetrics]) -> Dict[str, Any]:
        """Calculate overall deployment health score"""
        if not metrics:
            return {"status": "unknown", "score": 0, "factors": []}
        
        latest = metrics[-1]
        health_score = 100.0
        factors = []
        
        # Error rate factor (30% weight)
        if latest.error_rate > 5.0:
            deduction = min(30, latest.error_rate * 3)
            health_score -= deduction
            factors.append(f"High error rate: -{deduction:.1f} points")
        elif latest.error_rate > 2.0:
            deduction = latest.error_rate * 2
            health_score -= deduction
            factors.append(f"Elevated error rate: -{deduction:.1f} points")
        
        # Success rate factor (25% weight)
        if latest.success_rate < 95.0:
            deduction = (95.0 - latest.success_rate) * 2
            health_score -= deduction
            factors.append(f"Low success rate: -{deduction:.1f} points")
        
        # User adoption factor (20% weight)
        if latest.rollout_percentage > 0 and latest.user_adoption_rate < 80.0:
            deduction = (80.0 - latest.user_adoption_rate) * 0.25
            health_score -= deduction
            factors.append(f"Low user adoption: -{deduction:.1f} points")
        
        # Performance score factor (15% weight)
        if latest.performance_score < 70.0:
            deduction = (70.0 - latest.performance_score) * 0.2
            health_score -= deduction
            factors.append(f"Low performance: -{deduction:.1f} points")
        
        # Health score factor (10% weight)
        if latest.health_score < 80.0:
            deduction = (80.0 - latest.health_score) * 0.1
            health_score -= deduction
            factors.append(f"System health issues: -{deduction:.1f} points")
        
        health_score = max(0.0, min(100.0, health_score))
        
        # Determine status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 60:
            status = "fair"
        elif health_score >= 40:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "status": status,
            "score": round(health_score, 1),
            "factors": factors,
            "trend": self._calculate_health_trend(metrics)
        }
    
    def _calculate_health_trend(self, metrics: List[DeploymentMetrics]) -> str:
        """Calculate health trend over time"""
        if len(metrics) < 4:
            return "insufficient_data"
        
        # Compare first and last quarters
        quarter_size = max(1, len(metrics) // 4)
        first_quarter = metrics[:quarter_size]
        last_quarter = metrics[-quarter_size:]
        
        first_avg_success = sum(m.success_rate for m in first_quarter) / len(first_quarter)
        last_avg_success = sum(m.success_rate for m in last_quarter) / len(last_quarter)
        
        first_avg_error = sum(m.error_rate for m in first_quarter) / len(first_quarter)
        last_avg_error = sum(m.error_rate for m in last_quarter) / len(last_quarter)
        
        # Determine trend based on success rate and error rate changes
        success_improvement = last_avg_success - first_avg_success
        error_improvement = first_avg_error - last_avg_error  # Lower error is better
        
        if success_improvement > 2 and error_improvement > 1:
            return "improving"
        elif success_improvement < -2 or error_improvement < -1:
            return "degrading"
        else:
            return "stable"
    
    def _generate_deployment_recommendations(self, metrics: List[DeploymentMetrics], alerts: List[DeploymentAlert]) -> List[str]:
        """Generate deployment recommendations based on metrics and alerts"""
        recommendations = []
        
        if not metrics:
            return ["Insufficient data to generate recommendations"]
        
        latest = metrics[-1]
        
        # Error rate recommendations
        if latest.error_rate > 5.0:
            recommendations.append("CRITICAL: Error rate exceeds 5% - consider immediate rollback")
            recommendations.append("Investigate connection failures and routing issues")
        elif latest.error_rate > 2.0:
            recommendations.append("WARNING: Elevated error rate - monitor closely")
            recommendations.append("Review WebSocket connection logs for patterns")
        
        # User adoption recommendations
        if latest.rollout_percentage > 0:
            expected_unified = latest.rollout_percentage
            actual_unified = (latest.unified_connections / max(1, latest.total_connections)) * 100
            
            if actual_unified < expected_unified * 0.7:
                recommendations.append(f"User adoption ({actual_unified:.1f}%) below expected ({expected_unified}%)")
                recommendations.append("Check feature flag assignment and user migration logic")
        
        # Performance recommendations
        if latest.performance_score < 70:
            recommendations.append("Performance score below threshold - investigate system bottlenecks")
            recommendations.append("Monitor memory usage, CPU utilization, and network latency")
        
        # Alert-based recommendations
        critical_alerts = [a for a in alerts if a.severity == "critical" and not a.resolved]
        if len(critical_alerts) > 2:
            recommendations.append("Multiple unresolved critical alerts - consider rollback")
        
        # Consecutive failures
        if self.consecutive_failures >= 2:
            recommendations.append("System showing instability - pause rollout and investigate")
        
        # Fallback rate recommendations
        if latest.total_connections > 0:
            fallback_rate = (latest.fallback_activations / latest.total_connections) * 100
            if fallback_rate > 10:
                recommendations.append("High fallback rate indicates unified system issues")
                recommendations.append("Review unified WebSocket implementation for bugs")
        
        # Positive recommendations
        if not recommendations and latest.error_rate < 1.0 and latest.success_rate > 98.0:
            recommendations.append("System performing well - consider increasing rollout percentage")
            recommendations.append("Monitor for sustained performance before full deployment")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _calculate_performance_trends(self, metrics: List[DeploymentMetrics]) -> Dict[str, Any]:
        """Calculate performance trends over the monitoring period"""
        if len(metrics) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate trends for key metrics
        timestamps = [m.timestamp for m in metrics]
        error_rates = [m.error_rate for m in metrics]
        success_rates = [m.success_rate for m in metrics]
        adoption_rates = [m.user_adoption_rate for m in metrics]
        
        return {
            "error_rate_trend": self._calculate_metric_trend(error_rates),
            "success_rate_trend": self._calculate_metric_trend(success_rates),
            "adoption_rate_trend": self._calculate_metric_trend(adoption_rates),
            "connection_growth": {
                "start_connections": metrics[0].total_connections,
                "end_connections": metrics[-1].total_connections,
                "peak_connections": max(m.total_connections for m in metrics)
            },
            "stability_indicators": {
                "error_rate_variance": self._calculate_variance(error_rates),
                "success_rate_variance": self._calculate_variance(success_rates),
                "consistent_performance": self._assess_consistency(metrics)
            }
        }
    
    def _calculate_metric_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend for a specific metric"""
        if len(values) < 2:
            return {"trend": "unknown", "change": 0}
        
        start_avg = sum(values[:len(values)//3]) / max(1, len(values)//3)
        end_avg = sum(values[-len(values)//3:]) / max(1, len(values)//3)
        
        change = end_avg - start_avg
        change_percent = (change / max(0.01, start_avg)) * 100
        
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        return {
            "trend": trend,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "start_value": round(start_avg, 2),
            "end_value": round(end_avg, 2)
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a metric"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return round(variance, 4)
    
    def _assess_consistency(self, metrics: List[DeploymentMetrics]) -> Dict[str, Any]:
        """Assess consistency of performance metrics"""
        if len(metrics) < 3:
            return {"status": "insufficient_data"}
        
        # Check for consistent performance (low variance in key metrics)
        error_rates = [m.error_rate for m in metrics]
        success_rates = [m.success_rate for m in metrics]
        
        error_variance = self._calculate_variance(error_rates)
        success_variance = self._calculate_variance(success_rates)
        
        # Determine consistency level
        if error_variance < 1.0 and success_variance < 4.0:
            consistency = "high"
        elif error_variance < 4.0 and success_variance < 16.0:
            consistency = "moderate"
        else:
            consistency = "low"
        
        return {
            "status": consistency,
            "error_rate_variance": error_variance,
            "success_rate_variance": success_variance,
            "performance_stability": "stable" if consistency == "high" else "variable"
        }
    
    def _get_resource_usage_summary(self) -> Dict[str, Any]:
        """Get current resource usage summary"""
        try:
            import psutil
            
            # Get current process info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # System info
            system_memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "process_memory_percent": round(process.memory_percent(), 2),
                "system_memory_percent": round(system_memory.percent, 2),
                "system_cpu_percent": round(cpu_percent, 2),
                "available_memory_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.debug(f"Could not get resource usage: {e}")
            return {"error": "Resource monitoring not available"}
    
    def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """Update alert thresholds"""
        try:
            for key, value in new_thresholds.items():
                if hasattr(self.thresholds, key):
                    setattr(self.thresholds, key, value)
                    logger.info(f"Updated threshold {key} to {value}")
                else:
                    logger.warning(f"Unknown threshold: {key}")
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")


# Global instance
_deployment_monitoring_service = None


def get_deployment_monitoring_service() -> WebSocketDeploymentMonitoringService:
    """Get the global deployment monitoring service instance"""
    global _deployment_monitoring_service
    if _deployment_monitoring_service is None:
        _deployment_monitoring_service = WebSocketDeploymentMonitoringService()
    return _deployment_monitoring_service