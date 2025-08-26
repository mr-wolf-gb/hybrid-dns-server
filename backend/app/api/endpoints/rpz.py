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


# Threat Feed Management Endpoints

@router.get("/threat-feeds", response_model=List[ThreatFeedSchema])
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


@router.post("/threat-feeds", response_model=ThreatFeedSchema)
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


@router.get("/threat-feeds/{feed_id}", response_model=ThreatFeedSchema)
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


@router.put("/threat-feeds/{feed_id}", response_model=ThreatFeedSchema)
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


@router.post("/threat-feeds/{feed_id}/toggle", response_model=ThreatFeedSchema)
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


@router.post("/threat-feeds/schedule-updates", response_model=BulkThreatFeedUpdateResult)
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


@router.post("/threat-feeds/custom", response_model=ThreatFeedSchema)
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


@router.put("/threat-feeds/{feed_id}/custom", response_model=ThreatFeedUpdateResult)
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
    
    feed = await threat_feed_service.toggle_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    return feed


@router.get("/threat-feeds/{feed_id}/status", response_model=ThreatFeedStatus)
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


@router.post("/threat-feeds/update", response_model=BulkThreatFeedUpdateResult)
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


@router.post("/threat-feeds/{feed_id}/update", response_model=ThreatFeedUpdateResult)
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


@router.get("/threat-feeds/statistics")
async def get_threat_feed_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive threat feed statistics"""
    threat_feed_service = ThreatFeedService(db)
    statistics = await threat_feed_service.get_feed_statistics()
    return statistics


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


# Custom Threat List Management Endpoints

@router.get("/custom-lists", response_model=List[ThreatFeedSchema])
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


@router.post("/custom-lists", response_model=ThreatFeedSchema)
async def create_custom_threat_list(
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


@router.get("/custom-lists/{list_id}/domains", response_model=List[RPZRuleSchema])
async def list_custom_list_domains(
    list_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search for specific domains"),
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List domains in a custom threat list"""
    threat_feed_service = ThreatFeedService(db)
    rpz_service = RPZService(db)
    
    # Verify the custom list exists and is of type 'custom'
    feed = await threat_feed_service.get_feed(list_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Custom threat list not found")
    
    if feed.feed_type != 'custom':
        raise HTTPException(status_code=400, detail="This operation is only allowed for custom threat lists")
    
    # Get rules for this custom list
    rules = await rpz_service.get_rules(
        source=f"custom_list_{list_id}",
        search=search,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    
    return rules


# Threat Intelligence Statistics Endpoints

@router.get("/intelligence/statistics")
async def get_threat_intelligence_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive threat intelligence statistics"""
    threat_feed_service = ThreatFeedService(db)
    rpz_service = RPZService(db)
    
    # Get threat feed statistics
    feed_stats = await threat_feed_service.get_feed_statistics()
    
    # Get RPZ statistics
    rpz_stats = await rpz_service.get_comprehensive_statistics()
    
    # Combine statistics
    intelligence_stats = {
        'threat_feeds': feed_stats,
        'rpz_rules': rpz_stats,
        'protection_coverage': {
            'total_domains_protected': feed_stats.get('total_rules_from_feeds', 0),
            'active_threat_feeds': feed_stats.get('active_feeds', 0),
            'custom_lists': feed_stats.get('feeds_by_type', {}).get('custom', 0),
            'external_feeds': sum(
                count for feed_type, count in feed_stats.get('feeds_by_type', {}).items() 
                if feed_type != 'custom'
            )
        },
        'update_health': {
            'feeds_up_to_date': feed_stats.get('update_status_counts', {}).get('success', 0),
            'feeds_with_errors': feed_stats.get('update_status_counts', {}).get('failed', 0),
            'feeds_never_updated': feed_stats.get('update_status_counts', {}).get('never', 0),
            'feeds_due_for_update': feed_stats.get('feeds_due_for_update', 0)
        },
        'generated_at': datetime.utcnow()
    }
    
    return intelligence_stats


@router.get("/intelligence/coverage-report")
async def get_threat_coverage_report(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed threat coverage report"""
    threat_feed_service = ThreatFeedService(db)
    rpz_service = RPZService(db)
    
    # Get all active feeds
    feeds = await threat_feed_service.get_feeds(active_only=True, limit=1000)
    
    # Build coverage report
    coverage_report = {
        'total_feeds': len(feeds),
        'feeds_by_type': {},
        'coverage_by_category': {},
        'feed_health': {
            'healthy': 0,
            'unhealthy': 0,
            'never_updated': 0,
            'updating': 0
        },
        'total_domains_protected': 0,
        'feeds_detail': []
    }
    
    for feed in feeds:
        # Count by type
        feed_type = feed.feed_type
        if feed_type not in coverage_report['feeds_by_type']:
            coverage_report['feeds_by_type'][feed_type] = 0
        coverage_report['feeds_by_type'][feed_type] += 1
        
        # Count by category (RPZ zone)
        if feed_type not in coverage_report['coverage_by_category']:
            coverage_report['coverage_by_category'][feed_type] = {
                'feeds': 0,
                'domains': 0
            }
        coverage_report['coverage_by_category'][feed_type]['feeds'] += 1
        coverage_report['coverage_by_category'][feed_type]['domains'] += feed.rules_count
        
        # Health status
        if feed.last_update_status == UpdateStatus.SUCCESS:
            coverage_report['feed_health']['healthy'] += 1
        elif feed.last_update_status == UpdateStatus.FAILED:
            coverage_report['feed_health']['unhealthy'] += 1
        elif feed.last_update_status == UpdateStatus.PENDING:
            coverage_report['feed_health']['updating'] += 1
        else:
            coverage_report['feed_health']['never_updated'] += 1
        
        # Total domains
        coverage_report['total_domains_protected'] += feed.rules_count
        
        # Feed detail
        coverage_report['feeds_detail'].append({
            'id': feed.id,
            'name': feed.name,
            'type': feed.feed_type,
            'domains': feed.rules_count,
            'last_updated': feed.last_updated,
            'status': feed.last_update_status,
            'is_active': feed.is_active
        })
    
    coverage_report['generated_at'] = datetime.utcnow()
    
    return coverage_report


@router.get("/intelligence/feed-performance")
async def get_feed_performance_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get performance metrics for threat feeds over time"""
    threat_feed_service = ThreatFeedService(db)
    
    # Get all feeds
    feeds = await threat_feed_service.get_feeds(active_only=False, limit=1000)
    
    # Calculate performance metrics
    performance_metrics = {
        'analysis_period_days': days,
        'total_feeds_analyzed': len(feeds),
        'performance_summary': {
            'average_rules_per_feed': 0,
            'most_productive_feed': None,
            'least_productive_feed': None,
            'feeds_with_recent_updates': 0,
            'feeds_with_stale_data': 0
        },
        'feed_performance': [],
        'generated_at': datetime.utcnow()
    }
    
    if feeds:
        # Calculate averages and find extremes
        total_rules = sum(feed.rules_count for feed in feeds)
        performance_metrics['performance_summary']['average_rules_per_feed'] = total_rules / len(feeds)
        
        # Find most and least productive feeds
        active_feeds = [f for f in feeds if f.is_active and f.rules_count > 0]
        if active_feeds:
            most_productive = max(active_feeds, key=lambda f: f.rules_count)
            least_productive = min(active_feeds, key=lambda f: f.rules_count)
            
            performance_metrics['performance_summary']['most_productive_feed'] = {
                'name': most_productive.name,
                'rules_count': most_productive.rules_count
            }
            performance_metrics['performance_summary']['least_productive_feed'] = {
                'name': least_productive.name,
                'rules_count': least_productive.rules_count
            }
        
        # Analyze update freshness
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for feed in feeds:
            # Check if feed has recent updates
            if feed.last_updated and feed.last_updated >= cutoff_date:
                performance_metrics['performance_summary']['feeds_with_recent_updates'] += 1
            elif feed.last_updated and feed.last_updated < cutoff_date:
                performance_metrics['performance_summary']['feeds_with_stale_data'] += 1
            
            # Add individual feed performance
            performance_metrics['feed_performance'].append({
                'id': feed.id,
                'name': feed.name,
                'type': feed.feed_type,
                'is_active': feed.is_active,
                'rules_count': feed.rules_count,
                'last_updated': feed.last_updated,
                'last_update_status': feed.last_update_status,
                'update_frequency_hours': feed.update_frequency / 3600,
                'days_since_update': (
                    (datetime.utcnow() - feed.last_updated).days 
                    if feed.last_updated else None
                )
            })
    
    return performance_metrics


# Background task helper function
async def _update_bind_configuration(rpz_zone: str):
    """Background task to update BIND9 configuration for a specific RPZ zone"""
    try:
        from ...services.bind_service import BindService
        from ...core.database import get_database_session
        
        # Get a database session for the background task
        db = next(get_database_session())
        bind_service = BindService(db)
        
        logger.info(f"Updating BIND9 configuration for RPZ zone: {rpz_zone}")
        
        # Update RPZ zone file
        await bind_service.update_rpz_zone_file(rpz_zone)
        
        # Reload BIND9 configuration
        await bind_service.reload_configuration()
        
        logger.info(f"Successfully updated BIND9 configuration for RPZ zone: {rpz_zone}")
        
    except Exception as e:
        logger.error(f"Failed to update BIND9 configuration for RPZ zone {rpz_zone}: {str(e)}")


# RPZ Statistics and Reporting Endpoints

@router.get("/statistics")
async def get_rpz_statistics(
    category: Optional[str] = Query(None, description="Filter statistics by RPZ category/zone"),
    include_trends: bool = Query(True, description="Include trend analysis"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive RPZ statistics including blocked queries and threat detection"""
    rpz_service = RPZService(db)
    
    try:
        # Get comprehensive RPZ statistics
        rpz_stats = await rpz_service.get_comprehensive_statistics()
        
        # Get category-specific statistics if requested
        if category:
            category_stats = await rpz_service.get_zone_statistics(rpz_zone=category)
            rpz_stats['category_focus'] = category_stats
        
        # Get blocked query statistics from monitoring service
        from ...services.monitoring_service import MonitoringService
        monitoring_service = MonitoringService()
        
        # Get blocked query statistics for different time periods
        blocked_stats = {
            'last_24_hours': await monitoring_service.get_blocked_query_stats(hours=24),
            'last_7_days': await monitoring_service.get_blocked_query_stats(hours=168),
            'last_30_days': await monitoring_service.get_blocked_query_stats(hours=720)
        }
        
        # Get top blocked domains
        top_blocked = await monitoring_service.get_top_blocked_domains(hours=168, limit=20)
        
        # Get blocking effectiveness by category
        category_effectiveness = await monitoring_service.get_blocking_by_category(hours=168)
        
        # Combine all statistics
        comprehensive_stats = {
            'rpz_rules': rpz_stats,
            'blocked_queries': blocked_stats,
            'top_blocked_domains': top_blocked,
            'category_effectiveness': category_effectiveness,
            'protection_summary': {
                'total_active_rules': rpz_stats.get('overall', {}).get('active_rules', 0),
                'categories_enabled': len([cat for cat in rpz_stats.get('categories', []) if cat.get('active_rules', 0) > 0]),
                'total_blocked_last_24h': blocked_stats.get('last_24_hours', {}).get('blocked_queries', 0),
                'block_rate_percentage': round(
                    (blocked_stats.get('last_24_hours', {}).get('blocked_queries', 0) / 
                     max(blocked_stats.get('last_24_hours', {}).get('total_queries', 1), 1)) * 100, 2
                )
            }
        }
        
        # Add trend analysis if requested
        if include_trends:
            trend_data = await monitoring_service.get_blocking_trends(days=30)
            comprehensive_stats['trends'] = trend_data
        
        comprehensive_stats['generated_at'] = datetime.utcnow()
        
        return comprehensive_stats
        
    except Exception as e:
        logger.error(f"Failed to get RPZ statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve RPZ statistics: {str(e)}")


@router.get("/blocked-queries")
async def get_blocked_query_report(
    hours: int = Query(24, ge=1, le=8760, description="Number of hours to analyze (max 1 year)"),
    category: Optional[str] = Query(None, description="Filter by RPZ category"),
    client_ip: Optional[str] = Query(None, description="Filter by client IP address"),
    domain: Optional[str] = Query(None, description="Filter by domain pattern"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed blocked query report with filtering options"""
    from ...services.monitoring_service import MonitoringService
    
    try:
        monitoring_service = MonitoringService()
        
        # Get blocked queries with filters
        blocked_queries = await monitoring_service.get_blocked_queries(
            hours=hours,
            category=category,
            client_ip=client_ip,
            domain=domain,
            limit=limit,
            skip=skip
        )
        
        # Get summary statistics for the filtered results
        summary_stats = await monitoring_service.get_blocked_query_summary(
            hours=hours,
            category=category,
            client_ip=client_ip,
            domain=domain
        )
        
        # Get hourly breakdown for the time period
        hourly_breakdown = await monitoring_service.get_blocked_queries_hourly(
            hours=min(hours, 168),  # Limit hourly breakdown to 1 week max
            category=category
        )
        
        return {
            'query_results': blocked_queries,
            'summary': summary_stats,
            'hourly_breakdown': hourly_breakdown,
            'filters_applied': {
                'hours': hours,
                'category': category,
                'client_ip': client_ip,
                'domain': domain,
                'limit': limit,
                'skip': skip
            },
            'generated_at': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get blocked query report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve blocked query report: {str(e)}")


@router.get("/threat-detection-report")
async def get_threat_detection_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    include_details: bool = Query(True, description="Include detailed threat breakdown"),
    format: str = Query("json", regex="^(json|csv)$", description="Response format"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Generate comprehensive threat detection report"""
    from ...services.monitoring_service import MonitoringService
    from ...services.threat_feed_service import ThreatFeedService
    
    try:
        monitoring_service = MonitoringService()
        threat_feed_service = ThreatFeedService(db)
        rpz_service = RPZService(db)
        
        # Get threat detection statistics
        threat_stats = await monitoring_service.get_threat_detection_stats(days=days)
        
        # Get threat feed effectiveness
        feed_effectiveness = await threat_feed_service.get_feed_effectiveness_report(days=days)
        
        # Get category-based threat detection
        category_threats = await monitoring_service.get_threats_by_category(days=days)
        
        # Get top threat sources (domains/IPs that triggered most blocks)
        top_threat_sources = await monitoring_service.get_top_threat_sources(days=days, limit=50)
        
        # Get threat timeline (daily breakdown)
        threat_timeline = await monitoring_service.get_threat_timeline(days=days)
        
        # Get geographic threat distribution if available
        geo_threats = await monitoring_service.get_geographic_threat_distribution(days=days)
        
        report_data = {
            'report_period': {
                'days': days,
                'start_date': (datetime.utcnow() - timedelta(days=days)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            },
            'executive_summary': {
                'total_threats_blocked': threat_stats.get('total_blocked', 0),
                'unique_threat_domains': threat_stats.get('unique_domains', 0),
                'threat_sources_identified': threat_stats.get('unique_sources', 0),
                'most_active_threat_category': threat_stats.get('top_category', 'Unknown'),
                'average_daily_blocks': threat_stats.get('daily_average', 0),
                'threat_detection_rate': threat_stats.get('detection_rate_percent', 0)
            },
            'threat_categories': category_threats,
            'feed_effectiveness': feed_effectiveness,
            'threat_timeline': threat_timeline,
            'top_threat_sources': top_threat_sources,
            'geographic_distribution': geo_threats
        }
        
        # Add detailed breakdown if requested
        if include_details:
            detailed_threats = await monitoring_service.get_detailed_threat_breakdown(days=days)
            report_data['detailed_breakdown'] = detailed_threats
        
        report_data['generated_at'] = datetime.utcnow()
        
        # Return CSV format if requested
        if format == "csv":
            csv_data = await _generate_threat_report_csv(report_data)
            from fastapi.responses import Response
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=threat_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
        return report_data
        
    except Exception as e:
        logger.error(f"Failed to generate threat detection report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate threat detection report: {str(e)}")


@router.get("/category-statistics")
async def get_category_based_statistics(
    include_inactive: bool = Query(False, description="Include statistics for inactive categories"),
    time_period: int = Query(24, ge=1, le=8760, description="Time period in hours for query statistics"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed statistics broken down by RPZ categories"""
    rpz_service = RPZService(db)
    
    try:
        from ...services.monitoring_service import MonitoringService
        monitoring_service = MonitoringService()
        
        # Get all categories
        categories = await rpz_service.get_available_categories()
        category_statistics = []
        
        for category in categories:
            # Get basic category info
            category_info = await rpz_service.get_category_info(category)
            
            # Get category status
            category_status = await rpz_service.get_category_status(category)
            
            # Skip inactive categories if not requested
            if not include_inactive and category_status['status'] in ['disabled', 'empty']:
                continue
            
            # Get blocking statistics for this category
            blocking_stats = await monitoring_service.get_category_blocking_stats(
                category=category, 
                hours=time_period
            )
            
            # Get top blocked domains in this category
            top_blocked_in_category = await monitoring_service.get_top_blocked_domains(
                hours=time_period,
                category=category,
                limit=10
            )
            
            # Combine all statistics for this category
            category_stat = {
                'category': category,
                'display_name': category_info['display_name'],
                'description': category_info['description'],
                'rule_statistics': {
                    'total_rules': category_info['total_rules'],
                    'active_rules': category_info['active_rules'],
                    'rules_by_action': category_info['rules_by_action'],
                    'rules_by_source': category_info['rules_by_source']
                },
                'status': category_status,
                'blocking_performance': blocking_stats,
                'top_blocked_domains': top_blocked_in_category,
                'effectiveness_score': _calculate_category_effectiveness(
                    category_info, blocking_stats
                )
            }
            
            category_statistics.append(category_stat)
        
        # Calculate overall statistics
        total_active_rules = sum(cat['rule_statistics']['active_rules'] for cat in category_statistics)
        total_blocks = sum(cat['blocking_performance'].get('blocked_queries', 0) for cat in category_statistics)
        
        overall_summary = {
            'total_categories': len(category_statistics),
            'total_active_rules': total_active_rules,
            'total_blocks_period': total_blocks,
            'most_effective_category': max(
                category_statistics, 
                key=lambda x: x['effectiveness_score']
            )['category'] if category_statistics else None,
            'least_effective_category': min(
                category_statistics, 
                key=lambda x: x['effectiveness_score']
            )['category'] if category_statistics else None
        }
        
        return {
            'time_period_hours': time_period,
            'include_inactive': include_inactive,
            'overall_summary': overall_summary,
            'category_statistics': category_statistics,
            'generated_at': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get category-based statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve category-based statistics: {str(e)}")


# Helper functions

def _calculate_category_effectiveness(category_info: Dict, blocking_stats: Dict) -> float:
    """Calculate effectiveness score for a category (0-100)"""
    try:
        active_rules = category_info.get('active_rules', 0)
        blocked_queries = blocking_stats.get('blocked_queries', 0)
        
        if active_rules == 0:
            return 0.0
        
        # Simple effectiveness calculation: blocks per rule
        blocks_per_rule = blocked_queries / active_rules
        
        # Normalize to 0-100 scale (assuming 10 blocks per rule is excellent)
        effectiveness = min(blocks_per_rule * 10, 100)
        
        return round(effectiveness, 2)
        
    except Exception:
        return 0.0


async def _generate_threat_report_csv(report_data: Dict) -> str:
    """Generate CSV format for threat detection report"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Threat Detection Report'])
    writer.writerow(['Generated:', report_data['generated_at']])
    writer.writerow(['Period:', f"{report_data['report_period']['days']} days"])
    writer.writerow([])
    
    # Executive summary
    writer.writerow(['Executive Summary'])
    summary = report_data['executive_summary']
    for key, value in summary.items():
        writer.writerow([key.replace('_', ' ').title(), value])
    writer.writerow([])
    
    # Top threat sources
    writer.writerow(['Top Threat Sources'])
    writer.writerow(['Domain', 'Blocks', 'Category', 'First Seen', 'Last Seen'])
    for threat in report_data.get('top_threat_sources', []):
        writer.writerow([
            threat.get('domain', ''),
            threat.get('block_count', 0),
            threat.get('category', ''),
            threat.get('first_seen', ''),
            threat.get('last_seen', '')
        ])
    
    return output.getvalue()


# RPZ Rule Templates Endpoints

@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_rpz_templates(
    category: Optional[str] = Query(None, description="Filter templates by category"),
    current_user: dict = Depends(get_current_user)
):
    """List available RPZ rule templates"""
    try:
        # Define common RPZ rule templates
        templates = [
            {
                "id": "malware-block",
                "name": "Malware Domain Block",
                "description": "Block known malware domains",
                "category": "malware",
                "zone": "malware",
                "action": "block",
                "domains": ["example-malware.com"],
                "redirect_target": None
            },
            {
                "id": "phishing-block",
                "name": "Phishing Domain Block", 
                "description": "Block phishing and fraudulent websites",
                "category": "phishing",
                "zone": "phishing",
                "action": "block",
                "domains": ["example-phishing.com"],
                "redirect_target": None
            },
            {
                "id": "social-media-block",
                "name": "Social Media Block",
                "description": "Block social media platforms",
                "category": "social_media", 
                "zone": "social-media",
                "action": "block",
                "domains": ["facebook.com", "twitter.com", "instagram.com"],
                "redirect_target": None
            },
            {
                "id": "adult-content-block",
                "name": "Adult Content Block",
                "description": "Block adult and inappropriate content",
                "category": "adult",
                "zone": "adult", 
                "action": "block",
                "domains": ["example-adult.com"],
                "redirect_target": None
            },
            {
                "id": "gambling-block",
                "name": "Gambling Sites Block",
                "description": "Block gambling and betting websites",
                "category": "gambling",
                "zone": "gambling",
                "action": "block", 
                "domains": ["example-casino.com"],
                "redirect_target": None
            },
            {
                "id": "redirect-template",
                "name": "Redirect Template",
                "description": "Redirect blocked domains to a warning page",
                "category": "custom",
                "zone": "custom",
                "action": "redirect",
                "domains": ["example.com"],
                "redirect_target": "blocked.example.com"
            }
        ]
        
        # Filter by category if specified
        if category:
            templates = [t for t in templates if t["category"] == category]
            
        return templates
        
    except Exception as e:
        logger.error(f"Failed to list RPZ templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list RPZ templates")


@router.post("/templates", response_model=Dict[str, Any])
async def create_rpz_template(
    template_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Create a new RPZ rule template"""
    try:
        # For now, return the template data as-is since we're using static templates
        # In a full implementation, this would save to database
        template_id = f"custom-{datetime.utcnow().timestamp()}"
        template = {
            "id": template_id,
            **template_data
        }
        
        logger.info(f"Created RPZ template: {template_id}")
        return template
        
    except Exception as e:
        logger.error(f"Failed to create RPZ template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create RPZ template")


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_rpz_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific RPZ rule template"""
    try:
        # This would normally fetch from database
        # For now, return a placeholder
        template = {
            "id": template_id,
            "name": "Template",
            "description": "Template description",
            "category": "custom",
            "zone": "custom",
            "action": "block",
            "domains": [],
            "redirect_target": None
        }
        
        return template
        
    except Exception as e:
        logger.error(f"Failed to get RPZ template {template_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Template not found")


@router.put("/templates/{template_id}", response_model=Dict[str, Any])
async def update_rpz_template(
    template_id: str,
    template_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update an RPZ rule template"""
    try:
        # This would normally update in database
        template = {
            "id": template_id,
            **template_data
        }
        
        logger.info(f"Updated RPZ template: {template_id}")
        return template
        
    except Exception as e:
        logger.error(f"Failed to update RPZ template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update RPZ template")


@router.delete("/templates/{template_id}")
async def delete_rpz_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an RPZ rule template"""
    try:
        # This would normally delete from database
        logger.info(f"Deleted RPZ template: {template_id}")
        return {"message": "Template deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete RPZ template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete RPZ template")


# Helper function for background BIND configuration updates
async def _update_bind_configuration(feed_type: str):
    """Update BIND9 configuration for a specific feed type"""
    try:
        bind_service = BindService()
        await bind_service.update_rpz_zone_file(feed_type)
        await bind_service.reload_configuration()
        logger.info(f"Updated BIND9 configuration for feed type: {feed_type}")
    except Exception as e:
        logger.error(f"Failed to update BIND9 configuration for {feed_type}: {str(e)}")