"""
API endpoints for event broadcasting, filtering, and replay functionality
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_database_session
from ...core.dependencies import get_current_user
from ...services.event_service import get_event_service
from ...models.events import Event, EventSubscription, EventReplay
from ...schemas.auth import User

router = APIRouter(prefix="/events", tags=["events"])


# Pydantic schemas for request/response
class EventCreate(BaseModel):
    event_type: str = Field(..., description="Type of event")
    event_category: str = Field(..., description="Category of event (health, dns, security, system, user)")
    event_source: str = Field(..., description="Source component that generated the event")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    severity: str = Field(default="info", description="Event severity (debug, info, warning, error, critical)")
    tags: Optional[List[str]] = Field(None, description="Event tags for filtering")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    persist: bool = Field(default=True, description="Whether to persist the event")
    broadcast_immediately: bool = Field(default=True, description="Whether to broadcast immediately")


class EventResponse(BaseModel):
    id: int
    event_id: str
    event_type: str
    event_category: str
    event_source: str
    event_data: Dict[str, Any]
    user_id: Optional[str]
    session_id: Optional[str]
    severity: str
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    processed_at: Optional[datetime]
    is_processed: bool
    retry_count: int


class SubscriptionCreate(BaseModel):
    connection_id: Optional[str] = Field(None, description="WebSocket connection ID")
    event_type: Optional[str] = Field(None, description="Specific event type to subscribe to")
    event_category: Optional[str] = Field(None, description="Event category filter")
    event_source: Optional[str] = Field(None, description="Event source filter")
    severity_filter: Optional[List[str]] = Field(None, description="Severity levels to include")
    tag_filters: Optional[List[str]] = Field(None, description="Required tags")
    user_filters: Optional[List[str]] = Field(None, description="User ID filters")
    expires_at: Optional[datetime] = Field(None, description="Subscription expiration time")


class SubscriptionUpdate(BaseModel):
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    event_source: Optional[str] = None
    severity_filter: Optional[List[str]] = None
    tag_filters: Optional[List[str]] = None
    user_filters: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    id: int
    subscription_id: str
    user_id: str
    connection_id: Optional[str]
    event_type: Optional[str]
    event_category: Optional[str]
    event_source: Optional[str]
    severity_filter: Optional[List[str]]
    tag_filters: Optional[List[str]]
    user_filters: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]


class EventFilterCreate(BaseModel):
    name: str = Field(..., description="Filter name")
    description: Optional[str] = Field(None, description="Filter description")
    filter_config: Dict[str, Any] = Field(..., description="Filter configuration")


class EventReplayCreate(BaseModel):
    name: str = Field(..., description="Replay session name")
    description: Optional[str] = Field(None, description="Replay description")
    start_time: datetime = Field(..., description="Start time for event range")
    end_time: datetime = Field(..., description="End time for event range")
    filter_config: Dict[str, Any] = Field(..., description="Filter configuration for events to replay")
    replay_speed: int = Field(default=1, ge=1, le=10, description="Replay speed multiplier")


class EventReplayResponse(BaseModel):
    id: int
    replay_id: str
    name: str
    description: Optional[str]
    user_id: str
    filter_config: Dict[str, Any]
    replay_speed: int
    start_time: datetime
    end_time: datetime
    status: str
    progress: int
    total_events: int
    processed_events: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class EventStatistics(BaseModel):
    event_counts_by_category: Dict[str, int]
    delivery_statistics: Dict[str, int]
    active_subscriptions: int
    active_replays: int
    service_running: bool
    total_events_today: int
    websocket_connections: Dict[str, Any]


@router.post("/emit", response_model=EventResponse)
async def emit_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_user)
):
    """Emit a new event"""
    event_service = get_event_service()
    
    try:
        event = await event_service.emit_event(
            event_type=event_data.event_type,
            event_category=event_data.event_category,
            event_source=event_data.event_source,
            event_data=event_data.event_data,
            user_id=current_user.username,
            severity=event_data.severity,
            tags=event_data.tags,
            metadata=event_data.metadata,
            persist=event_data.persist,
            broadcast_immediately=event_data.broadcast_immediately
        )
        
        return EventResponse(**event.to_dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to emit event: {str(e)}")


@router.get("/", response_model=List[EventResponse])
async def get_events(
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    event_categories: Optional[List[str]] = Query(None, description="Filter by event categories"),
    event_sources: Optional[List[str]] = Query(None, description="Filter by event sources"),
    severity_levels: Optional[List[str]] = Query(None, description="Filter by severity levels"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_user: User = Depends(get_current_user)
):
    """Get events with filtering"""
    event_service = get_event_service()
    
    try:
        events = await event_service.get_events(
            event_types=event_types,
            event_categories=event_categories,
            event_sources=event_sources,
            user_id=current_user.username if not current_user.is_admin else None,
            severity_levels=severity_levels,
            tags=tags,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        return [EventResponse(**event.to_dict()) for event in events]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new event subscription"""
    event_service = get_event_service()
    
    try:
        subscription = await event_service.create_subscription(
            user_id=current_user.username,
            connection_id=subscription_data.connection_id,
            event_type=subscription_data.event_type,
            event_category=subscription_data.event_category,
            event_source=subscription_data.event_source,
            severity_filter=subscription_data.severity_filter,
            tag_filters=subscription_data.tag_filters,
            user_filters=subscription_data.user_filters,
            expires_at=subscription_data.expires_at
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            subscription_id=str(subscription.subscription_id),
            user_id=subscription.user_id,
            connection_id=subscription.connection_id,
            event_type=subscription.event_type,
            event_category=subscription.event_category,
            event_source=subscription.event_source,
            severity_filter=subscription.severity_filter,
            tag_filters=subscription.tag_filters,
            user_filters=subscription.user_filters,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            expires_at=subscription.expires_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    current_user: User = Depends(get_current_user)
):
    """Get all subscriptions for the current user"""
    event_service = get_event_service()
    
    try:
        subscriptions = await event_service.get_user_subscriptions(current_user.username)
        
        return [
            SubscriptionResponse(
                id=sub.id,
                subscription_id=str(sub.subscription_id),
                user_id=sub.user_id,
                connection_id=sub.connection_id,
                event_type=sub.event_type,
                event_category=sub.event_category,
                event_source=sub.event_source,
                severity_filter=sub.severity_filter,
                tag_filters=sub.tag_filters,
                user_filters=sub.user_filters,
                is_active=sub.is_active,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                expires_at=sub.expires_at
            )
            for sub in subscriptions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscriptions: {str(e)}")


@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an event subscription"""
    event_service = get_event_service()
    
    try:
        # Only allow users to update their own subscriptions (unless admin)
        if not current_user.is_admin:
            subscriptions = await event_service.get_user_subscriptions(current_user.username)
            if not any(str(sub.subscription_id) == subscription_id for sub in subscriptions):
                raise HTTPException(status_code=403, detail="Not authorized to update this subscription")
        
        subscription = await event_service.update_subscription(
            subscription_id,
            **subscription_data.dict(exclude_unset=True)
        )
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return SubscriptionResponse(
            id=subscription.id,
            subscription_id=str(subscription.subscription_id),
            user_id=subscription.user_id,
            connection_id=subscription.connection_id,
            event_type=subscription.event_type,
            event_category=subscription.event_category,
            event_source=subscription.event_source,
            severity_filter=subscription.severity_filter,
            tag_filters=subscription.tag_filters,
            user_filters=subscription.user_filters,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            expires_at=subscription.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an event subscription"""
    event_service = get_event_service()
    
    try:
        # Only allow users to delete their own subscriptions (unless admin)
        if not current_user.is_admin:
            subscriptions = await event_service.get_user_subscriptions(current_user.username)
            if not any(str(sub.subscription_id) == subscription_id for sub in subscriptions):
                raise HTTPException(status_code=403, detail="Not authorized to delete this subscription")
        
        success = await event_service.delete_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"message": "Subscription deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete subscription: {str(e)}")


@router.post("/filters")
async def create_event_filter(
    filter_data: EventFilterCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a reusable event filter"""
    event_service = get_event_service()
    
    try:
        event_filter = await event_service.create_event_filter(
            name=filter_data.name,
            filter_config=filter_data.filter_config,
            created_by=current_user.username,
            description=filter_data.description
        )
        
        return {
            "id": event_filter.id,
            "filter_id": str(event_filter.filter_id),
            "name": event_filter.name,
            "description": event_filter.description,
            "filter_config": event_filter.filter_config,
            "is_active": event_filter.is_active,
            "created_by": event_filter.created_by,
            "created_at": event_filter.created_at,
            "updated_at": event_filter.updated_at
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create event filter: {str(e)}")


@router.post("/replay", response_model=EventReplayResponse)
async def start_event_replay(
    replay_data: EventReplayCreate,
    current_user: User = Depends(get_current_user)
):
    """Start an event replay session"""
    event_service = get_event_service()
    
    try:
        # Validate time range
        if replay_data.end_time <= replay_data.start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        # Limit replay duration to prevent abuse
        max_duration = timedelta(days=7)
        if replay_data.end_time - replay_data.start_time > max_duration:
            raise HTTPException(status_code=400, detail="Replay duration cannot exceed 7 days")
        
        replay = await event_service.start_event_replay(
            name=replay_data.name,
            user_id=current_user.username,
            start_time=replay_data.start_time,
            end_time=replay_data.end_time,
            filter_config=replay_data.filter_config,
            replay_speed=replay_data.replay_speed,
            description=replay_data.description
        )
        
        return EventReplayResponse(
            id=replay.id,
            replay_id=str(replay.replay_id),
            name=replay.name,
            description=replay.description,
            user_id=replay.user_id,
            filter_config=replay.filter_config,
            replay_speed=replay.replay_speed,
            start_time=replay.start_time,
            end_time=replay.end_time,
            status=replay.status,
            progress=replay.progress,
            total_events=replay.total_events,
            processed_events=replay.processed_events,
            created_at=replay.created_at,
            started_at=replay.started_at,
            completed_at=replay.completed_at,
            error_message=replay.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start event replay: {str(e)}")


@router.get("/replay/{replay_id}", response_model=EventReplayResponse)
async def get_replay_status(
    replay_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an event replay"""
    event_service = get_event_service()
    
    try:
        replay = await event_service.get_replay_status(replay_id)
        
        if not replay:
            raise HTTPException(status_code=404, detail="Replay not found")
        
        # Only allow users to view their own replays (unless admin)
        if not current_user.is_admin and replay.user_id != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to view this replay")
        
        return EventReplayResponse(
            id=replay.id,
            replay_id=str(replay.replay_id),
            name=replay.name,
            description=replay.description,
            user_id=replay.user_id,
            filter_config=replay.filter_config,
            replay_speed=replay.replay_speed,
            start_time=replay.start_time,
            end_time=replay.end_time,
            status=replay.status,
            progress=replay.progress,
            total_events=replay.total_events,
            processed_events=replay.processed_events,
            created_at=replay.created_at,
            started_at=replay.started_at,
            completed_at=replay.completed_at,
            error_message=replay.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get replay status: {str(e)}")


@router.post("/replay/{replay_id}/stop")
async def stop_event_replay(
    replay_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop an active event replay"""
    event_service = get_event_service()
    
    try:
        # Check if user owns the replay (unless admin)
        if not current_user.is_admin:
            replay = await event_service.get_replay_status(replay_id)
            if not replay or replay.user_id != current_user.username:
                raise HTTPException(status_code=403, detail="Not authorized to stop this replay")
        
        success = await event_service.stop_event_replay(replay_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Replay not found or not active")
        
        return {"message": "Replay stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop replay: {str(e)}")


@router.get("/statistics", response_model=EventStatistics)
async def get_event_statistics(
    current_user: User = Depends(get_current_user)
):
    """Get event broadcasting statistics"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    event_service = get_event_service()
    
    try:
        stats = await event_service.get_event_statistics()
        return EventStatistics(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/service/start")
async def start_event_service(
    current_user: User = Depends(get_current_user)
):
    """Start the event broadcasting service"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    event_service = get_event_service()
    
    try:
        await event_service.start()
        return {"message": "Event broadcasting service started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start service: {str(e)}")


@router.post("/service/stop")
async def stop_event_service(
    current_user: User = Depends(get_current_user)
):
    """Stop the event broadcasting service"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    event_service = get_event_service()
    
    try:
        await event_service.stop()
        return {"message": "Event broadcasting service stopped"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop service: {str(e)}")