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

settings = get_settings()
logger = get_security_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.info(f"Created access token for user: {data.get('sub', 'unknown')}")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.info(f"Created refresh token for user: {data.get('sub', 'unknown')}")
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


# Two-Factor Authentication
def generate_totp_secret() -> str:
    """Generate a new TOTP secret for 2FA"""
    return pyotp.random_base32()


def generate_totp_qr_code(secret: str, email: str, issuer_name: str = "Hybrid DNS Server") -> str:
    """Generate QR code for TOTP setup"""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer_name
    )
    
    # Generate QR code as SVG
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    # Create SVG image
    factory = qrcode.image.svg.SvgPathImage
    img = qr.make_image(image_factory=factory)
    
    # Convert to string
    buffer = BytesIO()
    img.save(buffer)
    return buffer.getvalue().decode()


def verify_totp_token(secret: str, token: str) -> bool:
    """Verify TOTP token"""
    totp = pyotp.TOTP(secret)
    # Allow for clock drift
    return totp.verify(token, valid_window=1)


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
    
    return failed_attempts >= settings.MAX_LOGIN_ATTEMPTS


def calculate_lockout_time(failed_attempts: int) -> datetime:
    """Calculate account lockout time based on failed attempts"""
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


def log_security_event(event_type: str, details: Dict[str, Any], ip_address: str = None):
    """Log security-related events"""
    logger.warning(f"Security Event: {event_type}", extra={
        "event_type": event_type,
        "details": details,
        "ip_address": ip_address,
        "timestamp": datetime.utcnow().isoformat()
    })


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