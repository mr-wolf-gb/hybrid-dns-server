"""
Security utilities for authentication and authorization
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings
from .logging_config import get_security_logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def get_current_user_websocket(token: str) -> Optional[Dict[str, Any]]:
    """
    Get current user from WebSocket token
    For now, this is a simplified version - in production you'd validate the JWT token
    """
    try:
        # For development, we'll accept any non-empty token
        # In production, you'd decode and validate the JWT token here
        if token and len(token) > 0:
            return {"id": token, "username": token}
        return None
    except Exception:
        return None


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    settings = get_settings()
    logger = get_security_logger()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        logger.debug(f"Created access token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    settings = get_settings()
    logger = get_security_logger()
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        logger.debug(f"Created refresh token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    settings = get_settings()
    logger = get_security_logger()
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA"""
    return pyotp.random_base32()


def generate_totp_qr_code(secret: str, user_email: str) -> str:
    """Generate QR code for TOTP setup"""
    settings = get_settings()
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name=settings.TOTP_ISSUER_NAME
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    import base64
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp_token(secret: str, token: str) -> bool:
    """Verify TOTP token"""
    settings = get_settings()
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=settings.TOTP_VALID_WINDOW)


def get_client_ip(request) -> str:
    """Get client IP address from request"""
    # Check for forwarded IP first (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to client host
    return request.client.host if request.client else "unknown"


def is_account_locked(user: Dict[str, Any]) -> bool:
    """Check if user account is locked"""
    if not user.get("locked_until"):
        return False
    
    locked_until = user["locked_until"]
    if isinstance(locked_until, str):
        from datetime import datetime
        locked_until = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
    
    return datetime.utcnow() < locked_until


def log_security_event(event_type: str, details: Dict[str, Any], ip_address: str = None):
    """Log security events"""
    logger = get_security_logger()
    logger.info(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    settings = get_settings()
    logger = get_security_logger()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        logger.debug(f"Created refresh token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    settings = get_settings()
    logger = get_security_logger()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


# Two-Factor Authentication (PNG base64 QR for broad compatibility)
def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA"""
    return pyotp.random_base32()


def generate_totp_qr_code(secret: str, user_email: str) -> str:
    """Generate QR code (PNG base64) for TOTP setup"""
    settings = get_settings()
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name=settings.TOTP_ISSUER_NAME
    )
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    import base64
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp_token(secret: str, token: str) -> bool:
    """Verify TOTP token with configured time window"""
    settings = get_settings()
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=settings.TOTP_VALID_WINDOW)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for 2FA recovery"""
    return [secrets.token_hex(4).upper() for _ in range(count)]


# Password validation
def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and return requirements"""
    requirements = {
        "min_length": len(password) >= 8,
        "has_upper": any(c.isupper() for c in password),
        "has_lower": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
    }
    
    is_valid = all(requirements.values())
    
    return {
        "is_valid": is_valid,
        "requirements": requirements,
        "score": sum(requirements.values()),
        "feedback": generate_password_feedback(requirements)
    }


def generate_password_feedback(requirements: Dict[str, bool]) -> list[str]:
    """Generate feedback for password requirements"""
    feedback = []
    
    if not requirements["min_length"]:
        feedback.append("Password must be at least 8 characters long")
    if not requirements["has_upper"]:
        feedback.append("Password must contain at least one uppercase letter")
    if not requirements["has_lower"]:
        feedback.append("Password must contain at least one lowercase letter")
    if not requirements["has_digit"]:
        feedback.append("Password must contain at least one number")
    if not requirements["has_special"]:
        feedback.append("Password must contain at least one special character")
    
    return feedback


# Rate limiting and security
def is_account_locked(failed_attempts: int, locked_until: Optional[datetime]) -> bool:
    """Check if account is locked due to failed login attempts"""
    if locked_until and datetime.utcnow() < locked_until:
        return True
    
    settings = get_settings()
    return failed_attempts >= settings.MAX_LOGIN_ATTEMPTS


def calculate_lockout_time(failed_attempts: int) -> datetime:
    """Calculate account lockout time based on failed attempts"""
    settings = get_settings()
    if failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        return datetime.utcnow() + timedelta(seconds=settings.LOCKOUT_DURATION)
    return None


def get_client_ip(request) -> str:
    """Extract client IP from request, considering proxies"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


# (Consolidated above) log_security_event defined once


# API Key management (for service-to-service communication)
def generate_api_key() -> str:
    """Generate a new API key"""
    return f"dns_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return get_password_hash(api_key)


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash"""
    return verify_password(api_key, hashed_key)


# CSRF protection
def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """Verify CSRF token (simple implementation)"""
    # In production, this should be more sophisticated
    return len(token) == 43 and token.replace("_", "").replace("-", "").isalnum()


# Encryption utilities for sensitive data
def encrypt_sensitive_data(data: str, key: Optional[str] = None) -> str:
    """Encrypt sensitive data (simple implementation)"""
    # This is a placeholder - implement proper encryption in production
    # Consider using cryptography.fernet for real encryption
    return f"encrypted_{secrets.token_urlsafe(16)}_{len(data)}"


def decrypt_sensitive_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """Decrypt sensitive data (simple implementation)"""
    # This is a placeholder - implement proper decryption in production
    return "decrypted_data"


# FastAPI dependency for authentication
async def get_current_user() -> Dict[str, Any]:
    """Get current authenticated user (placeholder for testing)"""
    # This is a placeholder implementation for testing
    # In production, this would validate JWT tokens and return user info
    return {
        "id": 1,
        "username": "admin",
        "email": "admin@localhost",
        "is_active": True,
        "is_superuser": True
    }