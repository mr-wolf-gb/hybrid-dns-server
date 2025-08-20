"""
Event integration service for automatically emitting events from existing services
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.logging_config import get_logger
from .event_service import get_event_service

logger = get_logger(__name__)


class EventIntegration:
    """
    Service for integrating event broadcasting with existing services
    """
    
    def __init__(self):
        self.event_service = get_event_service()
    
    async def emit_zone_event(
        self,
        event_type: str,
        zone_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Emit DNS zone-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="dns",
            event_source="zone_service",
            event_data=zone_data,
            user_id=user_id,
            session_id=session_id,
            severity="info",
            tags=["dns", "zone"],
            metadata={"zone_id": zone_data.get("id"), "zone_name": zone_data.get("name")}
        )
    
    async def emit_record_event(
        self,
        event_type: str,
        record_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Emit DNS record-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="dns",
            event_source="record_service",
            event_data=record_data,
            user_id=user_id,
            session_id=session_id,
            severity="info",
            tags=["dns", "record"],
            metadata={
                "record_id": record_data.get("id"),
                "record_name": record_data.get("name"),
                "record_type": record_data.get("type"),
                "zone_id": record_data.get("zone_id")
            }
        )
    
    async def emit_forwarder_event(
        self,
        event_type: str,
        forwarder_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info"
    ):
        """Emit forwarder-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="health",
            event_source="forwarder_service",
            event_data=forwarder_data,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            tags=["forwarder", "health"],
            metadata={
                "forwarder_id": forwarder_data.get("id"),
                "forwarder_name": forwarder_data.get("name")
            }
        )
    
    async def emit_health_event(
        self,
        event_type: str,
        health_data: Dict[str, Any],
        severity: str = "info"
    ):
        """Emit health monitoring events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="health",
            event_source="health_service",
            event_data=health_data,
            severity=severity,
            tags=["health", "monitoring"],
            metadata=health_data.get("metadata", {})
        )
    
    async def emit_security_event(
        self,
        event_type: str,
        security_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "warning"
    ):
        """Emit security-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="security",
            event_source="rpz_service",
            event_data=security_data,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            tags=["security", "rpz"],
            metadata=security_data.get("metadata", {})
        )
    
    async def emit_system_event(
        self,
        event_type: str,
        system_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info"
    ):
        """Emit system-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="system",
            event_source="system_service",
            event_data=system_data,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            tags=["system"],
            metadata=system_data.get("metadata", {})
        )
    
    async def emit_user_event(
        self,
        event_type: str,
        user_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Emit user-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="user",
            event_source="auth_service",
            event_data=user_data,
            user_id=user_id,
            session_id=session_id,
            severity="info",
            tags=["user", "auth"],
            metadata={"target_user": user_data.get("username")}
        )
    
    async def emit_bind_event(
        self,
        event_type: str,
        bind_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info"
    ):
        """Emit BIND9-related events"""
        await self.event_service.emit_event(
            event_type=event_type,
            event_category="system",
            event_source="bind_service",
            event_data=bind_data,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            tags=["bind9", "dns"],
            metadata=bind_data.get("metadata", {})
        )
    
    # Convenience methods for common events
    async def zone_created(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit zone created event"""
        await self.emit_zone_event("zone_created", zone_data, user_id)
    
    async def zone_updated(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit zone updated event"""
        await self.emit_zone_event("zone_updated", zone_data, user_id)
    
    async def zone_deleted(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit zone deleted event"""
        await self.emit_zone_event("zone_deleted", zone_data, user_id)
    
    async def record_created(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit record created event"""
        await self.emit_record_event("record_created", record_data, user_id)
    
    async def record_updated(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit record updated event"""
        await self.emit_record_event("record_updated", record_data, user_id)
    
    async def record_deleted(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit record deleted event"""
        await self.emit_record_event("record_deleted", record_data, user_id)
    
    async def forwarder_status_changed(
        self,
        forwarder_data: Dict[str, Any],
        old_status: str,
        new_status: str
    ):
        """Emit forwarder status change event"""
        event_data = {
            **forwarder_data,
            "old_status": old_status,
            "new_status": new_status,
            "status_changed_at": datetime.utcnow().isoformat()
        }
        
        severity = "error" if new_status == "unhealthy" else "info"
        await self.emit_forwarder_event("forwarder_status_changed", event_data, severity=severity)
    
    async def health_alert(self, alert_data: Dict[str, Any], severity: str = "warning"):
        """Emit health alert event"""
        await self.emit_health_event("health_alert", alert_data, severity)
    
    async def security_threat_detected(
        self,
        threat_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Emit security threat detected event"""
        await self.emit_security_event("threat_detected", threat_data, user_id, severity="error")
    
    async def rpz_rule_updated(
        self,
        rule_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Emit RPZ rule updated event"""
        await self.emit_security_event("rpz_update", rule_data, user_id)
    
    async def bind_reload(
        self,
        reload_data: Dict[str, Any],
        user_id: Optional[str] = None,
        success: bool = True
    ):
        """Emit BIND9 reload event"""
        event_data = {
            **reload_data,
            "success": success,
            "reloaded_at": datetime.utcnow().isoformat()
        }
        
        severity = "info" if success else "error"
        await self.emit_bind_event("bind_reload", event_data, user_id, severity=severity)
    
    async def config_backup_created(
        self,
        backup_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Emit configuration backup created event"""
        await self.emit_system_event("config_backup_created", backup_data, user_id)
    
    async def config_restored(
        self,
        restore_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Emit configuration restored event"""
        await self.emit_system_event("config_restored", restore_data, user_id, severity="warning")
    
    async def user_login(self, user_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit user login event"""
        await self.emit_user_event("user_login", user_data, user_id)
    
    async def user_logout(self, user_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit user logout event"""
        await self.emit_user_event("user_logout", user_data, user_id)
    
    async def user_session_expired(self, user_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit user session expired event"""
        await self.emit_user_event("session_expired", user_data, user_id, severity="warning")


# Global event integration instance
_event_integration = None

def get_event_integration() -> EventIntegration:
    """Get the global event integration instance"""
    global _event_integration
    if _event_integration is None:
        _event_integration = EventIntegration()
    return _event_integration