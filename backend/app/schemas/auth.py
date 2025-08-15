"""
Authentication-related Pydantic schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)
    totp_code: Optional[str] = Field(None, pattern=r'^\d{6}$', description="6-digit TOTP code")


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    session_token: Optional[str] = None
    requires_2fa: bool = False
    temporary_token: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class TwoFactorSetupResponse(BaseModel):
    """2FA setup response schema"""
    secret: str
    qr_code: str
    backup_codes: List[str]


class TwoFactorVerifyRequest(BaseModel):
    """2FA verification request schema"""
    totp_code: str = Field(..., pattern=r'^\d{6}$', description="6-digit TOTP code")


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class UserInfo(BaseModel):
    """User information schema"""
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    two_factor_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime


class UserCreate(BaseModel):
    """User creation schema"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_superuser: bool = False
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        return v


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class SessionInfo(BaseModel):
    """Session information schema"""
    id: int
    user_id: int
    session_token: str
    expires_at: datetime
    created_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool = False


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        return v


class ApiKeyCreate(BaseModel):
    """API key creation schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class ApiKeyInfo(BaseModel):
    """API key information schema"""
    id: int
    name: str
    description: Optional[str]
    key_preview: str  # Only show first/last few characters
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    is_active: bool