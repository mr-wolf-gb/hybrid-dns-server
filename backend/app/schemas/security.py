"""
Security-related Pydantic schemas for the Hybrid DNS Server
"""

from pydantic import BaseModel, Field, validator, model_validator, HttpUrl
from typing import Optional
from datetime import datetime
from enum import Enum


class FeedType(str, Enum):
    """Threat feed types"""
    MALWARE = "malware"
    PHISHING = "phishing"
    ADULT = "adult"
    SOCIAL_MEDIA = "social_media"
    GAMBLING = "gambling"
    CUSTOM = "custom"


class FormatType(str, Enum):
    """Feed format types"""
    HOSTS = "hosts"
    DOMAINS = "domains"
    RPZ = "rpz"
    JSON = "json"


class UpdateStatus(str, Enum):
    """Update status types"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    NEVER = "never"


class RPZAction(str, Enum):
    """RPZ rule actions"""
    BLOCK = "block"
    REDIRECT = "redirect"
    PASSTHRU = "passthru"


# ThreatFeed Schemas
class ThreatFeedBase(BaseModel):
    """Base schema for ThreatFeed"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the threat feed")
    url: HttpUrl = Field(..., description="URL of the threat feed")
    feed_type: FeedType = Field(..., description="Type of threats in this feed")
    format_type: FormatType = Field(..., description="Format of the feed data")
    update_frequency: int = Field(default=3600, ge=300, le=86400, description="Update frequency in seconds")
    description: Optional[str] = Field(None, max_length=500, description="Description of the threat feed")

    @validator('update_frequency')
    def validate_update_frequency(cls, v):
        """Validate update frequency is reasonable"""
        if v < 300:  # 5 minutes minimum
            raise ValueError('Update frequency must be at least 300 seconds (5 minutes)')
        if v > 86400:  # 24 hours maximum
            raise ValueError('Update frequency must be at most 86400 seconds (24 hours)')
        return v


class ThreatFeedCreate(ThreatFeedBase):
    """Schema for creating a new threat feed"""
    pass


class ThreatFeedUpdate(BaseModel):
    """Schema for updating an existing threat feed"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    feed_type: Optional[FeedType] = None
    format_type: Optional[FormatType] = None
    update_frequency: Optional[int] = Field(None, ge=300, le=86400)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @validator('update_frequency')
    def validate_update_frequency(cls, v):
        """Validate update frequency is reasonable"""
        if v is not None:
            if v < 300:  # 5 minutes minimum
                raise ValueError('Update frequency must be at least 300 seconds (5 minutes)')
            if v > 86400:  # 24 hours maximum
                raise ValueError('Update frequency must be at most 86400 seconds (24 hours)')
        return v


class ThreatFeed(ThreatFeedBase):
    """Schema for ThreatFeed response"""
    id: int
    is_active: bool
    last_updated: Optional[datetime] = None
    last_update_status: Optional[UpdateStatus] = None
    last_update_error: Optional[str] = None
    rules_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThreatFeedStatus(BaseModel):
    """Schema for threat feed status information"""
    id: int
    name: str
    is_active: bool
    last_updated: Optional[datetime] = None
    last_update_status: Optional[UpdateStatus] = None
    last_update_error: Optional[str] = None
    rules_count: int = 0
    next_update: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ThreatFeedUpdateResult(BaseModel):
    """Schema for threat feed update results"""
    feed_id: int
    feed_name: str
    status: UpdateStatus
    rules_added: int = 0
    rules_updated: int = 0
    rules_removed: int = 0
    error_message: Optional[str] = None
    update_duration: Optional[float] = None  # seconds
    
    class Config:
        from_attributes = True


class BulkThreatFeedUpdateResult(BaseModel):
    """Schema for bulk threat feed update results"""
    total_feeds: int
    successful_updates: int
    failed_updates: int
    total_rules_added: int = 0
    total_rules_updated: int = 0
    total_rules_removed: int = 0
    feed_results: list[ThreatFeedUpdateResult] = []
    update_duration: Optional[float] = None  # seconds
    
    class Config:
        from_attributes = True


# RPZ Rule Schemas (related to threat feeds)
class RPZRuleBase(BaseModel):
    """Base schema for RPZ rules"""
    domain: str = Field(..., min_length=1, max_length=255, description="Domain to apply rule to")
    rpz_zone: str = Field(..., min_length=1, max_length=50, description="RPZ zone category")
    action: RPZAction = Field(..., description="Action to take for this domain")
    redirect_target: Optional[str] = Field(None, max_length=255, description="Target for redirect action")
    description: Optional[str] = Field(None, max_length=500, description="Description of the rule")

    @model_validator(mode='after')
    def validate_redirect_target(self):
        """Validate redirect target is provided when action is redirect"""
        if self.action == RPZAction.REDIRECT and not self.redirect_target:
            raise ValueError('Redirect target is required for redirect action')
        return self

    @validator('domain')
    def validate_domain(cls, v):
        """Basic domain validation"""
        if not v:
            raise ValueError('Domain cannot be empty')
        
        # Trim and normalize
        domain = v.strip().lower()
        
        if not domain:
            raise ValueError('Domain cannot be empty')
        
        # Basic domain format check (after trimming)
        if not all(c.isalnum() or c in '.-_' for c in domain):
            raise ValueError('Domain contains invalid characters')
        
        return domain


class RPZRuleCreate(RPZRuleBase):
    """Schema for creating RPZ rules"""
    source: Optional[str] = Field(None, max_length=50, description="Source of the rule (manual, threat_feed, etc.)")


class RPZRuleUpdate(BaseModel):
    """Schema for updating RPZ rules"""
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    rpz_zone: Optional[str] = Field(None, min_length=1, max_length=50)
    action: Optional[RPZAction] = None
    redirect_target: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_redirect_target(self):
        """Validate redirect target is provided when action is redirect"""
        if self.action == RPZAction.REDIRECT and not self.redirect_target:
            raise ValueError('Redirect target is required for redirect action')
        return self


class RPZRule(RPZRuleBase):
    """Schema for RPZ rule response"""
    id: int
    is_active: bool
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RPZRuleImportResult(BaseModel):
    """Schema for RPZ rule import results"""
    total_processed: int = 0
    rules_added: int = 0
    rules_updated: int = 0
    rules_skipped: int = 0
    errors: list[str] = []
    
    class Config:
        from_attributes = True