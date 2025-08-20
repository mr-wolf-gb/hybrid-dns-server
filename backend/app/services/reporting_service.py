"""
Reporting Service for DNS Server Analytics and Reports

This service handles automated report generation, customizable templates,
scheduling, and export functionality.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import csv
import io
from jinja2 import Template, Environment, FileSystemLoader
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.database import get_db
from app.models.dns import Zone, DNSRecord
from app.models.security import RPZRule, ThreatFeed
from app.models.system import SystemConfig, ForwarderHealth
from app.services.monitoring_service import MonitoringService
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class ReportTemplate:
    """Report template configuration"""
    
    def __init__(self, template_id: str, name: str, description: str, 
                 template_content: str, parameters: Dict[str, Any]):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.template_content = template_content
        self.parameters = parameters
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class ReportSchedule:
    """Report schedule configuration"""
    
    def __init__(self, schedule_id: str, template_id: str, name: str,
                 frequency: str, parameters: Dict[str, Any], 
                 recipients: List[str], enabled: bool = True):
        self.schedule_id = schedule_id
        self.template_id = template_id
        self.name = name
        self.frequency = frequency  # daily, weekly, monthly
        self.parameters = parameters
        self.recipients = recipients
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.last_run = None
        self.next_run = self._calculate_next_run()
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.utcnow()
        if self.frequency == "daily":
            return now + timedelta(days=1)
        elif self.frequency == "weekly":
            return now + timedelta(weeks=1)
        elif self.frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(hours=1)

class ReportingService:
    """Service for managing reports, templates, and scheduling"""
    
    def __init__(self):
        self.templates: Dict[str, ReportTemplate] = {}
        self.schedules: Dict[str, ReportSchedule] = {}
        self.monitoring_service = MonitoringService()
        self.analytics_service = AnalyticsService()
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default report templates"""
        
        # DNS Zone Summary Report
        zone_summary_template = """
# DNS Zone Summary Report
Generated: {{ report_date }}
Period: {{ start_date }} to {{ end_date }}

## Zone Statistics
- Total Zones: {{ total_zones }}
- Active Zones: {{ active_zones }}
- Inactive Zones: {{ inactive_zones }}

## Zone Details
{% for zone in zones %}
### {{ zone.name }}
- Type: {{ zone.zone_type }}
- Status: {{ zone.status }}
- Records: {{ zone.record_count }}
- Last Modified: {{ zone.updated_at }}
{% endfor %}

## Top Queried Zones
{% for zone in top_zones %}
- {{ zone.name }}: {{ zone.query_count }} queries
{% endfor %}
"""
        
        self.add_template(
            "zone_summary",
            "DNS Zone Summary",
            "Comprehensive summary of DNS zones and their statistics",
            zone_summary_template,
            {
                "include_inactive": False,
                "top_zones_limit": 10,
                "include_records": True
            }
        )
        
        # Security Report Template
        security_template = """
# DNS Security Report
Generated: {{ report_date }}
Period: {{ start_date }} to {{ end_date }}

## RPZ Statistics
- Total Rules: {{ total_rpz_rules }}
- Active Rules: {{ active_rpz_rules }}
- Blocked Queries: {{ blocked_queries }}
- Block Rate: {{ block_rate }}%

## Threat Categories
{% for category in threat_categories %}
- {{ category.name }}: {{ category.rule_count }} rules, {{ category.blocks }} blocks
{% endfor %}

## Top Blocked Domains
{% for domain in top_blocked %}
- {{ domain.name }}: {{ domain.block_count }} blocks
{% endfor %}

## Recent Threats
{% for threat in recent_threats %}
- {{ threat.domain }}: {{ threat.category }} ({{ threat.detected_at }})
{% endfor %}
"""
        
        self.add_template(
            "security_report",
            "DNS Security Report",
            "Security analysis including RPZ statistics and threat detection",
            security_template,
            {
                "include_threat_details": True,
                "top_blocked_limit": 20,
                "recent_threats_days": 7
            }
        )
        
        # Performance Report Template
        performance_template = """
# DNS Performance Report
Generated: {{ report_date }}
Period: {{ start_date }} to {{ end_date }}

## Query Statistics
- Total Queries: {{ total_queries }}
- Average Response Time: {{ avg_response_time }}ms
- Success Rate: {{ success_rate }}%
- Error Rate: {{ error_rate }}%

## Forwarder Performance
{% for forwarder in forwarders %}
### {{ forwarder.name }}
- Status: {{ forwarder.status }}
- Response Time: {{ forwarder.avg_response_time }}ms
- Success Rate: {{ forwarder.success_rate }}%
- Queries Forwarded: {{ forwarder.query_count }}
{% endfor %}

## Performance Trends
- Peak Query Time: {{ peak_time }}
- Slowest Queries: {{ slowest_queries }}
- Most Active Clients: {{ top_clients }}
"""
        
        self.add_template(
            "performance_report",
            "DNS Performance Report",
            "Performance metrics and forwarder statistics",
            performance_template,
            {
                "include_trends": True,
                "performance_threshold": 100,
                "top_clients_limit": 10
            }
        )
    
    def add_template(self, template_id: str, name: str, description: str,
                    template_content: str, parameters: Dict[str, Any]) -> ReportTemplate:
        """Add a new report template"""
        template = ReportTemplate(template_id, name, description, template_content, parameters)
        self.templates[template_id] = template
        logger.info(f"Added report template: {name}")
        return template
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get a report template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[ReportTemplate]:
        """List all available report templates"""
        return list(self.templates.values())
    
    def update_template(self, template_id: str, **kwargs) -> Optional[ReportTemplate]:
        """Update an existing report template"""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        logger.info(f"Updated report template: {template_id}")
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a report template"""
        if template_id in self.templates:
            del self.templates[template_id]
            logger.info(f"Deleted report template: {template_id}")
            return True
        return False
    
    async def generate_report(self, template_id: str, parameters: Optional[Dict[str, Any]] = None,
                            start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate a report using the specified template"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Merge parameters
        report_params = template.parameters.copy()
        if parameters:
            report_params.update(parameters)
        
        # Collect report data
        report_data = await self._collect_report_data(template_id, report_params, start_date, end_date)
        
        # Render template
        jinja_template = Template(template.template_content)
        report_content = jinja_template.render(
            report_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            **report_data
        )
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "generated_at": datetime.utcnow(),
            "start_date": start_date,
            "end_date": end_date,
            "parameters": report_params,
            "content": report_content,
            "data": report_data
        }
    
    async def _collect_report_data(self, template_id: str, parameters: Dict[str, Any],
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect data for report generation"""
        data = {}
        
        # Get database session
        db = next(get_db())
        
        try:
            if template_id == "zone_summary":
                data.update(await self._collect_zone_data(db, parameters, start_date, end_date))
            elif template_id == "security_report":
                data.update(await self._collect_security_data(db, parameters, start_date, end_date))
            elif template_id == "performance_report":
                data.update(await self._collect_performance_data(db, parameters, start_date, end_date))
            
            return data
            
        finally:
            db.close()
    
    async def _collect_zone_data(self, db: Session, parameters: Dict[str, Any],
                               start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect zone-related data for reports"""
        
        # Basic zone statistics
        total_zones = db.query(Zone).count()
        active_zones = db.query(Zone).filter(Zone.enabled == True).count()
        inactive_zones = total_zones - active_zones
        
        # Zone details
        zones_query = db.query(Zone)
        if not parameters.get("include_inactive", False):
            zones_query = zones_query.filter(Zone.enabled == True)
        
        zones = zones_query.all()
        zone_data = []
        
        for zone in zones:
            record_count = db.query(DNSRecord).filter(DNSRecord.zone_id == zone.id).count()
            zone_data.append({
                "name": zone.name,
                "zone_type": zone.zone_type,
                "status": "Active" if zone.enabled else "Inactive",
                "record_count": record_count,
                "updated_at": zone.updated_at.strftime("%Y-%m-%d %H:%M:%S") if zone.updated_at else "N/A"
            })
        
        # Get query statistics from monitoring service
        query_stats = await self.monitoring_service.get_zone_query_stats(start_date, end_date)
        top_zones = sorted(query_stats.items(), key=lambda x: x[1], reverse=True)[:parameters.get("top_zones_limit", 10)]
        top_zones_data = [{"name": name, "query_count": count} for name, count in top_zones]
        
        return {
            "total_zones": total_zones,
            "active_zones": active_zones,
            "inactive_zones": inactive_zones,
            "zones": zone_data,
            "top_zones": top_zones_data
        }
    
    async def _collect_security_data(self, db: Session, parameters: Dict[str, Any],
                                   start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect security-related data for reports"""
        
        # RPZ statistics
        total_rpz_rules = db.query(RPZRule).count()
        active_rpz_rules = db.query(RPZRule).filter(RPZRule.enabled == True).count()
        
        # Get blocked query statistics
        blocked_stats = await self.monitoring_service.get_blocked_query_stats(start_date, end_date)
        blocked_queries = blocked_stats.get("total_blocked", 0)
        total_queries = blocked_stats.get("total_queries", 1)
        block_rate = round((blocked_queries / total_queries) * 100, 2) if total_queries > 0 else 0
        
        # Threat categories
        categories = db.query(RPZRule.category, func.count(RPZRule.id)).group_by(RPZRule.category).all()
        threat_categories = []
        for category, rule_count in categories:
            category_blocks = blocked_stats.get("categories", {}).get(category, 0)
            threat_categories.append({
                "name": category,
                "rule_count": rule_count,
                "blocks": category_blocks
            })
        
        # Top blocked domains
        top_blocked_data = blocked_stats.get("top_blocked", [])[:parameters.get("top_blocked_limit", 20)]
        top_blocked = [{"name": domain, "block_count": count} for domain, count in top_blocked_data]
        
        # Recent threats
        recent_days = parameters.get("recent_threats_days", 7)
        recent_date = end_date - timedelta(days=recent_days)
        recent_threats_data = await self.monitoring_service.get_recent_threats(recent_date, end_date)
        recent_threats = [
            {
                "domain": threat["domain"],
                "category": threat["category"],
                "detected_at": threat["detected_at"].strftime("%Y-%m-%d %H:%M:%S")
            }
            for threat in recent_threats_data
        ]
        
        return {
            "total_rpz_rules": total_rpz_rules,
            "active_rpz_rules": active_rpz_rules,
            "blocked_queries": blocked_queries,
            "block_rate": block_rate,
            "threat_categories": threat_categories,
            "top_blocked": top_blocked,
            "recent_threats": recent_threats
        }
    
    async def _collect_performance_data(self, db: Session, parameters: Dict[str, Any],
                                      start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect performance-related data for reports"""
        
        # Get performance statistics
        perf_stats = await self.monitoring_service.get_performance_stats(start_date, end_date)
        
        # Forwarder performance
        forwarder_stats = await self.monitoring_service.get_forwarder_performance(start_date, end_date)
        forwarders = []
        
        for forwarder_id, stats in forwarder_stats.items():
            forwarders.append({
                "name": stats.get("name", f"Forwarder {forwarder_id}"),
                "status": stats.get("status", "Unknown"),
                "avg_response_time": round(stats.get("avg_response_time", 0), 2),
                "success_rate": round(stats.get("success_rate", 0), 2),
                "query_count": stats.get("query_count", 0)
            })
        
        return {
            "total_queries": perf_stats.get("total_queries", 0),
            "avg_response_time": round(perf_stats.get("avg_response_time", 0), 2),
            "success_rate": round(perf_stats.get("success_rate", 0), 2),
            "error_rate": round(perf_stats.get("error_rate", 0), 2),
            "forwarders": forwarders,
            "peak_time": perf_stats.get("peak_time", "N/A"),
            "slowest_queries": perf_stats.get("slowest_queries", []),
            "top_clients": perf_stats.get("top_clients", [])
        }
    
    def add_schedule(self, schedule_id: str, template_id: str, name: str,
                    frequency: str, parameters: Dict[str, Any], 
                    recipients: List[str], enabled: bool = True) -> ReportSchedule:
        """Add a new report schedule"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        schedule = ReportSchedule(schedule_id, template_id, name, frequency, 
                                parameters, recipients, enabled)
        self.schedules[schedule_id] = schedule
        logger.info(f"Added report schedule: {name}")
        return schedule
    
    def get_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        """Get a report schedule by ID"""
        return self.schedules.get(schedule_id)
    
    def list_schedules(self) -> List[ReportSchedule]:
        """List all report schedules"""
        return list(self.schedules.values())
    
    def update_schedule(self, schedule_id: str, **kwargs) -> Optional[ReportSchedule]:
        """Update an existing report schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        if "frequency" in kwargs:
            schedule.next_run = schedule._calculate_next_run()
        
        logger.info(f"Updated report schedule: {schedule_id}")
        return schedule
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a report schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            logger.info(f"Deleted report schedule: {schedule_id}")
            return True
        return False
    
    async def run_scheduled_reports(self):
        """Run all scheduled reports that are due"""
        now = datetime.utcnow()
        
        for schedule in self.schedules.values():
            if not schedule.enabled:
                continue
            
            if schedule.next_run and now >= schedule.next_run:
                try:
                    logger.info(f"Running scheduled report: {schedule.name}")
                    
                    # Generate report
                    report = await self.generate_report(
                        schedule.template_id,
                        schedule.parameters
                    )
                    
                    # Export report
                    exported_report = await self.export_report(report, "pdf")
                    
                    # Send to recipients (placeholder for email/notification service)
                    await self._send_report_to_recipients(exported_report, schedule.recipients)
                    
                    # Update schedule
                    schedule.last_run = now
                    schedule.next_run = schedule._calculate_next_run()
                    
                    logger.info(f"Completed scheduled report: {schedule.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to run scheduled report {schedule.name}: {str(e)}")
    
    async def _send_report_to_recipients(self, report_data: bytes, recipients: List[str]):
        """Send report to recipients (placeholder for email service)"""
        # This would integrate with an email service or notification system
        logger.info(f"Report sent to {len(recipients)} recipients")
    
    async def export_report(self, report: Dict[str, Any], format: str = "pdf") -> bytes:
        """Export report in specified format"""
        
        if format.lower() == "json":
            return json.dumps(report, default=str, indent=2).encode('utf-8')
        
        elif format.lower() == "csv":
            # Convert report data to CSV format
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["Report", report["template_name"]])
            writer.writerow(["Generated", report["generated_at"]])
            writer.writerow(["Period", f"{report['start_date']} to {report['end_date']}"])
            writer.writerow([])
            
            # Write content (simplified)
            content_lines = report["content"].split('\n')
            for line in content_lines:
                writer.writerow([line])
            
            return output.getvalue().encode('utf-8')
        
        elif format.lower() == "html":
            # Convert markdown-like content to HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{report['template_name']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1, h2, h3 {{ color: #333; }}
                    pre {{ background: #f5f5f5; padding: 10px; }}
                </style>
            </head>
            <body>
                <pre>{report['content']}</pre>
            </body>
            </html>
            """
            return html_content.encode('utf-8')
        
        elif format.lower() == "pdf":
            # For PDF generation, you would use a library like weasyprint or reportlab
            # This is a placeholder implementation
            return f"PDF Report: {report['template_name']}\n{report['content']}".encode('utf-8')
        
        else:
            # Default to plain text
            return report["content"].encode('utf-8')
    
    async def get_report_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of generated reports"""
        # This would typically be stored in database
        # For now, return placeholder data
        return [
            {
                "id": "report_1",
                "template_name": "DNS Zone Summary",
                "generated_at": datetime.utcnow() - timedelta(days=1),
                "status": "completed",
                "size": "2.5 KB"
            }
        ]
    
    def get_report_statistics(self) -> Dict[str, Any]:
        """Get reporting system statistics"""
        return {
            "total_templates": len(self.templates),
            "total_schedules": len(self.schedules),
            "active_schedules": len([s for s in self.schedules.values() if s.enabled]),
            "next_scheduled_run": min([s.next_run for s in self.schedules.values() 
                                     if s.enabled and s.next_run], default=None)
        }

# Global reporting service instance
reporting_service = ReportingService()