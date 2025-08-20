# WebSocket Real-Time Event System Implementation

This document describes the comprehensive WebSocket implementation for real-time communication between the backend and frontend of the Hybrid DNS Server.

## Overview

The WebSocket system provides real-time updates for:
- DNS zone and record changes
- Security alerts and threat detection
- Health monitoring and forwarder status
- System status and configuration changes
- User authentication events

## Architecture

### Backend Components

#### 1. WebSocket Manager (`backend/app/websocket/manager.py`)
- **Enhanced Connection Management**: Supports multiple connection types (health, dns_management, security, system, admin)
- **Event-Driven Architecture**: Uses EventType enum for structured event handling
- **Message Queue**: Reliable message delivery with queue processing
- **Connection Metadata**: Tracks user sessions, message counts, and subscriptions
- **Automatic Broadcasting**: Background tasks for health and system updates

#### 2. WebSocket Event Service (`backend/app/services/websocket_events.py`)
- **Event Emission**: Centralized service for emitting events from business logic
- **Decorator Support**: `@emit_websocket_event` for automatic event emission
- **Batch Operations**: `WebSocketEventBatch` context manager for bulk events
- **Error Handling**: Comprehensive error handling and logging

#### 3. WebSocket Endpoints (`backend/main.py`)
- **Multi-Type Connections**: `/ws/{connection_type}/{user_id}` endpoint
- **Message Handling**: Supports ping/pong, subscriptions, and stats requests
- **Backward Compatibility**: Legacy `/ws/health/{user_id}` endpoint maintained

### Frontend Components

#### 1. WebSocket Service (`frontend/src/services/websocketService.ts`)
- **Connection Management**: Automatic reconnection with exponential backoff
- **Event Subscription**: Type-safe event handling with TypeScript enums
- **Message Queuing**: Queues messages when disconnected
- **Connection Types**: Supports all backend connection types

#### 2. Enhanced Hooks (`frontend/src/hooks/useWebSocket.ts`)
- **Legacy Hook**: Maintains backward compatibility
- **Enhanced Hook**: `useWebSocketService` with advanced features
- **Specialized Hooks**: `useHealthWebSocket`, `useDNSWebSocket`, etc.
- **Type Safety**: Full TypeScript support with proper typing

#### 3. Real-Time Event Context (`frontend/src/contexts/RealTimeEventContext.tsx`)
- **Global State**: Manages real-time events across the application
- **Event Categorization**: Separates DNS, security, health, and system events
- **Toast Notifications**: Automatic user notifications for important events
- **Event Acknowledgment**: Mark events as read/acknowledged

#### 4. UI Components
- **Real-Time Notifications** (`frontend/src/components/ui/RealTimeNotifications.tsx`)
- **Connection Status** (`frontend/src/components/ui/ConnectionStatus.tsx`)
- **Real-Time Dashboard** (`frontend/src/components/dashboard/RealTimeDashboard.tsx`)

## Event Types

### DNS Events
- `zone_created` - New DNS zone created
- `zone_updated` - DNS zone modified
- `zone_deleted` - DNS zone removed
- `record_created` - New DNS record added
- `record_updated` - DNS record modified
- `record_deleted` - DNS record removed

### Security Events
- `security_alert` - Security threat or violation detected
- `rpz_update` - Response Policy Zone rules updated
- `threat_detected` - Malware or threat identified

### Health Events
- `health_update` - Periodic health status update
- `health_alert` - Health threshold exceeded
- `forwarder_status_change` - DNS forwarder status changed

### System Events
- `system_status` - System performance metrics
- `bind_reload` - BIND9 configuration reloaded
- `config_change` - System configuration modified

### User Events
- `user_login` - User authentication successful
- `user_logout` - User session ended
- `session_expired` - User session timed out

## Connection Types

### Health (`health`)
- Receives health monitoring updates
- Forwarder status changes
- System performance metrics

### DNS Management (`dns_management`)
- Zone and record CRUD operations
- BIND9 reload notifications
- Configuration changes

### Security (`security`)
- Security alerts and threats
- RPZ rule updates
- Threat detection events

### System (`system`)
- System status updates
- Configuration changes
- User authentication events

### Admin (`admin`)
- Receives all event types
- Full system monitoring
- Administrative notifications

## Usage Examples

### Backend Event Emission

```python
from app.services.websocket_events import get_websocket_event_service

# Emit DNS zone creation event
event_service = get_websocket_event_service()
await event_service.emit_zone_created({
    "name": "example.com",
    "type": "master",
    "records_count": 5
}, user_id="user123")

# Emit security alert
await event_service.emit_security_alert({
    "message": "Suspicious DNS query detected",
    "severity": "warning",
    "source_ip": "192.168.1.100"
})
```

### Frontend Event Handling

```typescript
import { useDNSWebSocket, EventType } from '@/hooks/useWebSocket'

const MyComponent = () => {
  const { subscribe, isConnected } = useDNSWebSocket('user123')

  useEffect(() => {
    // Subscribe to zone creation events
    subscribe(EventType.ZONE_CREATED, (data) => {
      console.log('New zone created:', data)
      toast.success(`Zone ${data.name} created successfully`)
    })

    // Subscribe to record updates
    subscribe(EventType.RECORD_UPDATED, (data) => {
      console.log('Record updated:', data)
      // Update local state or refetch data
    })
  }, [subscribe])

  return (
    <div>
      <p>Connection Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
    </div>
  )
}
```

### Real-Time Context Usage

```typescript
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'

const Dashboard = () => {
  const { 
    events, 
    unreadCount, 
    systemStatus, 
    acknowledgeEvent 
  } = useRealTimeEvents()

  return (
    <div>
      <h2>Recent Events ({unreadCount} unread)</h2>
      {events.map(event => (
        <div key={event.id}>
          <p>{event.type}: {JSON.stringify(event.data)}</p>
          <button onClick={() => acknowledgeEvent(event.id)}>
            Mark as Read
          </button>
        </div>
      ))}
    </div>
  )
}
```

## Configuration

### Backend Configuration

The WebSocket system uses the existing FastAPI configuration. Key settings:

```python
# In app/core/config.py
class Settings(BaseSettings):
    # WebSocket settings
    WEBSOCKET_PING_INTERVAL: int = 30  # seconds
    WEBSOCKET_MAX_RECONNECT_ATTEMPTS: int = 5
    WEBSOCKET_RECONNECT_INTERVAL: int = 5  # seconds
    
    # Broadcasting intervals
    HEALTH_BROADCAST_INTERVAL: int = 30  # seconds
    SYSTEM_BROADCAST_INTERVAL: int = 60  # seconds
```

### Frontend Configuration

WebSocket connections are automatically configured based on the current host:

```typescript
// Automatic protocol detection
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsUrl = `${protocol}//${window.location.host}/ws/${connectionType}/${userId}`
```

## Testing

### Demo Endpoints

The system includes comprehensive demo endpoints for testing:

- `POST /api/websocket-demo/emit-dns-event` - Test DNS events
- `POST /api/websocket-demo/emit-security-event` - Test security events
- `POST /api/websocket-demo/simulate-dns-workflow` - Test complete workflows
- `GET /api/websocket-demo/connection-stats` - Get connection statistics

### Frontend Testing

Use the Real-Time Dashboard component to test all WebSocket functionality:

```typescript
import { RealTimeDashboard } from '@/components/dashboard/RealTimeDashboard'

// In your app
<RealTimeDashboard userId="test-user" />
```

## Monitoring and Debugging

### Connection Statistics

Get real-time connection statistics:

```bash
curl http://localhost:8000/api/websocket-demo/connection-stats
```

### Browser DevTools

Monitor WebSocket connections in browser DevTools:
1. Open Network tab
2. Filter by "WS" (WebSocket)
3. Click on connection to see messages

### Backend Logs

WebSocket events are logged with structured logging:

```
INFO: WebSocket connected for user test-user, type: health
INFO: Emitted zone_created event for zone: example.com
WARNING: Emitted security_alert event: Suspicious activity detected
```

## Security Considerations

### Authentication
- User ID validation should be implemented in production
- JWT token validation for WebSocket connections
- Rate limiting for WebSocket messages

### Authorization
- Connection type restrictions based on user roles
- Event filtering based on user permissions
- Audit logging for sensitive events

### Data Validation
- Input validation for all WebSocket messages
- Sanitization of event data before broadcasting
- Protection against WebSocket flooding

## Performance Optimization

### Connection Management
- Connection pooling and cleanup
- Automatic disconnection of idle connections
- Memory usage monitoring

### Message Optimization
- Message batching for high-frequency events
- Compression for large payloads
- Event deduplication

### Scaling Considerations
- Redis pub/sub for multi-instance deployments
- Load balancing for WebSocket connections
- Horizontal scaling with sticky sessions

## Troubleshooting

### Common Issues

1. **Connection Drops**
   - Check network stability
   - Verify ping/pong mechanism
   - Review reconnection logic

2. **Missing Events**
   - Check event subscription
   - Verify connection type
   - Review backend event emission

3. **Performance Issues**
   - Monitor connection count
   - Check message queue size
   - Review broadcasting intervals

### Debug Commands

```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/ws/health/test-user

# Emit test events
curl -X POST http://localhost:8000/api/websocket-demo/test-all-events?user_id=test-user

# Get connection statistics
curl http://localhost:8000/api/websocket-demo/connection-stats
```

## Future Enhancements

### Planned Features
- Message persistence for offline users
- WebSocket clustering with Redis
- Advanced event filtering and routing
- Real-time collaboration features
- Mobile app WebSocket support

### Integration Opportunities
- Prometheus metrics for WebSocket connections
- Grafana dashboards for real-time monitoring
- Alertmanager integration for critical events
- Webhook support for external integrations

## Conclusion

This WebSocket implementation provides a robust, scalable foundation for real-time communication in the Hybrid DNS Server. The event-driven architecture ensures loose coupling between components while maintaining high performance and reliability.

The system is designed to be:
- **Extensible**: Easy to add new event types and connection types
- **Reliable**: Automatic reconnection and message queuing
- **Performant**: Efficient broadcasting and connection management
- **Secure**: Built-in authentication and authorization hooks
- **Maintainable**: Clean separation of concerns and comprehensive logging