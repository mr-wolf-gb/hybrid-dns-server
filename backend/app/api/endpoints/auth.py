"""
Authentication endpoints
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.config import get_settings
from ...core.database import database
from ...core.logging_config import get_security_logger
from ...core.security import (
    create_access_token, create_refresh_token, generate_session_token,
    generate_totp_qr_code, generate_totp_secret, get_client_ip,
    get_password_hash, is_account_locked, log_security_event,
    verify_password, verify_totp_token, verify_token
)
from ...schemas.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, TokenResponse,
    TwoFactorSetupResponse, TwoFactorVerifyRequest, ChangePasswordRequest,
    UserInfo
)

settings = get_settings()
logger = get_security_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest):
    """User login with optional 2FA"""
    ip_address = get_client_ip(request)
    
    # Get user from database
    user_query = """
    SELECT id, username, email, hashed_password, is_active, two_factor_enabled,
           two_factor_secret, failed_login_attempts, locked_until
    FROM users WHERE username = :username
    """
    user = await database.fetch_one(user_query, {"username": login_data.username})
    
    if not user:
        log_security_event("login_attempt_invalid_user", {
            "username": login_data.username
        }, ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if account is locked
    if is_account_locked(user["failed_login_attempts"], user["locked_until"]):
        log_security_event("login_attempt_locked_account", {
            "user_id": user["id"],
            "username": user["username"]
        }, ip_address)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to multiple failed attempts"
        )
    
    # Verify password
    if not verify_password(login_data.password, user["hashed_password"]):
        # Update failed login attempts
        await database.execute(
            "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = :id",
            {"id": user["id"]}
        )
        
        log_security_event("login_attempt_invalid_password", {
            "user_id": user["id"],
            "username": user["username"]
        }, ip_address)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if account is active
    if not user["is_active"]:
        log_security_event("login_attempt_inactive_account", {
            "user_id": user["id"],
            "username": user["username"]
        }, ip_address)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Check 2FA if enabled
    if user["two_factor_enabled"]:
        if not login_data.totp_code:
            return LoginResponse(
                requires_2fa=True,
                temporary_token=create_access_token(
                    {"sub": user["username"], "temp": True},
                    expires_delta=timedelta(minutes=5)
                )
            )
        
        if not verify_totp_token(user["two_factor_secret"], login_data.totp_code):
            log_security_event("login_attempt_invalid_2fa", {
                "user_id": user["id"],
                "username": user["username"]
            }, ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    
    # Successful login - reset failed attempts and update last login
    session_token = generate_session_token()
    
    await database.execute("""
        UPDATE users 
        SET failed_login_attempts = 0, locked_until = NULL, last_login = :now
        WHERE id = :id
    """, {"id": user["id"], "now": datetime.utcnow()})
    
    # Create session
    await database.execute("""
        INSERT INTO sessions (user_id, session_token, expires_at, ip_address, user_agent)
        VALUES (:user_id, :session_token, :expires_at, :ip_address, :user_agent)
    """, {
        "user_id": user["id"],
        "session_token": session_token,
        "expires_at": datetime.utcnow() + timedelta(seconds=settings.SESSION_TIMEOUT),
        "ip_address": ip_address,
        "user_agent": request.headers.get("User-Agent", "")[:500]
    })
    
    # Create tokens
    access_token = create_access_token({"sub": user["username"], "user_id": user["id"]})
    refresh_token = create_refresh_token({"sub": user["username"], "user_id": user["id"]})
    
    log_security_event("login_success", {
        "user_id": user["id"],
        "username": user["username"]
    }, ip_address)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        session_token=session_token,
        requires_2fa=False
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(request: Request, refresh_data: RefreshTokenRequest):
    """Refresh access token"""
    payload = verify_token(refresh_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    username = payload.get("sub")
    user_id = payload.get("user_id")
    
    # Create new access token
    access_token = create_access_token({"sub": username, "user_id": user_id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user and invalidate session"""
    payload = verify_token(credentials.credentials)
    
    if payload:
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
        # Invalidate all sessions for this user (or specific session if we had session tracking)
        await database.execute(
            "DELETE FROM sessions WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        
        log_security_event("logout", {
            "user_id": user_id,
            "username": username
        }, get_client_ip(request))
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user information"""
    payload = verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    username = payload.get("sub")
    
    user_query = """
    SELECT id, username, email, is_active, is_superuser, two_factor_enabled,
           last_login, created_at
    FROM users WHERE username = :username
    """
    user = await database.fetch_one(user_query, {"username": username})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(**dict(user))


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Set up two-factor authentication"""
    payload = verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("user_id")
    username = payload.get("sub")
    
    # Get user email
    user_query = "SELECT email FROM users WHERE id = :user_id"
    user = await database.fetch_one(user_query, {"user_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate new TOTP secret
    secret = generate_totp_secret()
    qr_code = generate_totp_qr_code(secret, user["email"])
    
    # Store the secret temporarily (not enabled yet)
    await database.execute(
        "UPDATE users SET two_factor_secret = :secret WHERE id = :user_id",
        {"secret": secret, "user_id": user_id}
    )
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=[]  # Generate backup codes after verification
    )


@router.post("/2fa/verify")
async def verify_2fa(
    verify_data: TwoFactorVerifyRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verify and enable two-factor authentication"""
    payload = verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("user_id")
    
    # Get user's TOTP secret
    user_query = "SELECT two_factor_secret FROM users WHERE id = :user_id"
    user = await database.fetch_one(user_query, {"user_id": user_id})
    
    if not user or not user["two_factor_secret"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not set up"
        )
    
    # Verify TOTP code
    if not verify_totp_token(user["two_factor_secret"], verify_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Enable 2FA
    await database.execute(
        "UPDATE users SET two_factor_enabled = true WHERE id = :user_id",
        {"user_id": user_id}
    )
    
    return {"message": "2FA enabled successfully"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Change user password"""
    payload = verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("user_id")
    
    # Get current password hash
    user_query = "SELECT hashed_password FROM users WHERE id = :user_id"
    user = await database.fetch_one(user_query, {"user_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    # Update password
    new_password_hash = get_password_hash(password_data.new_password)
    await database.execute(
        "UPDATE users SET hashed_password = :hash WHERE id = :user_id",
        {"hash": new_password_hash, "user_id": user_id}
    )
    
    log_security_event("password_changed", {"user_id": user_id})
    
    return {"message": "Password changed successfully"}