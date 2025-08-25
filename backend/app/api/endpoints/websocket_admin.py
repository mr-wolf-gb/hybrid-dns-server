"""
Admin endpoints for WebSocket system management and feature flag control
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import asyncio

from ...core.auth_context import get_current_admin_user
from ...core.feature_flags import get_websocket_feature_flags, WebSocketMigrationMode
from ...websocket.router import get_websocket_router
from ...models.auth import User
from ...core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/websocket-admin", tags=["WebSocket Administration"])


class WebSocketMigrationConfig(BaseModel):
    """Configuration for WebSocket migration"""
    migration_mode: str = Field(..., description="Migration mode: disabled, testing, gradual, full")
    rollout_percentage: int = Field(0, ge=0, le=100, description="Percentage of users for gradual rollout")
    rollout_user_list: List[str] = Field(default_factory=list, description="Specific users for rollout")
    force_legacy_users: List[str] = Field(default_factory=list, description="Users forced to use legacy system")
    legacy_fallback: bool = Field(True, description="Enable fallback to legacy system on errors")


class UserMigrationRequest(BaseModel):
    """Request to migrate specific users"""
    user_ids: List[str] = Field(..., description="List of user IDs to migrate")
    to_unified: bool = Field(..., description="True to migrate to unified, False to legacy")


class WebSocketSystemInfo(BaseModel):
    """Information about WebSocket system for a user"""
    user_id: str
    use_unified: bool
    system: str
    migration_mode: str
    rollout_percentage: int
    in_explicit_list: bool
    forced_legacy: bool
    fallback_enabled: bool


@router.get("/status", response_model=Dict[str, Any])
async def get_websocket_system_status(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get current WebSocket system status and statistics
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        router_instance = get_websocket_router()
        
        return {
            "rollout_statistics": feature_flags.get_rollout_statistics(),
            "connection_statistics": router_instance.get_connection_stats(),
            "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket system status"
        )


@router.get("/user/{user_id}", response_model=WebSocketSystemInfo)
async def get_user_websocket_info(
    user_id: str,
    current_user: User = Depends(get_current_admin_user)
) -> WebSocketSystemInfo:
    """
    Get WebSocket system information for a specific user
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        info = feature_flags.get_websocket_system_info(user_id)
        
        return WebSocketSystemInfo(**info)
        
    except Exception as e:
        logger.error(f"Error getting WebSocket info for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get WebSocket info for user {user_id}"
        )


@router.post("/configure")
async def configure_websocket_migration(
    config: WebSocketMigrationConfig,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Configure WebSocket migration settings
    
    Requires admin privileges.
    """
    try:
        # Validate migration mode
        try:
            WebSocketMigrationMode(config.migration_mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid migration mode: {config.migration_mode}"
            )
        
        feature_flags = get_websocket_feature_flags()
        
        # Update settings (in a real implementation, this would update the configuration)
        # For now, we'll update the runtime configuration
        settings = feature_flags.settings
        
        # Note: In production, these would be persisted to configuration files or database
        settings.WEBSOCKET_MIGRATION_MODE = config.migration_mode.lower()
        settings.WEBSOCKET_ROLLOUT_PERCENTAGE = config.rollout_percentage
        settings.WEBSOCKET_ROLLOUT_USER_LIST = ",".join(config.rollout_user_list)
        settings.WEBSOCKET_FORCE_LEGACY_USERS = ",".join(config.force_legacy_users)
        settings.WEBSOCKET_LEGACY_FALLBACK = config.legacy_fallback
        
        # Clear user assignment cache to apply new settings
        feature_flags.clear_user_assignment_cache()
        
        logger.info(f"WebSocket migration configuration updated by admin {current_user.username}")
        
        return {
            "success": True,
            "message": "WebSocket migration configuration updated successfully",
            "configuration": {
                "migration_mode": config.migration_mode,
                "rollout_percentage": config.rollout_percentage,
                "rollout_users_count": len(config.rollout_user_list),
                "force_legacy_users_count": len(config.force_legacy_users),
                "legacy_fallback": config.legacy_fallback
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring WebSocket migration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure WebSocket migration"
        )


@router.post("/migrate-users")
async def migrate_users(
    request: UserMigrationRequest,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Migrate specific users between WebSocket systems
    
    Requires admin privileges.
    """
    try:
        router_instance = get_websocket_router()
        results = []
        
        for user_id in request.user_ids:
            result = await router_instance.migrate_user_connections(user_id, request.to_unified)
            results.append(result)
        
        successful_migrations = sum(1 for r in results if r["success"])
        total_connections_migrated = sum(r["connections_migrated"] for r in results)
        
        logger.info(f"Admin {current_user.username} migrated {successful_migrations} users "
                   f"to {'unified' if request.to_unified else 'legacy'} WebSocket system")
        
        return {
            "success": True,
            "message": f"Migration completed for {len(request.user_ids)} users",
            "summary": {
                "total_users": len(request.user_ids),
                "successful_migrations": successful_migrations,
                "failed_migrations": len(request.user_ids) - successful_migrations,
                "total_connections_migrated": total_connections_migrated,
                "target_system": "unified" if request.to_unified else "legacy"
            },
            "detailed_results": results
        }
        
    except Exception as e:
        logger.error(f"Error migrating users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to migrate users"
        )


@router.post("/clear-cache")
async def clear_user_assignment_cache(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Clear user assignment cache for WebSocket system selection
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        feature_flags.clear_user_assignment_cache(user_id)
        
        message = f"Cleared assignment cache for user {user_id}" if user_id else "Cleared all assignment cache"
        logger.info(f"Admin {current_user.username}: {message}")
        
        return {
            "success": True,
            "message": message,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error clearing user assignment cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear user assignment cache"
        )


@router.post("/emergency-rollback")
async def emergency_rollback_to_legacy(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Emergency rollback to legacy WebSocket system for all users
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        router_instance = get_websocket_router()
        
        # Set migration mode to disabled (legacy only)
        feature_flags.settings.WEBSOCKET_MIGRATION_MODE = "disabled"
        
        # Clear all user assignments
        feature_flags.clear_user_assignment_cache()
        
        # Get current connection stats before rollback
        stats_before = router_instance.get_connection_stats()
        unified_connections = stats_before.get("unified_stats", {}).get("total_connections", 0)
        
        logger.critical(f"EMERGENCY ROLLBACK initiated by admin {current_user.username}")
        
        return {
            "success": True,
            "message": "Emergency rollback to legacy WebSocket system completed",
            "rollback_info": {
                "initiated_by": current_user.username,
                "unified_connections_before": unified_connections,
                "migration_mode_set_to": "disabled",
                "cache_cleared": True
            },
            "next_steps": [
                "All new connections will use legacy system",
                "Existing unified connections will be disconnected on next reconnection",
                "Monitor system for stability",
                "Review logs for rollback cause"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error during emergency rollback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform emergency rollback"
        )


@router.get("/health")
async def websocket_system_health(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get health status of both WebSocket systems
    
    Requires admin privileges.
    """
    try:
        router_instance = get_websocket_router()
        stats = router_instance.get_connection_stats()
        
        # Analyze health
        router_stats = stats.get("router_stats", {})
        legacy_stats = stats.get("legacy_stats", {})
        unified_stats = stats.get("unified_stats", {})
        
        health_status = "healthy"
        issues = []
        
        # Check for routing errors
        routing_errors = router_stats.get("routing_errors", 0)
        if routing_errors > 10:  # Threshold for concern
            health_status = "degraded"
            issues.append(f"High routing errors: {routing_errors}")
        
        # Check fallback activations
        fallback_activations = router_stats.get("fallback_activations", 0)
        if fallback_activations > 5:  # Threshold for concern
            health_status = "degraded"
            issues.append(f"High fallback activations: {fallback_activations}")
        
        # Check connection distribution
        legacy_connections = router_stats.get("legacy_connections", 0)
        unified_connections = router_stats.get("unified_connections", 0)
        total_connections = legacy_connections + unified_connections
        
        return {
            "health_status": health_status,
            "issues": issues,
            "connection_summary": {
                "total_connections": total_connections,
                "legacy_connections": legacy_connections,
                "unified_connections": unified_connections,
                "legacy_percentage": (legacy_connections / total_connections * 100) if total_connections > 0 else 0,
                "unified_percentage": (unified_connections / total_connections * 100) if total_connections > 0 else 0
            },
            "error_summary": {
                "routing_errors": routing_errors,
                "fallback_activations": fallback_activations
            },
            "system_details": {
                "legacy_system": legacy_stats,
                "unified_system": unified_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket system health"
        )


@router.get("/production-monitoring")
async def get_production_monitoring_status(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get comprehensive production monitoring status for WebSocket deployment
    
    Requires admin privileges.
    """
    try:
        from ...services.websocket_deployment_monitoring import get_deployment_monitoring_service
        
        monitoring_service = get_deployment_monitoring_service()
        deployment_status = monitoring_service.get_deployment_status()
        
        # Get additional system metrics
        router_instance = get_websocket_router()
        connection_stats = router_instance.get_connection_stats()
        
        # Get WebSocket metrics if available
        try:
            from ...websocket.metrics import get_websocket_metrics
            websocket_metrics = get_websocket_metrics()
            metrics_summary = websocket_metrics.get_summary_stats()
        except Exception as e:
            logger.warning(f"Could not get WebSocket metrics: {e}")
            metrics_summary = {"error": "WebSocket metrics not available"}
        
        # Get health monitor status if available
        try:
            from ...websocket.health_monitor import get_websocket_health_monitor
            health_monitor = get_websocket_health_monitor()
            health_status = health_monitor.get_health_status()
        except Exception as e:
            logger.warning(f"Could not get health monitor status: {e}")
            health_status = {"error": "Health monitor not available"}
        
        return {
            "deployment_monitoring": deployment_status,
            "connection_statistics": connection_stats,
            "websocket_metrics": metrics_summary,
            "health_status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_active": monitoring_service.monitoring_active
        }
        
    except Exception as e:
        logger.error(f"Error getting production monitoring status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get production monitoring status"
        )


@router.get("/production-report")
async def get_production_deployment_report(
    hours: int = 1,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Generate comprehensive production deployment report
    
    Args:
        hours: Number of hours to include in the report (default: 1)
    
    Requires admin privileges.
    """
    try:
        from ...services.websocket_deployment_monitoring import get_deployment_monitoring_service
        
        monitoring_service = get_deployment_monitoring_service()
        report = monitoring_service.get_deployment_report(hours)
        
        return {
            "report": report,
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": current_user.username,
            "report_period_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Error generating production deployment report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate production deployment report"
        )


@router.post("/start-production-monitoring")
async def start_production_monitoring(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Start production deployment monitoring
    
    Requires admin privileges.
    """
    try:
        from ...services.websocket_deployment_monitoring import get_deployment_monitoring_service
        
        monitoring_service = get_deployment_monitoring_service()
        
        if monitoring_service.monitoring_active:
            return {
                "success": False,
                "message": "Production monitoring is already active",
                "monitoring_active": True
            }
        
        # Start monitoring in background task
        asyncio.create_task(monitoring_service.start_monitoring())
        
        logger.info(f"Production monitoring started by admin {current_user.username}")
        
        return {
            "success": True,
            "message": "Production monitoring started successfully",
            "started_by": current_user.username,
            "started_at": datetime.utcnow().isoformat(),
            "monitoring_active": True
        }
        
    except Exception as e:
        logger.error(f"Error starting production monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start production monitoring"
        )


@router.post("/stop-production-monitoring")
async def stop_production_monitoring(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Stop production deployment monitoring
    
    Requires admin privileges.
    """
    try:
        from ...services.websocket_deployment_monitoring import get_deployment_monitoring_service
        
        monitoring_service = get_deployment_monitoring_service()
        
        if not monitoring_service.monitoring_active:
            return {
                "success": False,
                "message": "Production monitoring is not active",
                "monitoring_active": False
            }
        
        monitoring_service.stop_monitoring()
        
        logger.info(f"Production monitoring stopped by admin {current_user.username}")
        
        return {
            "success": True,
            "message": "Production monitoring stopped successfully",
            "stopped_by": current_user.username,
            "stopped_at": datetime.utcnow().isoformat(),
            "monitoring_active": False
        }
        
    except Exception as e:
        logger.error(f"Error stopping production monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop production monitoring"
        )


class AlertThresholdUpdate(BaseModel):
    """Model for updating alert thresholds"""
    max_error_rate: Optional[float] = None
    min_success_rate: Optional[float] = None
    max_fallback_rate: Optional[float] = None
    min_user_adoption_rate: Optional[float] = None
    min_performance_score: Optional[float] = None
    min_health_score: Optional[float] = None
    consecutive_failures_threshold: Optional[int] = None


@router.post("/update-alert-thresholds")
async def update_alert_thresholds(
    thresholds: AlertThresholdUpdate,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Update alert thresholds for production monitoring
    
    Requires admin privileges.
    """
    try:
        from ...services.websocket_deployment_monitoring import get_deployment_monitoring_service
        
        monitoring_service = get_deployment_monitoring_service()
        
        # Convert to dictionary, excluding None values
        threshold_updates = {
            k: v for k, v in thresholds.dict().items() 
            if v is not None
        }
        
        if not threshold_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No threshold updates provided"
            )
        
        monitoring_service.update_thresholds(threshold_updates)
        
        logger.info(f"Alert thresholds updated by admin {current_user.username}: {threshold_updates}")
        
        return {
            "success": True,
            "message": "Alert thresholds updated successfully",
            "updated_thresholds": threshold_updates,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert thresholds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alert thresholds"
        )


class DeploymentRequest(BaseModel):
    """Request for deployment operations"""
    deployment_type: str = Field(..., description="Type of deployment: testing, gradual, full")
    test_users: Optional[List[str]] = Field(None, description="User IDs for testing deployment")
    initial_percentage: int = Field(5, ge=0, le=100, description="Initial rollout percentage")
    max_percentage: int = Field(100, ge=0, le=100, description="Maximum rollout percentage")
    step_size: int = Field(5, ge=1, le=50, description="Percentage increase per step")


@router.post("/deploy")
async def deploy_websocket_system(
    request: DeploymentRequest,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Deploy WebSocket system with specified configuration
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        settings = feature_flags.settings
        
        if request.deployment_type == "testing":
            if not request.test_users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Test users required for testing deployment"
                )
            
            # Set testing mode
            settings.WEBSOCKET_MIGRATION_MODE = "testing"
            settings.WEBSOCKET_ROLLOUT_USER_LIST = ",".join(request.test_users)
            settings.WEBSOCKET_UNIFIED_ENABLED = True
            
            deployment_info = {
                "mode": "testing",
                "test_users": len(request.test_users),
                "user_list": request.test_users
            }
            
        elif request.deployment_type == "gradual":
            # Set gradual mode
            settings.WEBSOCKET_MIGRATION_MODE = "gradual"
            settings.WEBSOCKET_GRADUAL_ROLLOUT_ENABLED = True
            settings.WEBSOCKET_UNIFIED_ENABLED = True
            settings.WEBSOCKET_ROLLOUT_PERCENTAGE = request.initial_percentage
            
            deployment_info = {
                "mode": "gradual",
                "initial_percentage": request.initial_percentage,
                "max_percentage": request.max_percentage,
                "step_size": request.step_size
            }
            
        elif request.deployment_type == "full":
            # Set full mode
            settings.WEBSOCKET_MIGRATION_MODE = "full"
            settings.WEBSOCKET_ROLLOUT_PERCENTAGE = 100
            settings.WEBSOCKET_UNIFIED_ENABLED = True
            
            deployment_info = {
                "mode": "full",
                "percentage": 100
            }
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid deployment type: {request.deployment_type}"
            )
        
        # Clear user assignment cache
        feature_flags.clear_user_assignment_cache()
        
        logger.info(f"WebSocket system deployed in {request.deployment_type} mode by admin {current_user.username}")
        
        return {
            "success": True,
            "message": f"WebSocket system deployed in {request.deployment_type} mode",
            "deployment_info": deployment_info,
            "deployed_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying WebSocket system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy WebSocket system"
        )


@router.post("/rollback")
async def rollback_websocket_system(
    rollback_type: str = "emergency",
    reason: str = "Manual rollback via API",
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Rollback WebSocket system to legacy mode
    
    Requires admin privileges.
    """
    try:
        feature_flags = get_websocket_feature_flags()
        router_instance = get_websocket_router()
        
        # Get current stats before rollback
        stats_before = router_instance.get_connection_stats()
        unified_connections = stats_before.get("unified_stats", {}).get("total_connections", 0)
        
        if rollback_type == "emergency":
            # Emergency rollback - disable unified system completely
            feature_flags.settings.WEBSOCKET_MIGRATION_MODE = "disabled"
            feature_flags.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = 0
            feature_flags.settings.WEBSOCKET_UNIFIED_ENABLED = False
            
        elif rollback_type == "gradual":
            # Gradual rollback - reduce percentage
            current_percentage = feature_flags.settings.WEBSOCKET_ROLLOUT_PERCENTAGE
            new_percentage = max(0, current_percentage - 10)  # Reduce by 10%
            feature_flags.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = new_percentage
            
            if new_percentage == 0:
                feature_flags.settings.WEBSOCKET_MIGRATION_MODE = "disabled"
        
        # Clear user assignment cache
        feature_flags.clear_user_assignment_cache()
        
        logger.critical(f"WebSocket system rollback ({rollback_type}) initiated by admin {current_user.username}: {reason}")
        
        return {
            "success": True,
            "message": f"WebSocket system rollback ({rollback_type}) completed",
            "rollback_info": {
                "type": rollback_type,
                "reason": reason,
                "initiated_by": current_user.username,
                "unified_connections_before": unified_connections,
                "timestamp": datetime.utcnow().isoformat()
            },
            "next_steps": [
                "Monitor system for stability",
                "Review logs for rollback cause",
                "All new connections will use legacy system"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error during WebSocket rollback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform WebSocket rollback"
        )