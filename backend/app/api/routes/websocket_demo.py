"""
Demo API endpoints showing WebSocket event integration
These endpoints demonstrate how to emit real-time events from API operations
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from ...services.websocket_events import get_websocket_event_service, WebSocketEventBatch, emit_websocket_event
from ...websocket.manager import get_websocket_manager, EventType
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/websocket-demo", tags=["WebSocket Demo"])


@router.post("/emit-dns-event")
async def emit_dns_event(
    event_type: str,
    zone_name: str,
    record_name: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Demo endpoint to emit DNS events"""
    event_service = get_websocket_event_service()
    
    # Prepare event data
    event_data = {
        "name": zone_name,
        "type": "A" if record_name else "zone",
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_id or "system"
    }
    
    if record_name:
        event_data["record_name"] = record_name
    
    # Emit appropriate event
    try:
        if event_type == "zone_created":
            await event_service.emit_zone_created(event_data, user_id)
        elif event_type == "zone_updated":
            await event_service.emit_zone_updated(event_data, user_id)
        elif event_type == "zone_deleted":
            await event_service.emit_zone_deleted(event_data, user_id)
        elif event_type == "record_created":
            await event_service.emit_record_created(event_data, user_id)
        elif event_type == "record_updated":
            await event_service.emit_record_updated(event_data, user_id)
        elif event_type == "record_deleted":
            await event_service.emit_record_deleted(event_data, user_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid event type")
        
        return {"message": f"Emitted {event_type} event", "data": event_data}
        
    except Exception as e:
        logger.error(f"Error emitting DNS event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emit-security-event")
async def emit_security_event(
    event_type: str,
    message: str,
    severity: str = "warning",
    details: Optional[Dict[str, Any]] = None
):
    """Demo endpoint to emit security events"""
    event_service = get_websocket_event_service()
    
    # Prepare event data
    event_data = {
        "message": message,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details or {}
    }
    
    try:
        if event_type == "security_alert":
            await event_service.emit_security_alert(event_data)
        elif event_type == "threat_detected":
            event_data["threat_type"] = details.get("threat_type", "unknown") if details else "unknown"
            await event_service.emit_threat_detected(event_data)
        elif event_type == "rpz_update":
            event_data["zone"] = details.get("zone", "unknown") if details else "unknown"
            await event_service.emit_rpz_update(event_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid security event type")
        
        return {"message": f"Emitted {event_type} event", "data": event_data}
        
    except Exception as e:
        logger.error(f"Error emitting security event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emit-system-event")
async def emit_system_event(
    event_type: str,
    component: str,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None
):
    """Demo endpoint to emit system events"""
    event_service = get_websocket_event_service()
    
    # Prepare event data
    event_data = {
        "component": component,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details or {}
    }
    
    try:
        if event_type == "bind_reload":
            await event_service.emit_bind_reload(event_data)
        elif event_type == "config_change":
            await event_service.emit_config_change(event_data)
        else:
            # Emit custom system event
            await event_service.emit_custom_event(event_type, event_data)
        
        return {"message": f"Emitted {event_type} event", "data": event_data}
        
    except Exception as e:
        logger.error(f"Error emitting system event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-events")
async def emit_batch_events(
    events: list[Dict[str, Any]]
):
    """Demo endpoint to emit multiple events in a batch"""
    try:
        async with WebSocketEventBatch() as batch:
            for event in events:
                batch.add_event(
                    event.get("type", "custom_event"),
                    event.get("data", {}),
                    event.get("user_id")
                )
        
        return {"message": f"Emitted {len(events)} events in batch"}
        
    except Exception as e:
        logger.error(f"Error emitting batch events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-dns-workflow")
async def simulate_dns_workflow(
    zone_name: str,
    user_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """Simulate a complete DNS workflow with multiple events"""
    
    async def workflow():
        event_service = get_websocket_event_service()
        
        try:
            # Step 1: Create zone
            await event_service.emit_zone_created({
                "name": zone_name,
                "type": "master",
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
            
            await asyncio.sleep(1)  # Simulate processing time
            
            # Step 2: Add some records
            for record_type, record_name in [("A", "www"), ("A", "mail"), ("CNAME", "ftp")]:
                await event_service.emit_record_created({
                    "zone": zone_name,
                    "name": f"{record_name}.{zone_name}",
                    "type": record_type,
                    "value": "192.168.1.100" if record_type == "A" else f"www.{zone_name}",
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)
                
                await asyncio.sleep(0.5)
            
            # Step 3: Reload BIND
            await event_service.emit_bind_reload({
                "zones_reloaded": [zone_name],
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Step 4: Configuration change notification
            await event_service.emit_config_change({
                "component": "dns_zones",
                "action": "zone_added",
                "zone": zone_name,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in DNS workflow simulation: {e}")
    
    # Run workflow in background
    if background_tasks:
        background_tasks.add_task(workflow)
    else:
        asyncio.create_task(workflow())
    
    return {"message": f"Started DNS workflow simulation for zone: {zone_name}"}


@router.get("/connection-stats")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    websocket_manager = get_websocket_manager()
    stats = websocket_manager.get_connection_stats()
    
    return {
        "connection_stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/broadcast-message")
async def broadcast_message(
    message: str,
    connection_type: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Broadcast a custom message to WebSocket clients"""
    websocket_manager = get_websocket_manager()
    
    message_data = {
        "type": "custom_message",
        "data": {
            "message": message,
            "sender": "api",
            "timestamp": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        if user_id:
            await websocket_manager.send_to_user(message_data, user_id, connection_type)
        else:
            await websocket_manager.broadcast(message_data, connection_type)
        
        return {"message": "Message broadcasted successfully"}
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example of using the decorator
@router.post("/decorated-operation")
@emit_websocket_event("custom_operation", lambda result, operation_type, **kwargs: {
    "operation": operation_type,
    "result": result,
    "timestamp": datetime.utcnow().isoformat()
})
async def decorated_operation(operation_type: str, data: Dict[str, Any]):
    """Demo endpoint showing decorator usage for automatic event emission"""
    
    # Simulate some operation
    await asyncio.sleep(0.1)
    
    result = {
        "operation": operation_type,
        "data": data,
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return result


@router.post("/test-all-events")
async def test_all_events(user_id: Optional[str] = None):
    """Test endpoint to emit all types of events for testing"""
    event_service = get_websocket_event_service()
    
    events_emitted = []
    
    try:
        # DNS Events
        await event_service.emit_zone_created({"name": "test.local", "type": "master"}, user_id)
        events_emitted.append("zone_created")
        
        await event_service.emit_record_created({"zone": "test.local", "name": "www.test.local", "type": "A"}, user_id)
        events_emitted.append("record_created")
        
        # Security Events
        await event_service.emit_security_alert({"message": "Test security alert", "severity": "warning"})
        events_emitted.append("security_alert")
        
        await event_service.emit_threat_detected({"threat_type": "malware", "details": "Test threat detection"})
        events_emitted.append("threat_detected")
        
        # System Events
        await event_service.emit_bind_reload({"status": "success", "zones_reloaded": ["test.local"]})
        events_emitted.append("bind_reload")
        
        await event_service.emit_config_change({"component": "test", "action": "update"})
        events_emitted.append("config_change")
        
        # User Events (if user_id provided)
        if user_id:
            await event_service.emit_user_login({"username": f"user_{user_id}", "timestamp": datetime.utcnow().isoformat()})
            events_emitted.append("user_login")
        
        return {
            "message": "All test events emitted successfully",
            "events_emitted": events_emitted,
            "total_events": len(events_emitted)
        }
        
    except Exception as e:
        logger.error(f"Error emitting test events: {e}")
        raise HTTPException(status_code=500, detail=str(e))