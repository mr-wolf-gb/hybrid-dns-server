"""
RPZ management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import csv
import io

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...models.auth import User
from ...schemas.security import (
    RPZRuleCreate, RPZRuleUpdate, RPZRule as RPZRuleSchema,
    RPZRuleImportResult, RPZAction, RPZCategory, RPZCategoryStatus,
    RPZCategoryToggleResult, RPZBulkCategorizeRequest, RPZBulkCategorizeResult,
    RPZBulkUpdateRequest, RPZBulkUpdateResult, RPZBulkDeleteRequest, RPZBulkDeleteResult,
    ThreatFeedCreate, ThreatFeedUpdate, ThreatFeed as ThreatFeedSchema,
    ThreatFeedUpdateResult, BulkThreatFeedUpdateResult, ThreatFeedStatus, UpdateStatus
)
from ...services.rpz_service import RPZService
from ...services.threat_feed_service import ThreatFeedService
from ...services.bind_service import BindService
from ...core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


# RPZ Rules Management Endpoints

@router.get("/rules")
async def list_rpz_rules(
    category: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List RPZ rules with filtering"""
    rpz_service = RPZService(db)
    rules = await rpz_service.get_rules(
        rpz_zone=category,
        action=action,
        search=search,
        active_only=active_only,
        skip=skip,
        limit=limit
    )  
  
    # Transform the rules to ensure frontend compatibility
    transformed_rules = []
    for rule in rules:
        # Ensure rpz_zone has proper format
        rpz_zone = rule.rpz_zone or "custom"
        if not rpz_zone.startswith('rpz.'):
            rpz_zone = f"rpz.{rpz_zone}"
        
        rule_dict = {
            "id": rule.id,
            "domain": rule.domain or "",
            "rpz_zone": rpz_zone,
            "category": rpz_zone.replace('rpz.', '') if rpz_zone.startswith('rpz.') else rpz_zone,
            "action": rule.action or "block",
            "redirect_target": rule.redirect_target or "",
            "description": rule.description or "",
            "is_active": rule.is_active if rule.is_active is not None else True,
            "source": rule.source or "manual",
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        }
        transformed_rules.append(rule_dict)
    
    return transformed_rules


@router.post("/rules", response_model=RPZRuleSchema)
async def create_rpz_rule(
    rule_data: RPZRuleCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    # Create backup before RPZ rule creation
    backup_success = await bind_service.backup_before_rpz_changes(rule_data.rpz_zone, "create_rule")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before RPZ rule creation"
        )
    
    # Create rule in database
    rule = await rpz_service.create_rule(rule_data.model_dump())
    
    # Update RPZ zone files
    await bind_service.update_rpz_zone_file(rule.rpz_zone)
    await bind_service.reload_configuration()
    
    return rule


@router.put("/rules/{rule_id}", response_model=RPZRuleSchema)
async def update_rpz_rule(
    rule_id: int,
    rule_data: RPZRuleUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update an RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    # Get existing rule for backup
    existing_rule = await rpz_service.get_rule(rule_id)
    if not existing_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Create backup before RPZ rule update
    backup_success = await bind_service.backup_before_rpz_changes(existing_rule.rpz_zone, "update_rule")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before RPZ rule update"
        )
    
    rule = await rpz_service.update_rule(rule_id, rule_data.model_dump(exclude_unset=True))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update RPZ zone files
    await bind_service.update_rpz_zone_file(rule.rpz_zone)
    await bind_service.reload_configuration()
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rpz_rule(
    rule_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete an RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService()
    
    rpz_zone = await rpz_service.get_rule_zone(rule_id)
    success = await rpz_service.delete_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update RPZ zone files
    if rpz_zone:
        await bind_service.update_rpz_zone_file(rpz_zone)
        await bind_service.reload_configuration()
    
    return {"message": "Rule deleted successfully"}


# Threat Feed Management Endpoints - Specific routes first

@router.get("/threat-feeds")
async def list_threat_feeds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    feed_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all threat feeds with filtering and pagination"""
    threat_feed_service = ThreatFeedService(db)
    feeds = await threat_feed_service.get_feeds(
        skip=skip,
        limit=limit,
        feed_type=feed_type,
        active_only=active_only,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return feeds


@router.get("/threat-feeds/schedule")
async def get_threat_feed_schedule(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get threat feed update schedule"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        schedule = await threat_feed_service.get_feed_update_schedule()
        return schedule
    except Exception as e:
        logger.error(f"Failed to get threat feed schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-feeds/statistics")
async def get_threat_feed_statistics(
    feed_id: Optional[int] = Query(None, description="Get statistics for specific feed"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive threat feed statistics"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        stats = await threat_feed_service.get_comprehensive_statistics(feed_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get threat feed statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-feeds/defaults/available")
async def get_available_default_feeds(
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of available default threat feeds with their import status"""
    try:
        threat_feed_service = ThreatFeedService(db)
        result = await threat_feed_service.get_available_default_feeds()
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to load default feeds")
            )
        
        return {
            "feeds": result["feeds"],
            "categories": result["categories"],
            "metadata": result["metadata"],
            "summary": result["summary"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get available default feeds: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load default feeds: {str(e)}")


@router.get("/threat-feeds/defaults/categories")
async def get_default_feed_categories(
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Get available threat feed categories with descriptions"""
    try:
        threat_feed_service = ThreatFeedService(db)
        default_data = await threat_feed_service.load_default_feeds()
        
        return {
            "categories": default_data.get("categories", {}),
            "metadata": default_data.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to get default feed categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load categories: {str(e)}")


@router.post("/threat-feeds")
async def create_threat_feed(
    feed_data: ThreatFeedCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        feed = await threat_feed_service.create_feed(feed_data.model_dump())
        logger.info(f"Created threat feed {feed.id}: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to create threat feed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/threat-feeds/schedule-updates")
async def schedule_threat_feed_updates(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Execute scheduled updates for all feeds that are due"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        result = await threat_feed_service.schedule_feed_updates()
        logger.info(f"Scheduled updates completed: {result.successful_updates} successful, {result.failed_updates} failed")
        return result
    except Exception as e:
        logger.error(f"Failed to execute scheduled updates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat-feeds/custom")
async def create_custom_threat_list(
    name: str = Body(..., description="Name for the custom threat list"),
    domains: List[str] = Body(..., description="List of domains to block"),
    category: str = Body("custom", description="Category for the threat list"),
    description: Optional[str] = Body(None, description="Description of the threat list"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a custom threat list from provided domains"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        feed = await threat_feed_service.create_custom_threat_list(
            name=name,
            domains=domains,
            category=category,
            description=description
        )
        logger.info(f"Created custom threat list {feed.id}: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to create custom threat list: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/threat-feeds/update")
async def update_all_threat_feeds(
    force_update: bool = Query(False, description="Force update all feeds regardless of schedule"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update all active threat feeds"""
    threat_feed_service = ThreatFeedService(db)
    bind_service = BindService(db)
    
    logger.info(f"Bulk threat feed update requested (force={force_update})")
    
    # Update all feeds
    result = await threat_feed_service.update_all_feeds(force_update=force_update)
    
    # Schedule BIND9 configuration updates for all affected zones
    if result.successful_updates > 0:
        # Get unique feed types that were updated successfully
        updated_feed_types = set()
        for feed_result in result.feed_results:
            if feed_result.status == UpdateStatus.SUCCESS:
                # Get the feed to determine its type
                feed = await threat_feed_service.get_feed(feed_result.feed_id)
                if feed:
                    updated_feed_types.add(feed.feed_type)
        
        # Schedule BIND9 updates for each affected zone
        for feed_type in updated_feed_types:
            background_tasks.add_task(_update_bind_configuration, feed_type)
    
    return result


@router.post("/threat-feeds/defaults/import")
async def import_default_feeds(
    selected_feeds: List[str] = Body(None, description="List of feed names to import (empty for all recommended)"),
    activate_feeds: bool = Body(True, description="Whether to activate imported feeds"),
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Import selected default threat feeds"""
    try:
        threat_feed_service = ThreatFeedService(db)
        
        # If no specific feeds selected, import only the recommended active ones
        if not selected_feeds:
            available_result = await threat_feed_service.get_available_default_feeds()
            if available_result["success"]:
                selected_feeds = [
                    feed["name"] for feed in available_result["feeds"] 
                    if feed["recommended_active"] and not feed["is_imported"]
                ]
        
        result = await threat_feed_service.import_default_feeds(
            selected_feeds=selected_feeds,
            activate_feeds=activate_feeds
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Failed to import default feeds")
            )
        
        return {
            "message": f"Successfully imported {result['imported']} threat feeds",
            "imported": result["imported"],
            "skipped": result["skipped"],
            "errors": result.get("errors", []),
            "feeds": result.get("feeds", []),
            "categories": result.get("categories", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import default feeds: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# Parameterized routes come after specific routes

@router.get("/threat-feeds/{feed_id}")
async def get_threat_feed(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific threat feed"""
    threat_feed_service = ThreatFeedService(db)
    feed = await threat_feed_service.get_feed(feed_id)
    
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    return feed


@router.put("/threat-feeds/{feed_id}")
async def update_threat_feed(
    feed_id: int,
    feed_data: ThreatFeedUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        feed = await threat_feed_service.update_feed(feed_id, feed_data.model_dump(exclude_unset=True))
        if not feed:
            raise HTTPException(status_code=404, detail="Threat feed not found")
        
        logger.info(f"Updated threat feed {feed.id}: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to update threat feed {feed_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/threat-feeds/{feed_id}")
async def delete_threat_feed(
    feed_id: int,
    remove_rules: bool = Query(True, description="Whether to remove associated RPZ rules"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a threat feed and optionally remove associated rules"""
    threat_feed_service = ThreatFeedService(db)
    
    success = await threat_feed_service.delete_feed(feed_id, remove_rules=remove_rules)
    if not success:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    return {"message": "Threat feed deleted successfully"}


@router.post("/threat-feeds/{feed_id}/test")
async def test_threat_feed(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test connectivity to a threat feed without updating rules"""
    threat_feed_service = ThreatFeedService(db)
    
    feed = await threat_feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    test_result = await threat_feed_service.test_feed_connectivity(feed)
    return test_result


@router.post("/threat-feeds/{feed_id}/toggle")
async def toggle_threat_feed(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle the active status of a threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    feed = await threat_feed_service.toggle_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    return feed


@router.get("/threat-feeds/{feed_id}/status")
async def get_threat_feed_status(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed status information for a threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    feed = await threat_feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    # Get health status
    health_info = await threat_feed_service.get_feed_health_status(feed_id)
    
    # Create status response
    status = ThreatFeedStatus(
        id=feed.id,
        name=feed.name,
        is_active=feed.is_active,
        last_updated=feed.last_updated,
        last_update_status=feed.last_update_status,
        last_update_error=feed.last_update_error,
        rules_count=feed.rules_count,
        next_update=health_info.get('next_update')
    )
    
    return status


@router.post("/threat-feeds/{feed_id}/update")
async def update_single_threat_feed(
    feed_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a single threat feed from its source"""
    threat_feed_service = ThreatFeedService(db)
    bind_service = BindService(db)
    
    feed = await threat_feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    if not feed.is_active:
        raise HTTPException(status_code=400, detail="Cannot update inactive threat feed")
    
    logger.info(f"Manual update requested for threat feed: {feed.name}")
    
    # Update the feed
    result = await threat_feed_service.update_feed_from_source(feed)
    
    # Schedule BIND9 configuration update in background if successful
    if result.status == UpdateStatus.SUCCESS:
        background_tasks.add_task(_update_bind_configuration, feed.feed_type)
    
    return result


@router.get("/threat-feeds/{feed_id}/health")
async def get_threat_feed_health(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health status for a specific threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    health_status = await threat_feed_service.get_feed_health_status(feed_id)
    
    if 'error' in health_status:
        raise HTTPException(status_code=404, detail=health_status['error'])
    
    return health_status


@router.put("/threat-feeds/{feed_id}/custom")
async def update_custom_threat_list(
    feed_id: int,
    domains: List[str] = Body(..., description="Updated list of domains"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a custom threat list with new domains"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        result = await threat_feed_service.update_custom_threat_list(feed_id, domains)
        logger.info(f"Updated custom threat list {feed_id}: {result.status}")
        return result
    except Exception as e:
        logger.error(f"Failed to update custom threat list {feed_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Helper function for background BIND configuration updates
async def _update_bind_configuration(feed_type: str):
    """Update BIND9 configuration for a specific feed type"""
    try:
        from ...core.database import get_database_session
        
        # Get a database session for the background task
        async for db in get_database_session():
            bind_service = BindService(db)
            break  # Only need one iteration
        
        # Update the RPZ zone file for this feed type
        await bind_service.update_rpz_zone_file(f"rpz.{feed_type}")
        await bind_service.reload_configuration()
        
        logger.info(f"Successfully updated BIND9 configuration for feed type: {feed_type}")
        
    except Exception as e:
        logger.error(f"Failed to update BIND9 configuration for feed type {feed_type}: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

# Custom Threat List Management Endpoints

@router.get("/custom-lists")
async def list_custom_threat_lists(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List custom threat lists (feeds with type 'custom')"""
    threat_feed_service = ThreatFeedService(db)
    feeds = await threat_feed_service.get_feeds(
        skip=skip,
        limit=limit,
        feed_type="custom",
        active_only=active_only,
        sort_by="name",
        sort_order="asc"
    )
    return feeds


@router.post("/custom-lists")
async def create_custom_threat_list_empty(
    name: str = Query(..., description="Name of the custom threat list"),
    description: Optional[str] = Query(None, description="Description of the custom threat list"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new custom threat list (local feed without URL)"""
    threat_feed_service = ThreatFeedService(db)
    
    # Create a custom feed with a placeholder URL
    feed_data = {
        'name': name,
        'url': 'http://localhost/custom',  # Placeholder URL for custom lists
        'feed_type': 'custom',
        'format_type': 'domains',
        'update_frequency': 86400,  # Daily
        'description': description or f"Custom threat list: {name}",
        'is_active': True
    }
    
    try:
        feed = await threat_feed_service.create_feed(feed_data)
        logger.info(f"Created custom threat list {feed.id}: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to create custom threat list: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
@router.post("/custom-lists/{list_id}/domains")
async def add_domains_to_custom_list(
    list_id: int,
    domains: List[str] = Query(..., description="List of domains to add to the custom list"),
    action: RPZAction = Query(RPZAction.BLOCK, description="Action to apply to the domains"),
    redirect_target: Optional[str] = Query(None, description="Redirect target (required if action is redirect)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Add domains to a custom threat list"""
    threat_feed_service = ThreatFeedService(db)
    rpz_service = RPZService(db)
    
    # Verify the custom list exists and is of type 'custom'
    feed = await threat_feed_service.get_feed(list_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Custom threat list not found")
    
    if feed.feed_type != 'custom':
        raise HTTPException(status_code=400, detail="This operation is only allowed for custom threat lists")
    
    # Validate redirect target if action is redirect
    if action == RPZAction.REDIRECT and not redirect_target:
        raise HTTPException(
            status_code=400, 
            detail="Redirect target is required when action is redirect"
        )
    
    # Prepare rule data
    rules_data = []
    for domain in domains:
        rule_data = {
            'domain': domain.strip().lower(),
            'rpz_zone': 'custom',
            'action': action.value,
            'source': f"custom_list_{list_id}",
            'description': f"Custom list: {feed.name}"
        }
        if redirect_target:
            rule_data['redirect_target'] = redirect_target
        
        rules_data.append(rule_data)
    
    try:
        # Create the rules
        created_count, error_count, errors = await rpz_service.bulk_create_rules(
            rules_data, 
            source=f"custom_list_{list_id}"
        )
        
        # Update the feed's rule count
        await threat_feed_service.update_feed(list_id, {
            'rules_count': feed.rules_count + created_count
        })
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, 'custom')
        
        return {
            'message': f'Added {created_count} domains to custom list',
            'domains_added': created_count,
            'domains_failed': error_count,
            'errors': errors[:10] if errors else []  # Limit errors to first 10
        }
        
    except Exception as e:
        logger.error(f"Failed to add domains to custom list {list_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/custom-lists/{list_id}/domains")
async def remove_domains_from_custom_list(
    list_id: int,
    domains: List[str] = Query(..., description="List of domains to remove from the custom list"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Remove domains from a custom threat list"""
    threat_feed_service = ThreatFeedService(db)
    rpz_service = RPZService(db)
    
    # Verify the custom list exists and is of type 'custom'
    feed = await threat_feed_service.get_feed(list_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Custom threat list not found")
    
    if feed.feed_type != 'custom':
        raise HTTPException(status_code=400, detail="This operation is only allowed for custom threat lists")
    
    try:
        # Get rules for these domains from this custom list
        rules_to_delete = []
        for domain in domains:
            rules = await rpz_service.get_rules(
                search=domain.strip().lower(),
                source=f"custom_list_{list_id}",
                active_only=False,
                limit=1
            )
            if rules:
                rules_to_delete.extend([rule.id for rule in rules])
        
        if not rules_to_delete:
            return {
                'message': 'No matching domains found in custom list',
                'domains_removed': 0,
                'domains_failed': len(domains)
            }
        
        # Delete the rules
        deleted_count, error_count, errors = await rpz_service.bulk_delete_rules(rules_to_delete)
        
        # Update the feed's rule count
        await threat_feed_service.update_feed(list_id, {
            'rules_count': max(0, feed.rules_count - deleted_count)
        })
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, 'custom')
        
        return {
            'message': f'Removed {deleted_count} domains from custom list',
            'domains_removed': deleted_count,
            'domains_failed': error_count,
            'errors': errors[:10] if errors else []  # Limit errors to first 10
        }
        
    except Exception as e:
        logger.error(f"Failed to remove domains from custom list {list_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
# RPZ Bulk Operations

@router.get("/categories")
async def list_rpz_categories(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all RPZ categories with their status"""
    rpz_service = RPZService(db)
    categories = await rpz_service.get_categories()
    return categories


@router.post("/categories/{category}/toggle")
async def toggle_rpz_category(
    category: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle all rules in a category"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    result = await rpz_service.toggle_category(category)
    
    # Update RPZ zone files
    await bind_service.update_rpz_zone_file(f"rpz.{category}")
    await bind_service.reload_configuration()
    
    return result


@router.post("/bulk/categorize")
async def bulk_categorize_rules(
    request: RPZBulkCategorizeRequest,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk categorize RPZ rules"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    result = await rpz_service.bulk_categorize_rules(
        rule_ids=request.rule_ids,
        new_category=request.new_category
    )
    
    # Update affected RPZ zone files
    affected_zones = set()
    affected_zones.add(f"rpz.{request.new_category}")
    if request.old_categories:
        for old_cat in request.old_categories:
            affected_zones.add(f"rpz.{old_cat}")
    
    for zone in affected_zones:
        await bind_service.update_rpz_zone_file(zone)
    
    await bind_service.reload_configuration()
    
    return result


@router.post("/bulk/update")
async def bulk_update_rules(
    request: RPZBulkUpdateRequest,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk update RPZ rules"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    result = await rpz_service.bulk_update_rules(
        rule_ids=request.rule_ids,
        updates=request.updates.model_dump(exclude_unset=True)
    )
    
    # Update affected RPZ zone files
    affected_zones = await rpz_service.get_affected_zones(request.rule_ids)
    for zone in affected_zones:
        await bind_service.update_rpz_zone_file(zone)
    
    await bind_service.reload_configuration()
    
    return result


@router.post("/bulk/delete")
async def bulk_delete_rules(
    request: RPZBulkDeleteRequest,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete RPZ rules"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    # Get affected zones before deletion
    affected_zones = await rpz_service.get_affected_zones(request.rule_ids)
    
    result = await rpz_service.bulk_delete_rules(request.rule_ids)
    
    # Update affected RPZ zone files
    for zone in affected_zones:
        await bind_service.update_rpz_zone_file(zone)
    
    await bind_service.reload_configuration()
    
    return result


# Import/Export Operations

@router.post("/import")
async def import_rpz_rules(
    file: UploadFile = File(...),
    format_type: str = Query("csv", regex="^(csv|json|bind)$"),
    category: Optional[str] = Query(None),
    action: Optional[str] = Query("block"),
    skip_duplicates: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Import RPZ rules from file"""
    rpz_service = RPZService(db)
    bind_service = BindService(db)
    
    try:
        content = await file.read()
        
        if format_type == "csv":
            result = await rpz_service.import_from_csv(
                content.decode('utf-8'),
                category=category,
                default_action=action,
                skip_duplicates=skip_duplicates
            )
        elif format_type == "json":
            result = await rpz_service.import_from_json(
                content.decode('utf-8'),
                skip_duplicates=skip_duplicates
            )
        elif format_type == "bind":
            result = await rpz_service.import_from_bind_zone(
                content.decode('utf-8'),
                category=category,
                default_action=action,
                skip_duplicates=skip_duplicates
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format type")
        
        # Update affected RPZ zone files
        if result.imported_count > 0:
            affected_categories = result.affected_categories or [category or "custom"]
            for cat in affected_categories:
                await bind_service.update_rpz_zone_file(f"rpz.{cat}")
            
            await bind_service.reload_configuration()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to import RPZ rules: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
async def export_rpz_rules(
    format_type: str = Query("csv", regex="^(csv|json|bind)$"),
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Export RPZ rules to file"""
    rpz_service = RPZService(db)
    
    try:
        if format_type == "csv":
            content, filename = await rpz_service.export_to_csv(
                category=category,
                active_only=active_only
            )
            media_type = "text/csv"
        elif format_type == "json":
            content, filename = await rpz_service.export_to_json(
                category=category,
                active_only=active_only
            )
            media_type = "application/json"
        elif format_type == "bind":
            content, filename = await rpz_service.export_to_bind_zone(
                category=category,
                active_only=active_only
            )
            media_type = "text/plain"
        else:
            raise HTTPException(status_code=400, detail="Unsupported format type")
        
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export RPZ rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# RPZ Statistics and Analytics Endpoints

@router.get("/statistics")
async def get_rpz_statistics(
    include_trends: bool = Query(False, description="Include trend data"),
    hours: int = Query(24, description="Hours of data to include"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get RPZ statistics and analytics"""
    rpz_service = RPZService(db)
    
    try:
        stats = await rpz_service.get_rpz_statistics(
            include_trends=include_trends,
            hours=hours
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to get RPZ statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/statistics")
async def get_intelligence_statistics(
    hours: int = Query(24, description="Hours of data to include"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get threat intelligence statistics"""
    rpz_service = RPZService(db)
    
    try:
        stats = await rpz_service.get_intelligence_statistics(hours=hours)
        return stats
    except Exception as e:
        logger.error(f"Failed to get intelligence statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blocked-queries")
async def get_blocked_queries(
    hours: int = Query(24, description="Hours of data to retrieve"),
    limit: int = Query(100, description="Maximum number of queries to return"),
    skip: int = Query(0, description="Number of queries to skip"),
    category: Optional[str] = Query(None, description="Filter by RPZ category"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get recent blocked queries"""
    rpz_service = RPZService(db)
    
    try:
        queries = await rpz_service.get_blocked_queries(
            hours=hours,
            limit=limit,
            skip=skip,
            category=category
        )
        return queries
    except Exception as e:
        logger.error(f"Failed to get blocked queries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-blocked")
async def get_top_blocked_domains(
    hours: int = Query(24, description="Hours of data to analyze"),
    limit: int = Query(50, description="Number of top domains to return"),
    category: Optional[str] = Query(None, description="Filter by RPZ category"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get top blocked domains"""
    rpz_service = RPZService(db)
    
    try:
        top_domains = await rpz_service.get_top_blocked_domains(
            hours=hours,
            limit=limit,
            category=category
        )
        return top_domains
    except Exception as e:
        logger.error(f"Failed to get top blocked domains: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/timeline")
async def get_rpz_activity_timeline(
    hours: int = Query(24, description="Hours of data to include"),
    interval: str = Query("1h", description="Time interval for grouping (1h, 6h, 1d)"),
    category: Optional[str] = Query(None, description="Filter by RPZ category"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get RPZ activity timeline"""
    rpz_service = RPZService(db)
    
    try:
        timeline = await rpz_service.get_activity_timeline(
            hours=hours,
            interval=interval,
            category=category
        )
        return timeline
    except Exception as e:
        logger.error(f"Failed to get RPZ activity timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/metrics")
async def get_rpz_performance_metrics(
    hours: int = Query(24, description="Hours of data to analyze"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get RPZ performance metrics"""
    rpz_service = RPZService(db)
    
    try:
        metrics = await rpz_service.get_performance_metrics(hours=hours)
        return metrics
    except Exception as e:
        logger.error(f"Failed to get RPZ performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional RPZ Analytics Endpoints

@router.get("/threat-detection-report")
async def get_threat_detection_report(
    days: int = Query(30, description="Number of days to analyze"),
    include_details: bool = Query(True, description="Include detailed threat information"),
    category: Optional[str] = Query(None, description="Filter by threat category"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive threat detection report"""
    rpz_service = RPZService(db)
    
    try:
        report = await rpz_service.get_threat_detection_report(
            days=days,
            include_details=include_details,
            category=category
        )
        return report
    except Exception as e:
        logger.error(f"Failed to get threat detection report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category-statistics")
async def get_category_statistics(
    time_period: int = Query(24, description="Time period in hours"),
    include_inactive: bool = Query(False, description="Include inactive categories"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics by RPZ category"""
    rpz_service = RPZService(db)
    
    try:
        stats = await rpz_service.get_category_statistics(
            time_period=time_period,
            include_inactive=include_inactive
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to get category statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/coverage-report")
async def get_intelligence_coverage_report(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get threat intelligence coverage report"""
    rpz_service = RPZService(db)
    
    try:
        report = await rpz_service.get_intelligence_coverage_report()
        return report
    except Exception as e:
        logger.error(f"Failed to get intelligence coverage report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/feed-performance")
async def get_feed_performance_report(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get threat feed performance report"""
    rpz_service = RPZService(db)
    
    try:
        report = await rpz_service.get_feed_performance_report(days=days)
        return report
    except Exception as e:
        logger.error(f"Failed to get feed performance report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))