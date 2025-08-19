"""
RPZ management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import csv
import io

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.security import (
    RPZRuleCreate, RPZRuleUpdate, RPZRule as RPZRuleSchema,
    RPZRuleImportResult, RPZAction, RPZCategory, RPZCategoryStatus,
    RPZCategoryToggleResult, RPZBulkCategorizeRequest, RPZBulkCategorizeResult,
    ThreatFeedCreate, ThreatFeedUpdate, ThreatFeed as ThreatFeedSchema,
    ThreatFeedUpdateResult, BulkThreatFeedUpdateResult, ThreatFeedStatus
)
from ...services.rpz_service import RPZService
from ...services.threat_feed_service import ThreatFeedService
from ...services.bind_service import BindService
from ...core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/rules", response_model=List[RPZRuleSchema])
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
    return rules


@router.post("/rules", response_model=RPZRuleSchema)
async def create_rpz_rule(
    rule_data: RPZRuleCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService()
    
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
    bind_service = BindService()
    
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


@router.post("/rules/bulk-import", response_model=RPZRuleImportResult)
async def bulk_import_rules(
    rpz_zone: str = Query(..., description="RPZ zone category for imported rules"),
    action: RPZAction = Query(RPZAction.BLOCK, description="Default action for imported rules"),
    source: str = Query("bulk_import", description="Source identifier for imported rules"),
    redirect_target: Optional[str] = Query(None, description="Redirect target (required if action is redirect)"),
    file: UploadFile = File(..., description="File containing domains to import"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk import RPZ rules from file"""
    logger.info(f"Starting bulk import for RPZ zone: {rpz_zone}")
    
    # Validate redirect target if action is redirect
    if action == RPZAction.REDIRECT and not redirect_target:
        raise HTTPException(
            status_code=400, 
            detail="Redirect target is required when action is redirect"
        )
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = file.filename.lower().split('.')[-1]
    if file_extension not in ['txt', 'csv', 'json']:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Supported formats: txt, csv, json"
        )
    
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parse domains based on file type
        domains = []
        if file_extension == 'json':
            domains = await _parse_json_file(content_str)
        elif file_extension == 'csv':
            domains = await _parse_csv_file(content_str)
        else:  # txt
            domains = await _parse_txt_file(content_str)
        
        if not domains:
            raise HTTPException(status_code=400, detail="No valid domains found in file")
        
        # Prepare rule data
        rules_data = []
        for domain in domains:
            rule_data = {
                'domain': domain.strip().lower(),
                'rpz_zone': rpz_zone,
                'action': action.value,
                'source': source
            }
            if redirect_target:
                rule_data['redirect_target'] = redirect_target
            
            rules_data.append(rule_data)
        
        # Perform bulk import
        rpz_service = RPZService(db)
        created_count, error_count, errors = await rpz_service.bulk_create_rules(
            rules_data, source=source
        )
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, rpz_zone)
        
        # Prepare result
        result = RPZRuleImportResult(
            total_processed=len(rules_data),
            rules_added=created_count,
            rules_updated=0,  # Bulk create doesn't update existing rules
            rules_skipped=error_count,
            errors=errors[:50]  # Limit errors to first 50 to avoid huge responses
        )
        
        logger.info(f"Bulk import completed: {created_count} created, {error_count} errors")
        return result
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding not supported. Please use UTF-8.")
    except Exception as e:
        logger.error(f"Bulk import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/rules/bulk-import-json", response_model=RPZRuleImportResult)
async def bulk_import_rules_json(
    rules: List[RPZRuleCreate],
    source: str = Query("bulk_import", description="Source identifier for imported rules"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk import RPZ rules from JSON payload"""
    logger.info(f"Starting bulk JSON import of {len(rules)} rules")
    
    if not rules:
        raise HTTPException(status_code=400, detail="No rules provided")
    
    if len(rules) > 10000:  # Reasonable limit
        raise HTTPException(status_code=400, detail="Too many rules. Maximum 10,000 rules per import.")
    
    try:
        # Convert Pydantic models to dictionaries
        rules_data = []
        for rule in rules:
            rule_dict = rule.model_dump()
            rule_dict['source'] = source
            rules_data.append(rule_dict)
        
        # Perform bulk import
        rpz_service = RPZService(db)
        created_count, error_count, errors = await rpz_service.bulk_create_rules(
            rules_data, source=source
        )
        
        # Get unique RPZ zones for BIND9 update
        rpz_zones = list(set(rule.rpz_zone for rule in rules))
        
        # Schedule BIND9 configuration updates in background
        for zone in rpz_zones:
            background_tasks.add_task(_update_bind_configuration, zone)
        
        # Prepare result
        result = RPZRuleImportResult(
            total_processed=len(rules_data),
            rules_added=created_count,
            rules_updated=0,
            rules_skipped=error_count,
            errors=errors[:50]  # Limit errors to first 50
        )
        
        logger.info(f"Bulk JSON import completed: {created_count} created, {error_count} errors")
        return result
        
    except Exception as e:
        logger.error(f"Bulk JSON import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/rules/statistics")
async def get_rpz_statistics(
    rpz_zone: Optional[str] = Query(None, description="Specific RPZ zone to get statistics for"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get RPZ rules statistics"""
    rpz_service = RPZService(db)
    statistics = await rpz_service.get_zone_statistics(rpz_zone)
    return statistics


# Enhanced Statistics and Reporting Endpoints

@router.get("/statistics/comprehensive")
async def get_comprehensive_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive RPZ statistics across all categories"""
    rpz_service = RPZService(db)
    statistics = await rpz_service.get_comprehensive_statistics()
    return statistics


@router.get("/reports/activity")
async def get_activity_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in the report"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get activity report for the specified number of days"""
    rpz_service = RPZService(db)
    report = await rpz_service.get_activity_report(days)
    return report


@router.get("/reports/effectiveness")
async def get_effectiveness_report(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get effectiveness report showing rule distribution and coverage"""
    rpz_service = RPZService(db)
    report = await rpz_service.get_effectiveness_report()
    return report


@router.get("/reports/trends")
async def get_trend_analysis(
    days: int = Query(90, ge=7, le=365, description="Number of days to analyze for trends"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get trend analysis for rule creation and management over time"""
    rpz_service = RPZService(db)
    report = await rpz_service.get_trend_analysis(days)
    return report


@router.get("/reports/security-impact")
async def get_security_impact_report(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get security impact report showing protection coverage"""
    rpz_service = RPZService(db)
    report = await rpz_service.get_security_impact_report()
    return report


@router.get("/reports/export")
async def export_statistics_report(
    report_type: str = Query(
        "comprehensive", 
        regex="^(comprehensive|activity|effectiveness|trends|security)$",
        description="Type of report to export"
    ),
    format: str = Query(
        "json",
        regex="^(json)$", 
        description="Export format (currently only JSON supported)"
    ),
    days: Optional[int] = Query(
        None, 
        ge=1, 
        le=365, 
        description="Number of days for time-based reports (activity, trends)"
    ),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Export statistics report in specified format"""
    rpz_service = RPZService(db)
    
    try:
        # For time-based reports, use the days parameter if provided
        if report_type in ['activity', 'trends'] and days:
            if report_type == 'activity':
                data = await rpz_service.get_activity_report(days)
            else:  # trends
                data = await rpz_service.get_trend_analysis(days)
            
            export_data = {
                'report_type': report_type,
                'export_format': format,
                'exported_at': datetime.utcnow().isoformat(),
                'data': data
            }
        else:
            export_data = await rpz_service.export_statistics_report(report_type, format)
        
        return export_data
        
    except Exception as e:
        if "Invalid report type" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        logger.error(f"Report export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/statistics/summary")
async def get_statistics_summary(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a quick summary of key RPZ statistics"""
    rpz_service = RPZService(db)
    
    # Get basic statistics
    overall_stats = await rpz_service.get_zone_statistics()
    
    # Get category count
    categories = await rpz_service.get_available_categories()
    active_categories = 0
    
    for category in categories:
        category_rules = await rpz_service.count_rules(rpz_zone=category, active_only=True)
        if category_rules > 0:
            active_categories += 1
    
    # Get recent activity (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    if hasattr(rpz_service, 'is_async') and rpz_service.is_async:
        from sqlalchemy import select, func
        recent_query = select(func.count(rpz_service.model.id)).filter(
            rpz_service.model.created_at >= seven_days_ago
        )
        recent_result = await rpz_service.db.execute(recent_query)
        recent_rules = recent_result.scalar()
    else:
        from sqlalchemy import func
        recent_rules = rpz_service.db.query(func.count(rpz_service.model.id)).filter(
            rpz_service.model.created_at >= seven_days_ago
        ).scalar()
    
    summary = {
        'total_rules': overall_stats.get('total_rules', 0),
        'active_rules': overall_stats.get('active_rules', 0),
        'total_categories': len(categories),
        'active_categories': active_categories,
        'recent_activity': {
            'rules_added_last_7_days': recent_rules
        },
        'top_actions': overall_stats.get('rules_by_action', {}),
        'generated_at': datetime.utcnow().isoformat()
    }
    
    return summary


# Category Management Endpoints

@router.get("/categories", response_model=List[RPZCategory])
async def list_categories(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get information about all available RPZ categories"""
    rpz_service = RPZService(db)
    categories = await rpz_service.get_all_categories_info()
    return categories


@router.get("/categories/{category}", response_model=RPZCategory)
async def get_category_info(
    category: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific category"""
    rpz_service = RPZService(db)
    
    try:
        category_info = await rpz_service.get_category_info(category)
        return category_info
    except Exception as e:
        if "Invalid category" in str(e):
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category}/status", response_model=RPZCategoryStatus)
async def get_category_status(
    category: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get the current status of a category"""
    rpz_service = RPZService(db)
    
    try:
        status = await rpz_service.get_category_status(category)
        return status
    except Exception as e:
        if "Invalid category" in str(e):
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories/{category}/enable", response_model=RPZCategoryToggleResult)
async def enable_category(
    category: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Enable all rules in a category"""
    rpz_service = RPZService(db)
    
    try:
        updated_count, errors = await rpz_service.enable_category(category)
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, category)
        
        result = RPZCategoryToggleResult(
            category=category,
            action="enabled",
            rules_affected=updated_count,
            errors=errors
        )
        
        return result
        
    except Exception as e:
        if "Invalid category" in str(e):
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories/{category}/disable", response_model=RPZCategoryToggleResult)
async def disable_category(
    category: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Disable all rules in a category"""
    rpz_service = RPZService(db)
    
    try:
        updated_count, errors = await rpz_service.disable_category(category)
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, category)
        
        result = RPZCategoryToggleResult(
            category=category,
            action="disabled",
            rules_affected=updated_count,
            errors=errors
        )
        
        return result
        
    except Exception as e:
        if "Invalid category" in str(e):
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category}/rules", response_model=List[RPZRuleSchema])
async def list_category_rules(
    category: str,
    active_only: bool = Query(True),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List rules in a specific category"""
    rpz_service = RPZService(db)
    
    try:
        rules = await rpz_service.get_rules_by_category(
            category=category,
            skip=skip,
            limit=limit,
            active_only=active_only,
            action=action,
            search=search
        )
        return rules
        
    except Exception as e:
        if "Invalid category" in str(e):
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/bulk-categorize", response_model=RPZBulkCategorizeResult)
async def bulk_categorize_rules(
    request: RPZBulkCategorizeRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Move multiple rules to a different category"""
    rpz_service = RPZService(db)
    
    try:
        updated_count, error_count, errors = await rpz_service.bulk_categorize_rules(
            request.rule_ids, request.new_category
        )
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(_update_bind_configuration, request.new_category)
        
        result = RPZBulkCategorizeResult(
            total_processed=len(request.rule_ids),
            rules_updated=updated_count,
            rules_failed=error_count,
            new_category=request.new_category,
            errors=errors[:50]  # Limit errors to first 50
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Bulk categorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def _parse_json_file(content: str) -> List[str]:
    """Parse JSON file containing domains"""
    try:
        data = json.loads(content)
        
        # Handle different JSON structures
        if isinstance(data, list):
            # Simple list of domains
            if all(isinstance(item, str) for item in data):
                return data
            # List of objects with domain field
            elif all(isinstance(item, dict) and 'domain' in item for item in data):
                return [item['domain'] for item in data]
        elif isinstance(data, dict):
            # Object with domains array
            if 'domains' in data and isinstance(data['domains'], list):
                return data['domains']
            # Object with domain field
            elif 'domain' in data:
                return [data['domain']]
        
        raise ValueError("Unsupported JSON structure")
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")


async def _parse_csv_file(content: str) -> List[str]:
    """Parse CSV file containing domains"""
    domains = []
    csv_reader = csv.reader(io.StringIO(content))
    
    for row_num, row in enumerate(csv_reader, 1):
        if not row:  # Skip empty rows
            continue
        
        # Take the first column as domain
        domain = row[0].strip()
        
        # Skip header row (if it contains common header words) and comments
        if (domain and 
            not domain.startswith('#') and 
            domain.lower() not in ['domain', 'hostname', 'url', 'site']):
            domains.append(domain)
    
    return domains


async def _parse_txt_file(content: str) -> List[str]:
    """Parse text file containing domains (one per line)"""
    domains = []
    
    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Handle hosts file format (IP domain)
        if ' ' in line:
            parts = line.split()
            if len(parts) >= 2:
                # Take the second part as domain (skip IP)
                domain = parts[1].strip()
                if domain and domain != 'localhost':
                    domains.append(domain)
        else:
            # Simple domain list
            domains.append(line)
    
    return domains


async def _update_bind_configuration(rpz_zone: str):
    """Background task to update BIND9 configuration"""
    try:
        bind_service = BindService()
        await bind_service.update_rpz_zone_file(rpz_zone)
        await bind_service.reload_configuration()
        logger.info(f"BIND9 configuration updated for RPZ zone: {rpz_zone}")
    except Exception as e:
        logger.error(f"Failed to update BIND9 configuration for zone {rpz_zone}: {str(e)}")

# ===== THREAT FEED MANAGEMENT ENDPOINTS =====

@router.get("/threat-feeds", response_model=List[ThreatFeedSchema])
async def list_threat_feeds(
    feed_type: Optional[str] = Query(None, description="Filter by feed type"),
    active_only: bool = Query(True, description="Only return active feeds"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all threat feeds with filtering"""
    threat_feed_service = ThreatFeedService(db)
    feeds = await threat_feed_service.get_feeds(
        skip=skip,
        limit=limit,
        feed_type=feed_type,
        active_only=active_only
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
        logger.info(f"Created threat feed: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to create threat feed: {str(e)}")
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
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
        
        logger.info(f"Updated threat feed: {feed.name}")
        return feed
    except Exception as e:
        logger.error(f"Failed to update threat feed {feed_id}: {str(e)}")
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/threat-feeds/{feed_id}")
async def delete_threat_feed(
    feed_id: int,
    remove_rules: bool = Query(True, description="Remove associated RPZ rules"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a threat feed and optionally remove associated rules"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        # Get feed info before deletion for logging
        feed = await threat_feed_service.get_feed(feed_id)
        if not feed:
            raise HTTPException(status_code=404, detail="Threat feed not found")
        
        feed_name = feed.name
        feed_type = feed.feed_type
        
        success = await threat_feed_service.delete_feed(feed_id, remove_rules=remove_rules)
        
        if not success:
            raise HTTPException(status_code=404, detail="Threat feed not found")
        
        # Schedule BIND9 configuration update in background if rules were removed
        if remove_rules:
            background_tasks.add_task(_update_bind_configuration, feed_type)
        
        logger.info(f"Deleted threat feed: {feed_name}")
        return {"message": f"Threat feed '{feed_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete threat feed {feed_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat-feeds/{feed_id}/update", response_model=ThreatFeedUpdateResult)
async def update_threat_feed_from_source(
    feed_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a specific threat feed from its source"""
    threat_feed_service = ThreatFeedService(db)
    
    # Get the feed
    feed = await threat_feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    if not feed.is_active:
        raise HTTPException(status_code=400, detail="Cannot update inactive threat feed")
    
    try:
        # Update the feed
        result = await threat_feed_service.update_feed_from_source(feed)
        
        # Schedule BIND9 configuration update in background if successful
        if result.status == "success":
            background_tasks.add_task(_update_bind_configuration, feed.feed_type)
        
        logger.info(f"Updated threat feed {feed.name}: {result.status}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to update threat feed {feed_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat-feeds/update-all", response_model=BulkThreatFeedUpdateResult)
async def update_all_threat_feeds(
    force_update: bool = Query(False, description="Force update all feeds regardless of schedule"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update all active threat feeds"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        # Update all feeds
        result = await threat_feed_service.update_all_feeds(force_update=force_update)
        
        # Schedule BIND9 configuration updates for all affected zones
        if result.successful_updates > 0:
            # Get all active feed types for BIND9 update
            feeds = await threat_feed_service.get_feeds(active_only=True, limit=1000)
            feed_types = list(set(feed.feed_type for feed in feeds))
            
            for feed_type in feed_types:
                background_tasks.add_task(_update_bind_configuration, feed_type)
        
        logger.info(f"Bulk threat feed update completed: {result.successful_updates} successful, {result.failed_updates} failed")
        return result
        
    except Exception as e:
        logger.error(f"Bulk threat feed update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat-feeds/{feed_id}/test")
async def test_threat_feed_connectivity(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test connectivity to a threat feed without updating rules"""
    threat_feed_service = ThreatFeedService(db)
    
    # Get the feed
    feed = await threat_feed_service.get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    
    try:
        # Test connectivity
        result = await threat_feed_service.test_feed_connectivity(feed)
        
        logger.info(f"Tested threat feed {feed.name}: {'success' if result['success'] else 'failed'}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to test threat feed {feed_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat-feeds/{feed_id}/toggle")
async def toggle_threat_feed(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle the active status of a threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        feed = await threat_feed_service.toggle_feed(feed_id)
        if not feed:
            raise HTTPException(status_code=404, detail="Threat feed not found")
        
        status = "enabled" if feed.is_active else "disabled"
        logger.info(f"Threat feed {feed.name} {status}")
        
        return {
            "message": f"Threat feed '{feed.name}' {status} successfully",
            "feed": feed
        }
        
    except Exception as e:
        logger.error(f"Failed to toggle threat feed {feed_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-feeds/{feed_id}/status", response_model=ThreatFeedStatus)
async def get_threat_feed_status(
    feed_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed status information for a threat feed"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        status = await threat_feed_service.get_feed_health_status(feed_id)
        
        if 'error' in status:
            raise HTTPException(status_code=404, detail=status['error'])
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get threat feed status {feed_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-feeds/statistics")
async def get_threat_feed_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive threat feed statistics"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        statistics = await threat_feed_service.get_feed_statistics()
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to get threat feed statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-feeds/due-for-update")
async def get_feeds_due_for_update(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get threat feeds that are due for update"""
    threat_feed_service = ThreatFeedService(db)
    
    try:
        feeds = await threat_feed_service.get_feeds_due_for_update()
        
        return {
            "feeds_due_for_update": len(feeds),
            "feeds": [
                {
                    "id": feed.id,
                    "name": feed.name,
                    "feed_type": feed.feed_type,
                    "last_updated": feed.last_updated,
                    "update_frequency": feed.update_frequency,
                    "last_update_status": feed.last_update_status
                }
                for feed in feeds
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get feeds due for update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))