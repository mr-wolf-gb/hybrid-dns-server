"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import json

from ...core.database import get_database_session
from ...core.dependencies import get_current_user
from ...models.auth import User
from ...schemas.auth import UserInfo
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Default notification preferences
DEFAULT_NOTIFICATION_PREFERENCES = {
    "enabled_severities": ["warning", "error", "critical"],
    "enabled_categories": ["dns", "security", "system"],
    "show_health_updates": False,
    "show_system_events": True,
    "show_dns_events": True,
    "show_security_events": True,
    "throttle_duration": 5000,
    "max_notifications_per_minute": 10
}

@router.get("/")
async def list_users():
    return {"message": "User management endpoints - TODO"}

@router.get("/notification-preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """Get user's notification preferences"""
    try:
        # For now, we'll store preferences in user metadata
        # In a production system, you might want a separate table
        preferences = current_user.user_metadata.get("notification_preferences") if current_user.user_metadata else None
        
        if not preferences:
            preferences = DEFAULT_NOTIFICATION_PREFERENCES
        
        return {
            "success": True,
            "data": preferences
        }
    except Exception as e:
        logger.error(f"Error getting notification preferences for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification preferences")

@router.put("/notification-preferences")
async def update_notification_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """Update user's notification preferences"""
    try:
        # Validate preferences structure
        required_fields = [
            "enabled_severities", "enabled_categories", "show_health_updates",
            "show_system_events", "show_dns_events", "show_security_events",
            "throttle_duration", "max_notifications_per_minute"
        ]
        
        for field in required_fields:
            if field not in preferences:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Validate severity levels
        valid_severities = ["debug", "info", "warning", "error", "critical"]
        for severity in preferences["enabled_severities"]:
            if severity not in valid_severities:
                raise HTTPException(status_code=400, detail=f"Invalid severity level: {severity}")
        
        # Validate categories
        valid_categories = ["health", "dns", "security", "system"]
        for category in preferences["enabled_categories"]:
            if category not in valid_categories:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        # Validate numeric values
        if not isinstance(preferences["throttle_duration"], int) or preferences["throttle_duration"] < 1000:
            raise HTTPException(status_code=400, detail="Throttle duration must be at least 1000ms")
        
        if not isinstance(preferences["max_notifications_per_minute"], int) or preferences["max_notifications_per_minute"] < 1:
            raise HTTPException(status_code=400, detail="Max notifications per minute must be at least 1")
        
        # Update user metadata
        if not current_user.user_metadata:
            current_user.user_metadata = {}
        
        current_user.user_metadata["notification_preferences"] = preferences
        
        # Mark the metadata as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(current_user, "metadata")
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"Updated notification preferences for user {current_user.id}")
        
        return {
            "success": True,
            "data": preferences,
            "message": "Notification preferences updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating notification preferences for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")