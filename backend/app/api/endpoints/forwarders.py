"""
Forwarders management endpoints with health checking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import (
    ForwarderCreate, 
    ForwarderUpdate, 
    Forwarder as ForwarderSchema, 
    HealthCheckResult,
    ForwarderHealthStatus,
    ForwarderTestResult,
    HealthSummary
)
from ...services.forwarder_service import ForwarderService
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/", response_model=List[ForwarderSchema])
async def list_forwarders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    forwarder_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all DNS forwarders with filtering and pagination"""
    forwarder_service = ForwarderService(db)
    result = await forwarder_service.get_forwarders(
        skip=skip,
        limit=limit,
        forwarder_type=forwarder_type,
        active_only=active_only,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return result["items"]

@router.post("/", response_model=ForwarderSchema)
async def create_forwarder(
    forwarder_data: ForwarderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS forwarder with automatic health checking"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    # Create backup before forwarder creation
    backup_success = await bind_service.backup_before_forwarder_changes("create")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before forwarder creation"
        )
    
    # Create forwarder in database (includes initial health check)
    forwarder = await forwarder_service.create_forwarder(forwarder_data.dict())
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder

@router.get("/{forwarder_id}", response_model=ForwarderSchema)
async def get_forwarder(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific DNS forwarder with health status"""
    forwarder_service = ForwarderService(db)
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    return forwarder

@router.put("/{forwarder_id}", response_model=ForwarderSchema)
async def update_forwarder(
    forwarder_id: int,
    forwarder_data: ForwarderUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a DNS forwarder with health check validation"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    # Create backup before forwarder update
    backup_success = await bind_service.backup_before_forwarder_changes("update")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before forwarder update"
        )
    
    forwarder = await forwarder_service.update_forwarder(forwarder_id, forwarder_data.dict(exclude_unset=True))
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder

@router.delete("/{forwarder_id}")
async def delete_forwarder(
    forwarder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    # Create backup before forwarder deletion
    backup_success = await bind_service.backup_before_forwarder_changes("delete")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before forwarder deletion"
        )
    
    success = await forwarder_service.delete_forwarder(forwarder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return {"message": "Forwarder deleted successfully"}

@router.post("/bulk/test")
async def test_multiple_forwarders(
    request_data: dict,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test connectivity for multiple forwarders"""
    forwarder_service = ForwarderService(db)
    
    forwarder_ids = request_data.get("forwarder_ids", [])
    test_domains = request_data.get("test_domains")
    
    if not forwarder_ids:
        raise HTTPException(status_code=400, detail="No forwarder IDs provided")
    
    results = []
    for forwarder_id in forwarder_ids:
        try:
            forwarder = await forwarder_service.get_forwarder(forwarder_id)
            if not forwarder:
                results.append({
                    "id": forwarder_id,
                    "status": "error",
                    "response_time": 0,
                    "error": "Forwarder not found"
                })
                continue
            
            test_results = await forwarder_service.test_forwarder(forwarder, test_domains)
            
            # Calculate overall status and response time
            overall_status = "success"
            total_response_time = 0
            total_queries = 0
            
            for result in test_results:
                if result.get("success_rate", 0) < 100:
                    overall_status = "degraded" if result.get("success_rate", 0) > 0 else "failed"
                response_time = result.get("avg_response_time") or 0
                total_response_time += response_time
                total_queries += 1
            
            avg_response_time = total_response_time / total_queries if total_queries > 0 else 0
            
            results.append({
                "id": forwarder_id,
                "status": overall_status,
                "response_time": round(avg_response_time, 2),
                "error": None
            })
        except Exception as e:
            results.append({
                "id": forwarder_id,
                "status": "error",
                "response_time": 0,
                "error": str(e)
            })
    
    successful_tests = len([r for r in results if r["status"] == "success"])
    
    return {
        "data": results,
        "message": f"Bulk test completed: {successful_tests}/{len(forwarder_ids)} forwarders healthy",
        "details": {
            "tested_forwarders": len(forwarder_ids),
            "successful_tests": successful_tests,
            "failed_tests": len(forwarder_ids) - successful_tests
        }
    }

@router.post("/{forwarder_id}/test")
async def test_forwarder(
    forwarder_id: int,
    test_domains: Optional[List[str]] = None,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test forwarder connectivity with specified domains"""
    forwarder_service = ForwarderService(db)
    
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    test_results = await forwarder_service.test_forwarder(forwarder, test_domains)
    
    # Calculate overall status and response time for frontend compatibility
    overall_status = "success"
    total_response_time = 0
    total_queries = 0
    
    for result in test_results:
        if result.get("success_rate", 0) < 100:
            overall_status = "degraded" if result.get("success_rate", 0) > 0 else "failed"
        response_time = result.get("avg_response_time") or 0
        total_response_time += response_time
        total_queries += 1
    
    avg_response_time = total_response_time / total_queries if total_queries > 0 else 0
    
    # Return in the format expected by frontend
    return {
        "data": {
            "status": overall_status,
            "response_time": round(avg_response_time, 2)
        },
        "message": f"Forwarder test completed with {overall_status} status",
        "details": {
            "forwarder_id": forwarder_id,
            "results": test_results
        }
    }

@router.get("/{forwarder_id}/health")
async def get_forwarder_health(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive health status for a forwarder"""
    forwarder_service = ForwarderService(db)
    health_status = await forwarder_service.get_health_status(forwarder_id)
    
    if not health_status or health_status.get("total_servers", 0) == 0:
        raise HTTPException(status_code=404, detail="Forwarder not found or no health data available")
    
    return health_status

@router.get("/{forwarder_id}/health/history")
async def get_forwarder_health_history(
    forwarder_id: int,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health check history for a forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Verify forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    history = await forwarder_service.get_health_history(forwarder_id, hours, limit)
    return {
        "forwarder_id": forwarder_id,
        "hours": hours,
        "history": history
    }

@router.post("/{forwarder_id}/health/check")
async def perform_health_check(
    forwarder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a health check for a forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Verify forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    if not forwarder.health_check_enabled:
        raise HTTPException(status_code=400, detail="Health checking is disabled for this forwarder")
    
    # Perform health check in background
    background_tasks.add_task(forwarder_service.perform_health_check, forwarder_id)
    
    return {"message": "Health check initiated", "forwarder_id": forwarder_id}

@router.get("/{forwarder_id}/health/trends")
async def get_forwarder_health_trends(
    forwarder_id: int,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health status trends for a forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Check if forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    trends = await forwarder_service.get_health_status_trends(forwarder_id, hours)
    
    return trends

@router.get("/health/tracking")
async def get_all_forwarders_health_tracking(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive health tracking for all forwarders"""
    forwarder_service = ForwarderService(db)
    tracking_data = await forwarder_service.get_all_forwarders_health_tracking()
    
    return tracking_data

@router.post("/{forwarder_id}/toggle")
async def toggle_forwarder_status(
    forwarder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle forwarder active status"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    forwarder = await forwarder_service.toggle_forwarder_status(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder

@router.post("/{forwarder_id}/health/toggle")
async def toggle_health_check(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle forwarder health check enabled status"""
    forwarder_service = ForwarderService(db)
    
    forwarder = await forwarder_service.toggle_health_check(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    return forwarder

@router.post("/health/refresh")
async def refresh_all_forwarders_health(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Refresh health status for all forwarders with health checking enabled"""
    forwarder_service = ForwarderService(db)
    
    # Get all active forwarders with health checking enabled
    result = await forwarder_service.get_forwarders(active_only=True, limit=1000)
    forwarders = result["items"]
    
    health_enabled_forwarders = [f for f in forwarders if f.health_check_enabled]
    
    if not health_enabled_forwarders:
        return {
            "message": "No forwarders with health checking enabled found",
            "refreshed_count": 0,
            "total_forwarders": len(forwarders)
        }
    
    # Trigger health checks for all enabled forwarders in background
    for forwarder in health_enabled_forwarders:
        background_tasks.add_task(forwarder_service.perform_health_check, forwarder.id)
    
    return {
        "message": f"Health check refresh initiated for {len(health_enabled_forwarders)} forwarders",
        "refreshed_count": len(health_enabled_forwarders),
        "total_forwarders": len(forwarders),
        "forwarder_ids": [f.id for f in health_enabled_forwarders]
    }

@router.get("/health/summary")
async def get_all_forwarders_health_summary(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health summary for all forwarders"""
    forwarder_service = ForwarderService(db)
    
    # Get all active forwarders
    result = await forwarder_service.get_forwarders(active_only=True, limit=1000)
    forwarders = result["items"]
    
    summary = {
        "total_forwarders": len(forwarders),
        "healthy_forwarders": 0,
        "unhealthy_forwarders": 0,
        "degraded_forwarders": 0,
        "unknown_forwarders": 0,
        "forwarder_details": []
    }
    
    for forwarder in forwarders:
        if forwarder.health_check_enabled:
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
                "status": "disabled",
                "healthy_servers": 0,
                "total_servers": len(forwarder.servers) if forwarder.servers else 0,
                "last_checked": None
            })
    
    return summary

@router.get("/{forwarder_id}/statistics")
async def get_forwarder_statistics(
    forwarder_id: int,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive statistics for a specific forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Check if forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    statistics = await forwarder_service.get_forwarder_statistics(forwarder_id, hours)
    
    return statistics

@router.get("/{forwarder_id}/usage")
async def get_forwarder_usage_statistics(
    forwarder_id: int,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get usage statistics for a forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Check if forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    usage_stats = await forwarder_service.get_forwarder_usage_statistics(forwarder_id, hours)
    
    return usage_stats

@router.get("/{forwarder_id}/performance")
async def get_forwarder_performance_metrics(
    forwarder_id: int,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed performance metrics for a forwarder"""
    forwarder_service = ForwarderService(db)
    
    # Check if forwarder exists
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    performance_metrics = await forwarder_service.get_forwarder_performance_metrics(forwarder_id, hours)
    
    return performance_metrics

@router.get("/statistics/all")
async def get_all_forwarders_statistics(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive statistics for all forwarders"""
    forwarder_service = ForwarderService(db)
    
    all_statistics = await forwarder_service.get_all_forwarders_statistics(hours)
    
    return all_statistics


# Priority Management Endpoints
@router.put("/{forwarder_id}/priority")
async def update_forwarder_priority(
    forwarder_id: int,
    background_tasks: BackgroundTasks,
    priority: int = Query(..., ge=1, le=10),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update the priority of a specific forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    forwarder = await forwarder_service.update_forwarder_priority(forwarder_id, priority)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder


@router.post("/priorities/reorder")
async def reorder_forwarder_priorities(
    forwarder_priorities: List[Dict[str, int]],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Reorder multiple forwarders by updating their priorities"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    updated_forwarders = await forwarder_service.reorder_forwarder_priorities(forwarder_priorities)
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return {"updated_count": len(updated_forwarders), "forwarders": updated_forwarders}


@router.get("/priority/{priority}")
async def get_forwarders_by_priority(
    priority: int = Path(..., ge=1, le=10),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get all forwarders with a specific priority"""
    forwarder_service = ForwarderService(db)
    forwarders = await forwarder_service.get_forwarders_by_priority(priority)
    return forwarders


# Grouping Management Endpoints
@router.get("/groups")
async def get_forwarder_groups(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get all forwarder groups with statistics"""
    forwarder_service = ForwarderService(db)
    groups = await forwarder_service.get_forwarder_groups()
    return groups


@router.get("/groups/{group_name}")
async def get_forwarders_in_group(
    group_name: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get all forwarders in a specific group"""
    forwarder_service = ForwarderService(db)
    forwarders = await forwarder_service.get_forwarders_in_group(group_name)
    return forwarders


@router.get("/ungrouped")
async def get_ungrouped_forwarders(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get all forwarders that are not assigned to any group"""
    forwarder_service = ForwarderService(db)
    forwarders = await forwarder_service.get_ungrouped_forwarders()
    return forwarders


@router.put("/{forwarder_id}/group")
async def update_forwarder_group(
    forwarder_id: int,
    background_tasks: BackgroundTasks,
    group_name: Optional[str] = Query(None),
    group_priority: Optional[int] = Query(None, ge=1, le=10),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update the group assignment for a forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    forwarder = await forwarder_service.update_forwarder_group(forwarder_id, group_name, group_priority)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder


@router.post("/groups/{group_name}/add")
async def move_forwarders_to_group(
    group_name: str,
    forwarder_ids: List[int],
    background_tasks: BackgroundTasks,
    group_priority: Optional[int] = Query(None, ge=1, le=10),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Move multiple forwarders to a group"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    updated_forwarders = await forwarder_service.move_forwarders_to_group(forwarder_ids, group_name, group_priority)
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return {"updated_count": len(updated_forwarders), "forwarders": updated_forwarders}


@router.post("/groups/remove")
async def remove_forwarders_from_group(
    forwarder_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Remove forwarders from their current groups"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    updated_forwarders = await forwarder_service.remove_forwarders_from_group(forwarder_ids)
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return {"updated_count": len(updated_forwarders), "forwarders": updated_forwarders}


@router.put("/groups/{old_group_name}/rename")
async def rename_forwarder_group(
    old_group_name: str,
    background_tasks: BackgroundTasks,
    new_group_name: str = Query(...),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Rename a forwarder group"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    updated_forwarders = await forwarder_service.rename_forwarder_group(old_group_name, new_group_name)
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return {"updated_count": len(updated_forwarders), "forwarders": updated_forwarders}


# Template Management Endpoints
@router.post("/from-template")
async def create_forwarder_from_template(
    background_tasks: BackgroundTasks,
    template_name: str = Query(...),
    forwarder_data: Dict[str, Any] = {},
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a forwarder from a template"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService(db)
    
    # Create backup before forwarder creation
    backup_success = await bind_service.backup_before_forwarder_changes("create_from_template")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before forwarder creation"
        )
    
    forwarder = await forwarder_service.create_forwarder_from_template(template_name, forwarder_data)
    
    # Update BIND9 configuration in background
    background_tasks.add_task(bind_service.update_forwarder_configuration)
    background_tasks.add_task(bind_service.reload_configuration)
    
    return forwarder