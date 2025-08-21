"""
Reports API Endpoints

Provides endpoints for report generation, template management,
scheduling, and export functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
import io

from app.services.reporting_service import reporting_service
from app.services.analytics_service import analytics_service
from app.core.dependencies import get_current_user
from app.schemas.reports import (
    ReportTemplateCreate, ReportTemplateUpdate, ReportTemplate,
    ReportScheduleCreate, ReportScheduleUpdate, ReportSchedule,
    ReportGenerate, ReportResponse, ReportExport
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Report Templates Endpoints

@router.get("/templates", response_model=List[ReportTemplate])
async def list_report_templates(
    current_user: dict = Depends(get_current_user)
):
    """List all available report templates"""
    try:
        templates = reporting_service.list_templates()
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "created_at": t.created_at,
                "updated_at": t.updated_at
            }
            for t in templates
        ]
    except Exception as e:
        logger.error(f"Failed to list report templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list report templates")

@router.post("/templates", response_model=ReportTemplate)
async def create_report_template(
    template_data: ReportTemplateCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new report template"""
    try:
        template = reporting_service.add_template(
            template_data.template_id,
            template_data.name,
            template_data.description,
            template_data.template_content,
            template_data.parameters
        )
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "template_content": template.template_content,
            "parameters": template.parameters,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
    except Exception as e:
        logger.error(f"Failed to create report template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create report template")

@router.get("/templates/{template_id}", response_model=ReportTemplate)
async def get_report_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific report template"""
    template = reporting_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "template_content": template.template_content,
        "parameters": template.parameters,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }

@router.put("/templates/{template_id}", response_model=ReportTemplate)
async def update_report_template(
    template_id: str,
    template_data: ReportTemplateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing report template"""
    template = reporting_service.update_template(
        template_id,
        **template_data.dict(exclude_unset=True)
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "template_content": template.template_content,
        "parameters": template.parameters,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }

@router.delete("/templates/{template_id}")
async def delete_report_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a report template"""
    success = reporting_service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report template not found")
    
    return {"message": "Report template deleted successfully"}

# Report Generation Endpoints

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    report_request: ReportGenerate,
    current_user: dict = Depends(get_current_user)
):
    """Generate a report using the specified template"""
    try:
        report = await reporting_service.generate_report(
            report_request.template_id,
            report_request.parameters,
            report_request.start_date,
            report_request.end_date
        )
        
        return {
            "report_id": f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "template_id": report["template_id"],
            "template_name": report["template_name"],
            "generated_at": report["generated_at"],
            "start_date": report["start_date"],
            "end_date": report["end_date"],
            "parameters": report["parameters"],
            "content": report["content"],
            "data": report["data"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

@router.post("/export")
async def export_report(
    export_request: ReportExport,
    current_user: dict = Depends(get_current_user)
):
    """Export a report in the specified format"""
    try:
        # First generate the report
        report = await reporting_service.generate_report(
            export_request.template_id,
            export_request.parameters,
            export_request.start_date,
            export_request.end_date
        )
        
        # Export in requested format
        exported_data = await reporting_service.export_report(report, export_request.format)
        
        # Determine content type and filename
        content_type_map = {
            "json": "application/json",
            "csv": "text/csv",
            "html": "text/html",
            "pdf": "application/pdf",
            "txt": "text/plain"
        }
        
        content_type = content_type_map.get(export_request.format.lower(), "text/plain")
        filename = f"report_{export_request.template_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_request.format.lower()}"
        
        return StreamingResponse(
            io.BytesIO(exported_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to export report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export report")

# Report Scheduling Endpoints

@router.get("/schedules", response_model=List[ReportSchedule])
async def list_report_schedules(
    current_user: dict = Depends(get_current_user)
):
    """List all report schedules"""
    try:
        schedules = reporting_service.list_schedules()
        return [
            {
                "schedule_id": s.schedule_id,
                "template_id": s.template_id,
                "name": s.name,
                "frequency": s.frequency,
                "parameters": s.parameters,
                "recipients": s.recipients,
                "enabled": s.enabled,
                "created_at": s.created_at,
                "last_run": s.last_run,
                "next_run": s.next_run
            }
            for s in schedules
        ]
    except Exception as e:
        logger.error(f"Failed to list report schedules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list report schedules")

@router.post("/schedules", response_model=ReportSchedule)
async def create_report_schedule(
    schedule_data: ReportScheduleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new report schedule"""
    try:
        schedule = reporting_service.add_schedule(
            schedule_data.schedule_id,
            schedule_data.template_id,
            schedule_data.name,
            schedule_data.frequency,
            schedule_data.parameters,
            schedule_data.recipients,
            schedule_data.enabled
        )
        
        return {
            "schedule_id": schedule.schedule_id,
            "template_id": schedule.template_id,
            "name": schedule.name,
            "frequency": schedule.frequency,
            "parameters": schedule.parameters,
            "recipients": schedule.recipients,
            "enabled": schedule.enabled,
            "created_at": schedule.created_at,
            "last_run": schedule.last_run,
            "next_run": schedule.next_run
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create report schedule: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create report schedule")

@router.get("/schedules/{schedule_id}", response_model=ReportSchedule)
async def get_report_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific report schedule"""
    schedule = reporting_service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    return {
        "schedule_id": schedule.schedule_id,
        "template_id": schedule.template_id,
        "name": schedule.name,
        "frequency": schedule.frequency,
        "parameters": schedule.parameters,
        "recipients": schedule.recipients,
        "enabled": schedule.enabled,
        "created_at": schedule.created_at,
        "last_run": schedule.last_run,
        "next_run": schedule.next_run
    }

@router.put("/schedules/{schedule_id}", response_model=ReportSchedule)
async def update_report_schedule(
    schedule_id: str,
    schedule_data: ReportScheduleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing report schedule"""
    schedule = reporting_service.update_schedule(
        schedule_id,
        **schedule_data.dict(exclude_unset=True)
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    return {
        "schedule_id": schedule.schedule_id,
        "template_id": schedule.template_id,
        "name": schedule.name,
        "frequency": schedule.frequency,
        "parameters": schedule.parameters,
        "recipients": schedule.recipients,
        "enabled": schedule.enabled,
        "created_at": schedule.created_at,
        "last_run": schedule.last_run,
        "next_run": schedule.next_run
    }

@router.delete("/schedules/{schedule_id}")
async def delete_report_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a report schedule"""
    success = reporting_service.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    return {"message": "Report schedule deleted successfully"}

@router.post("/schedules/{schedule_id}/run")
async def run_report_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Manually run a report schedule"""
    schedule = reporting_service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    try:
        # Generate report
        report = await reporting_service.generate_report(
            schedule.template_id,
            schedule.parameters
        )
        
        # Export report
        exported_report = await reporting_service.export_report(report, "pdf")
        
        # Update schedule run time
        schedule.last_run = datetime.utcnow()
        
        return {
            "message": "Report schedule executed successfully",
            "report_id": f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": report["generated_at"]
        }
        
    except Exception as e:
        logger.error(f"Failed to run report schedule: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to run report schedule")

# Analytics Endpoints

@router.get("/analytics/trends")
async def get_query_trends(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    interval: str = Query("hour", description="Time interval (hour, day, week)"),
    current_user: dict = Depends(get_current_user)
):
    """Get query trends analytics"""
    try:
        trends = await analytics_service.get_query_trends(start_date, end_date, interval)
        return trends
    except Exception as e:
        logger.error(f"Failed to get query trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get query trends")

@router.get("/analytics/top-domains")
async def get_top_queried_domains(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    limit: int = Query(50, description="Number of top domains to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get most queried domains"""
    try:
        top_domains = await analytics_service.get_top_queried_domains(start_date, end_date, limit)
        return {"top_domains": top_domains}
    except Exception as e:
        logger.error(f"Failed to get top domains: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get top domains")

@router.get("/analytics/clients")
async def get_client_analytics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get client-based analytics"""
    try:
        client_analytics = await analytics_service.get_client_analytics(start_date, end_date)
        return client_analytics
    except Exception as e:
        logger.error(f"Failed to get client analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get client analytics")

@router.get("/analytics/performance")
async def get_performance_analytics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get performance analytics"""
    try:
        performance = await analytics_service.get_response_time_analytics(start_date, end_date)
        return performance
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get performance analytics")

@router.get("/analytics/errors")
async def get_error_analytics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get error analytics"""
    try:
        errors = await analytics_service.get_error_analytics(start_date, end_date)
        return errors
    except Exception as e:
        logger.error(f"Failed to get error analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get error analytics")

@router.get("/analytics/security")
async def get_security_analytics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get security analytics"""
    try:
        security = await analytics_service.get_security_analytics(start_date, end_date)
        return security
    except Exception as e:
        logger.error(f"Failed to get security analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get security analytics")

@router.get("/analytics/zones")
async def get_zone_analytics(
    zone_id: Optional[int] = Query(None, description="Specific zone ID to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """Get zone analytics"""
    try:
        zones = await analytics_service.get_zone_analytics(zone_id)
        return zones
    except Exception as e:
        logger.error(f"Failed to get zone analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get zone analytics")

@router.get("/analytics/insights")
async def get_analytics_insights(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get automated analytics insights"""
    try:
        insights = await analytics_service.generate_insights(start_date, end_date)
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Failed to get analytics insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get analytics insights")

# Report History and Statistics

@router.get("/history")
async def get_report_history(
    limit: int = Query(50, description="Number of reports to return"),
    current_user: dict = Depends(get_current_user)
):
    """Get report generation history"""
    try:
        history = await reporting_service.get_report_history(limit)
        return {"reports": history}
    except Exception as e:
        logger.error(f"Failed to get report history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get report history")

@router.get("/statistics")
async def get_reporting_statistics(
    current_user: dict = Depends(get_current_user)
):
    """Get reporting system statistics"""
    try:
        stats = reporting_service.get_report_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get reporting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get reporting statistics")