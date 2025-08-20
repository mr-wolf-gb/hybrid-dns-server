# WebSocket Integration Example

This example shows how to integrate WebSocket events into existing API endpoints.

## Before: Standard API Endpoint

```python
# backend/app/api/endpoints/zones.py (before)
@router.post("/", response_model=DNSZoneResponse)
async def create_zone(
    zone_data: DNSZoneCreate,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new DNS zone"""
    try:
        # Create zone in database
        zone = await zone_service.create_zone(db, zone_data, current_user.id)
        
        # Generate BIND configuration
        await bind_service.reload_configuration()
        
        return zone
        
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## After: WebSocket-Enabled API Endpoint

```python
# backend/app/api/endpoints/zones.py (after)
from ...services.websocket_events import get_websocket_event_service

@router.post("/", response_model=DNSZoneResponse)
async def create_zone(
    zone_data: DNSZoneCreate,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new DNS zone with real-time notifications"""
    try:
        # Create zone in database
        zone = await zone_service.create_zone(db, zone_data, current_user.id)
        
        # Emit WebSocket event for zone creation
        event_service = get_websocket_event_service()
        await event_service.emit_zone_created({
            "id": zone.id,
            "name": zone.name,
            "type": zone.zone_type,
            "created_by": current_user.username,
            "created_at": zone.created_at.isoformat()
        }, user_id=str(current_user.id))
        
        # Generate BIND configuration
        await bind_service.reload_configuration()
        
        # Emit BIND reload event
        await event_service.emit_bind_reload({
            "zones_reloaded": [zone.name],
            "status": "success",
            "reloaded_by": current_user.username
        })
        
        return zone
        
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        
        # Emit error event
        event_service = get_websocket_event_service()
        await event_service.emit_custom_event("zone_creation_failed", {
            "zone_name": zone_data.name,
            "error": str(e),
            "user": current_user.username
        }, user_id=str(current_user.id))
        
        raise HTTPException(status_code=500, detail=str(e))
```

## Frontend Integration

### Before: Standard Component

```typescript
// frontend/src/components/zones/ZoneList.tsx (before)
const ZoneList = () => {
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(false)

  const createZone = async (zoneData) => {
    setLoading(true)
    try {
      const response = await api.post('/zones', zoneData)
      setZones([...zones, response.data])
      toast.success('Zone created successfully')
    } catch (error) {
      toast.error('Failed to create zone')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Zone list UI */}
    </div>
  )
}
```

### After: Real-Time Component

```typescript
// frontend/src/components/zones/ZoneList.tsx (after)
import { useDNSWebSocket, EventType } from '@/hooks/useWebSocket'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'

const ZoneList = () => {
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(false)
  const { subscribe, isConnected } = useDNSWebSocket('user123')
  const { dnsEvents } = useRealTimeEvents()

  // Set up real-time event handlers
  useEffect(() => {
    // Listen for zone creation events
    subscribe(EventType.ZONE_CREATED, (data) => {
      setZones(prevZones => [...prevZones, data])
      toast.success(`Zone ${data.name} created successfully`)
    })

    // Listen for zone updates
    subscribe(EventType.ZONE_UPDATED, (data) => {
      setZones(prevZones => 
        prevZones.map(zone => 
          zone.id === data.id ? { ...zone, ...data } : zone
        )
      )
      toast.info(`Zone ${data.name} updated`)
    })

    // Listen for zone deletions
    subscribe(EventType.ZONE_DELETED, (data) => {
      setZones(prevZones => 
        prevZones.filter(zone => zone.id !== data.id)
      )
      toast.warning(`Zone ${data.name} deleted`)
    })

    // Listen for BIND reload events
    subscribe(EventType.BIND_RELOAD, (data) => {
      if (data.status === 'success') {
        toast.success('DNS server configuration reloaded')
      } else {
        toast.error('Failed to reload DNS server configuration')
      }
    })
  }, [subscribe])

  const createZone = async (zoneData) => {
    setLoading(true)
    try {
      // API call - the real-time update will come via WebSocket
      await api.post('/zones', zoneData)
      // Don't update local state here - let WebSocket handle it
    } catch (error) {
      toast.error('Failed to create zone')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Connection status indicator */}
      <div className="mb-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {isConnected ? 'Real-time updates active' : 'Real-time updates disconnected'}
        </span>
      </div>

      {/* Recent DNS events */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-900 mb-2">Recent DNS Events</h3>
        <div className="space-y-1">
          {dnsEvents.slice(0, 3).map(event => (
            <div key={event.id} className="text-xs text-gray-600">
              {event.type.replace('_', ' ')} - {format(new Date(event.timestamp), 'HH:mm:ss')}
            </div>
          ))}
        </div>
      </div>

      {/* Zone list UI */}
      <div className="space-y-4">
        {zones.map(zone => (
          <ZoneCard key={zone.id} zone={zone} />
        ))}
      </div>
    </div>
  )
}
```

## Service Integration

### DNS Service with Events

```python
# backend/app/services/dns_service.py
from .websocket_events import get_websocket_event_service

class DNSService:
    def __init__(self):
        self.event_service = get_websocket_event_service()
    
    async def create_zone(self, db: AsyncSession, zone_data: DNSZoneCreate, user_id: int):
        """Create DNS zone with real-time events"""
        
        # Create zone in database
        zone = DNSZone(**zone_data.dict(), created_by=user_id)
        db.add(zone)
        await db.commit()
        await db.refresh(zone)
        
        # Emit creation event
        await self.event_service.emit_zone_created({
            "id": zone.id,
            "name": zone.name,
            "type": zone.zone_type,
            "created_by": user_id
        }, user_id=str(user_id))
        
        return zone
    
    async def update_zone(self, db: AsyncSession, zone_id: int, zone_data: DNSZoneUpdate, user_id: int):
        """Update DNS zone with real-time events"""
        
        # Get existing zone
        zone = await db.get(DNSZone, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        # Update zone
        for field, value in zone_data.dict(exclude_unset=True).items():
            setattr(zone, field, value)
        
        await db.commit()
        await db.refresh(zone)
        
        # Emit update event
        await self.event_service.emit_zone_updated({
            "id": zone.id,
            "name": zone.name,
            "type": zone.zone_type,
            "updated_by": user_id,
            "changes": zone_data.dict(exclude_unset=True)
        }, user_id=str(user_id))
        
        return zone
```

## Error Handling with Events

```python
# backend/app/services/bind_service.py
class BindService:
    async def reload_configuration(self, user_id: Optional[int] = None):
        """Reload BIND configuration with event emission"""
        event_service = get_websocket_event_service()
        
        try:
            # Attempt to reload BIND
            result = await self._execute_bind_reload()
            
            if result.returncode == 0:
                # Success - emit success event
                await event_service.emit_bind_reload({
                    "status": "success",
                    "message": "BIND configuration reloaded successfully",
                    "reloaded_by": user_id
                })
            else:
                # Failure - emit error event
                await event_service.emit_bind_reload({
                    "status": "error",
                    "message": f"BIND reload failed: {result.stderr}",
                    "error_code": result.returncode,
                    "attempted_by": user_id
                })
                
        except Exception as e:
            # Exception - emit error event
            await event_service.emit_bind_reload({
                "status": "error",
                "message": f"BIND reload exception: {str(e)}",
                "attempted_by": user_id
            })
            raise
```

## Testing the Integration

### Backend Test

```python
# Test WebSocket event emission
async def test_zone_creation_events():
    # Create a test zone
    response = await client.post("/api/zones", json={
        "name": "test.local",
        "zone_type": "master"
    })
    
    assert response.status_code == 201
    
    # Check that WebSocket event was emitted
    # (This would require a WebSocket test client)
```

### Frontend Test

```typescript
// Test real-time updates
describe('ZoneList Real-time Updates', () => {
  it('should update zone list when zone is created', async () => {
    const { getByText } = render(<ZoneList />)
    
    // Simulate WebSocket event
    mockWebSocket.emit('zone_created', {
      id: 1,
      name: 'test.local',
      type: 'master'
    })
    
    // Check that zone appears in list
    expect(getByText('test.local')).toBeInTheDocument()
  })
})
```

## Key Benefits

1. **Real-time Updates**: Users see changes immediately without refreshing
2. **Better UX**: Instant feedback and notifications
3. **Collaboration**: Multiple users see each other's changes
4. **Error Handling**: Real-time error notifications
5. **System Status**: Live system health and performance updates

## Best Practices

1. **Event Naming**: Use consistent, descriptive event names
2. **Data Structure**: Keep event payloads consistent and well-structured
3. **Error Handling**: Always emit events for both success and failure cases
4. **User Context**: Include user information in events when relevant
5. **Performance**: Batch events when possible to avoid flooding
6. **Security**: Validate user permissions before emitting sensitive events