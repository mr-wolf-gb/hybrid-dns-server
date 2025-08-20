"""
Pydantic schemas for reporting system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator

class ReportTemplateBase(BaseModel):
    """Base schema for report templates"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template_content: str = Field(..., description="Jinja2 template content")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Default template parameters")

class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating report templates"""
    template_id: str = Field(..., description="Unique template identifier")
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Template ID must contain only alphanumeric characters, hyphens, and underscores')
        return v

class ReportTemplateUpdate(BaseModel):
    """Schema for updating report templates"""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_content: Optional[str] = Field(None, description="Jinja2 template content")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Template parameters")

class ReportTemplate(ReportTemplateBase):
    """Schema for report template responses"""
    template_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReportScheduleBase(BaseModel):
    """Base schema for report schedules"""
    template_id: str = Field(..., description="Template ID to use for scheduled reports")
    name: str = Field(..., description="Schedule name")
    frequency: str = Field(..., description="Schedule frequency (daily, weekly, monthly)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Report parameters")
    recipients: List[str] = Field(..., description="List of recipient email addresses")
    enabled: bool = Field(True, description="Whether the schedule is enabled")
    
    @validator('frequency')
    def validate_frequency(cls, v):
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if v not in valid_frequencies:
            raise ValueError(f'Frequency must be one of: {", ".join(valid_frequencies)}')
        return v
    
    @validator('recipients')
    def validate_recipients(cls, v):
        if not v:
            raise ValueError('At least one recipient is required')
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f'Invalid email address: {email}')
        return v

class ReportScheduleCreate(ReportScheduleBase):
    """Schema for creating report schedules"""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    
    @validator('schedule_id')
    def validate_schedule_id(cls, v):
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Schedule ID must contain only alphanumeric characters, hyphens, and underscores')
        return v

class ReportScheduleUpdate(BaseModel):
    """Schema for updating report schedules"""
    template_id: Optional[str] = Field(None, description="Template ID to use for scheduled reports")
    name: Optional[str] = Field(None, description="Schedule name")
    frequency: Optional[str] = Field(None, description="Schedule frequency")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Report parameters")
    recipients: Optional[List[str]] = Field(None, description="List of recipient email addresses")
    enabled: Optional[bool] = Field(None, description="Whether the schedule is enabled")
    
    @validator('frequency')
    def validate_frequency(cls, v):
        if v is not None:
            valid_frequencies = ['daily', 'weekly', 'monthly']
            if v not in valid_frequencies:
                raise ValueError(f'Frequency must be one of: {", ".join(valid_frequencies)}')
        return v
    
    @validator('recipients')
    def validate_recipients(cls, v):
        if v is not None:
            if not v:
                raise ValueError('At least one recipient is required')
            # Basic email validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            for email in v:
                if not re.match(email_pattern, email):
                    raise ValueError(f'Invalid email address: {email}')
        return v

class ReportSchedule(ReportScheduleBase):
    """Schema for report schedule responses"""
    schedule_id: str
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ReportGenerate(BaseModel):
    """Schema for report generation requests"""
    template_id: str = Field(..., description="Template ID to use for report generation")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Report parameters")
    start_date: Optional[datetime] = Field(None, description="Start date for report data")
    end_date: Optional[datetime] = Field(None, description="End date for report data")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v

class ReportResponse(BaseModel):
    """Schema for report generation responses"""
    report_id: str
    template_id: str
    template_name: str
    generated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    parameters: Dict[str, Any]
    content: str
    data: Dict[str, Any]
    
    class Config:
        from_attributes = True

class ReportExport(BaseModel):
    """Schema for report export requests"""
    template_id: str = Field(..., description="Template ID to use for report generation")
    format: str = Field(..., description="Export format (json, csv, html, pdf, txt)")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Report parameters")
    start_date: Optional[datetime] = Field(None, description="Start date for report data")
    end_date: Optional[datetime] = Field(None, description="End date for report data")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['json', 'csv', 'html', 'pdf', 'txt']
        if v.lower() not in valid_formats:
            raise ValueError(f'Format must be one of: {", ".join(valid_formats)}')
        return v.lower()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v

class AnalyticsQuery(BaseModel):
    """Schema for analytics queries"""
    start_date: datetime = Field(..., description="Start date for analysis")
    end_date: datetime = Field(..., description="End date for analysis")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class TrendAnalytics(BaseModel):
    """Schema for trend analytics responses"""
    interval: str
    start_date: datetime
    end_date: datetime
    data: List[Dict[str, Union[str, int, float]]]
    total_queries: int
    peak_hour: Optional[Dict[str, Union[str, int]]] = None

class DomainAnalytics(BaseModel):
    """Schema for domain analytics responses"""
    domain: str
    query_count: int
    percentage: float

class ClientAnalytics(BaseModel):
    """Schema for client analytics responses"""
    client_ip: str
    query_count: int
    unique_domains: int
    top_query_type: tuple
    success_rate: float

class PerformanceAnalytics(BaseModel):
    """Schema for performance analytics responses"""
    total_queries: int
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    by_query_type: Dict[str, Dict[str, Union[int, float]]]

class ErrorAnalytics(BaseModel):
    """Schema for error analytics responses"""
    total_queries: int
    error_queries: int
    error_rate: float
    response_codes: Dict[str, int]
    top_error_domains: List[Dict[str, Union[str, int]]]
    error_trends: List[Dict[str, Union[str, int]]]

class SecurityAnalytics(BaseModel):
    """Schema for security analytics responses"""
    total_blocked: int
    blocked_by_category: List[Dict[str, Union[str, int]]]
    top_blocked_clients: List[Dict[str, Union[str, int]]]
    blocked_trends: List[Dict[str, Union[str, int]]]
    threat_sources: Dict[str, int]

class ZoneAnalytics(BaseModel):
    """Schema for zone analytics responses"""
    zone_id: int
    zone_name: str
    zone_type: str
    enabled: bool
    total_records: int
    record_types: Dict[str, int]
    query_count_7d: int
    last_modified: Optional[str] = None

class AnalyticsInsight(BaseModel):
    """Schema for analytics insights"""
    type: str = Field(..., description="Insight type (volume, performance, errors, security)")
    severity: str = Field(..., description="Insight severity (info, warning, critical)")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    recommendation: str = Field(..., description="Recommended action")

class ReportHistory(BaseModel):
    """Schema for report history entries"""
    id: str
    template_name: str
    generated_at: datetime
    status: str
    size: str

class ReportingStatistics(BaseModel):
    """Schema for reporting system statistics"""
    total_templates: int
    total_schedules: int
    active_schedules: int
    next_scheduled_run: Optional[datetime] = None