# Unified WebSocket API Documentation

## Overview

The Unified WebSocket API provides a single, optimized connection per user for real-time communication between the frontend and backend. This replaces the previous multiple connection approach with a more efficient, resource-optimized system.

## Key Features

- **Single Connection Per User**: One WebSocket connection handles all event types
- **Dynamic Subscriptions**: Subscribe/unsubscribe to event types on demand
- **Permission-Based Filtering**: Events filtered based on user roles and permissions
- **Automatic Reconnection**: Built-in connection health monitoring and recovery
- **Message Batching**: Optimized message delivery with batching and priority queuing

## WebSocket Endpoint

### Connection URL
```
ws://localhost:8000/ws
wss://yourdomain.com/ws  (production with SSL)
```

### Authentication
All WebSocket connections require JWT authentication:

```javascript
const token = localStorage.getItem('access_token')
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`)
```

## Message Format

All WebSocket messages follow a standardized JSON format:

### Outgoing Messages (Client to Server)

```typescript
interface WebSocketMessage {
  type: MessageType
  data?: any
  id?: string  // Optional message ID for tracking
}

enum MessageType {
  // Connection management
  PING = 'ping',
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',
  
  // Administrative
  GET_STATS = 'get_stats',
  GET_SUBSCRIPTIONS = 'get_subscriptions'
}
```

### Incoming Messages (Server to Client)

```typescript
interface IncomingMessage {
  type: 'event' | 'response' | 'error' | 'pong'
  event_type?: EventType  // For event messages
  data: any
  timestamp: string
  id?: string
  priority?: 'low' | 'normal' | 'high' | 'critical'
}
```

## Event Types

### DNS Events
```typescript
enum DNSEventType {
  ZONE_CREATED = 'zone_created',
  ZONE_UPDATED = 'zone_updated', 
  ZONE_DELETED = 'zone_deleted',
  RECORD_CREATED = 'record_created',
  RECORD_UPDATED = 'record_updated',
  RECORD_DELETED = 'record_deleted',
  BULK_OPERATION_PROGRESS = 'bulk_operation_progress',
  BULK_OPERATION_COMPLETE = 'bulk_operation_complete'
}
```

### Security Events
```typescript
enum SecurityEventType {
  SECURITY_ALERT = 'security_alert',
  THREAT_DETECTED = 'threat_detected',
  RPZ_UPDATED = 'rpz_updated',
  THREAT_FEED_UPDATED = 'threat_feed_updated'
}
```

### System Events
```typescript
enum SystemEventType {
  HEALTH_UPDATE = 'health_update',
  HEALTH_ALERT = 'health_alert',
  FORWARDER_STATUS_CHANGE = 'forwarder_status_change',
  SYSTEM_METRICS = 'system_metrics',
  BIND_RELOAD = 'bind_reload',
  CONFIG_CHANGE = 'config_change'
}
```

### User Events
```typescript
enum UserEventType {
  USER_LOGIN = 'user_login',
  USER_LOGOUT = 'user_logout',
  SESSION_EXPIRED = 'session_expired',
  PERMISSION_CHANGED = 'permission_changed'
}
```

## Subscription Management

### Subscribe to Events

```javascript
// Subscribe to specific event types
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    event_types: ['zone_created', 'zone_updated', 'security_alert']
  }
}))
```

### Unsubscribe from Events

```javascript
// Unsubscribe from specific event types
ws.send(JSON.stringify({
  type: 'unsubscribe',
  data: {
    event_types: ['zone_created']
  }
}))
```

### Get Current Subscriptions

```javascript
ws.send(JSON.stringify({
  type: 'get_subscriptions'
}))

// Response:
{
  "type": "response",
  "data": {
    "subscriptions": ["zone_created", "zone_updated", "security_alert"],
    "default_subscriptions": ["health_update", "system_metrics"]
  }
}
```

## Default Subscriptions

Users automatically receive default subscriptions based on their role:

### Admin Users
- All event types available
- System-wide monitoring events
- Administrative notifications

### Regular Users
- DNS events for zones they have access to
- General health updates
- User-specific notifications

## Event Data Formats

### DNS Zone Events

```typescript
interface ZoneEvent {
  zone_id: string
  zone_name: string
  zone_type: 'master' | 'slave' | 'forward'
  action: 'created' | 'updated' | 'deleted'
  changes?: {
    field: string
    old_value: any
    new_value: any
  }[]
  user_id: string
  timestamp: string
}
```

### DNS Record Events

```typescript
interface RecordEvent {
  record_id: string
  zone_id: string
  zone_name: string
  record_name: string
  record_type: 'A' | 'AAAA' | 'CNAME' | 'MX' | 'TXT' | 'SRV' | 'PTR'
  record_value: string
  action: 'created' | 'updated' | 'deleted'
  changes?: {
    field: string
    old_value: any
    new_value: any
  }[]
  user_id: string
  timestamp: string
}
```

### Security Events

```typescript
interface SecurityEvent {
  alert_id: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  category: 'malware' | 'phishing' | 'suspicious' | 'policy_violation'
  message: string
  source_ip?: string
  domain?: string
  details: Record<string, any>
  timestamp: string
}
```

### Health Events

```typescript
interface HealthEvent {
  component: 'bind9' | 'forwarder' | 'system' | 'database'
  status: 'healthy' | 'warning' | 'critical' | 'unknown'
  metrics: {
    cpu_usage?: number
    memory_usage?: number
    disk_usage?: number
    response_time?: number
    error_rate?: number
  }
  message?: string
  timestamp: string
}
```

### System Metrics Events

```typescript
interface SystemMetricsEvent {
  metrics: {
    cpu: {
      usage_percent: number
      load_average: number[]
    }
    memory: {
      total: number
      used: number
      available: number
      usage_percent: number
    }
    disk: {
      total: number
      used: number
      available: number
      usage_percent: number
    }
    network: {
      bytes_sent: number
      bytes_received: number
      packets_sent: number
      packets_received: number
    }
    dns: {
      queries_per_second: number
      active_zones: number
      total_records: number
    }
  }
  timestamp: string
}
```

## Connection Management

### Connection Lifecycle

1. **Connect**: Establish WebSocket connection with JWT token
2. **Authenticate**: Server validates token and user permissions
3. **Subscribe**: Client receives default subscriptions based on user role
4. **Communicate**: Bi-directional message exchange
5. **Disconnect**: Graceful connection termination

### Health Monitoring

The connection includes automatic health monitoring:

```javascript
// Server sends ping every 30 seconds
{
  "type": "ping",
  "timestamp": "2024-01-15T10:30:00Z"
}

// Client should respond with pong
ws.send(JSON.stringify({
  type: 'pong',
  timestamp: new Date().toISOString()
}))
```

### Automatic Reconnection

The client should implement automatic reconnection with exponential backoff:

```javascript
class UnifiedWebSocketService {
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private baseReconnectDelay = 1000 // 1 second
  
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }
    
    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts)
    setTimeout(() => {
      this.connect()
      this.reconnectAttempts++
    }, delay)
  }
}
```

## Error Handling

### Error Message Format

```typescript
interface ErrorMessage {
  type: 'error'
  error_code: string
  message: string
  details?: any
  timestamp: string
}
```

### Common Error Codes

- `AUTH_FAILED`: Authentication token invalid or expired
- `PERMISSION_DENIED`: User lacks permission for requested operation
- `INVALID_MESSAGE`: Message format is invalid
- `SUBSCRIPTION_FAILED`: Unable to subscribe to requested event types
- `RATE_LIMITED`: Too many messages sent in short period
- `CONNECTION_LIMIT`: Maximum connections per user exceeded

### Error Handling Example

```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  
  if (message.type === 'error') {
    switch (message.error_code) {
      case 'AUTH_FAILED':
        // Redirect to login
        window.location.href = '/login'
        break
      case 'PERMISSION_DENIED':
        // Show permission error
        showError('You do not have permission for this operation')
        break
      case 'RATE_LIMITED':
        // Implement backoff
        setTimeout(() => retryMessage(), 5000)
        break
      default:
        console.error('WebSocket error:', message)
    }
  }
}
```

## Rate Limiting

The WebSocket connection implements rate limiting to prevent abuse:

- **Message Rate**: Maximum 100 messages per minute per user
- **Subscription Changes**: Maximum 10 subscription changes per minute
- **Administrative Commands**: Maximum 5 per minute for non-admin users

Rate limit exceeded responses:

```json
{
  "type": "error",
  "error_code": "RATE_LIMITED",
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "details": {
    "limit": 100,
    "window": 60,
    "retry_after": 45
  }
}
```

## Performance Considerations

### Message Batching

The server automatically batches related events to optimize network usage:

```json
{
  "type": "batch",
  "events": [
    {
      "event_type": "record_created",
      "data": { "record_id": "1", "name": "test1.example.com" }
    },
    {
      "event_type": "record_created", 
      "data": { "record_id": "2", "name": "test2.example.com" }
    }
  ],
  "batch_id": "batch_123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Priority Queuing

Events are prioritized for delivery:

- **Critical**: Security alerts, system failures (immediate delivery)
- **High**: DNS changes, health alerts (< 1 second delay)
- **Normal**: Regular updates, metrics (< 5 second delay)
- **Low**: Background events, statistics (< 30 second delay)

## Security

### Authentication

- JWT token required for all connections
- Token validation on every message
- Automatic disconnection on token expiration

### Authorization

- Role-based event filtering
- Permission checks before event delivery
- Audit logging for all WebSocket activities

### Data Protection

- Sensitive data filtered based on user permissions
- No sensitive information in error messages
- Secure WebSocket (WSS) required in production

## Monitoring and Debugging

### Connection Statistics

Get real-time connection statistics:

```javascript
ws.send(JSON.stringify({
  type: 'get_stats'
}))

// Response:
{
  "type": "response",
  "data": {
    "connection_id": "conn_123",
    "connected_at": "2024-01-15T10:00:00Z",
    "messages_sent": 150,
    "messages_received": 45,
    "subscriptions": ["zone_created", "health_update"],
    "last_activity": "2024-01-15T10:29:30Z"
  }
}
```

### Debug Mode

Enable debug mode for detailed logging:

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}&debug=true`)
```

## Migration from Legacy System

### Legacy Endpoint Support

The legacy multiple connection endpoints are deprecated but still supported:

- `/ws/health/{user_id}` → Use unified `/ws` with health event subscriptions
- `/ws/dns_management/{user_id}` → Use unified `/ws` with DNS event subscriptions
- `/ws/security/{user_id}` → Use unified `/ws` with security event subscriptions

### Migration Timeline

1. **Phase 1**: Both systems run in parallel
2. **Phase 2**: New features only available on unified endpoint
3. **Phase 3**: Legacy endpoints return deprecation warnings
4. **Phase 4**: Legacy endpoints removed

## Code Examples

### Complete Connection Setup

```typescript
class UnifiedWebSocketService {
  private ws: WebSocket | null = null
  private subscriptions = new Set<string>()
  private eventHandlers = new Map<string, Set<Function>>()
  
  async connect(token: string): Promise<void> {
    const wsUrl = `${this.getWebSocketUrl()}/ws?token=${token}`
    this.ws = new WebSocket(wsUrl)
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.subscribeToDefaults()
    }
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.handleMessage(message)
    }
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.reconnect()
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }
  
  subscribe(eventTypes: string[]): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        data: { event_types: eventTypes }
      }))
      eventTypes.forEach(type => this.subscriptions.add(type))
    }
  }
  
  on(eventType: string, handler: Function): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set())
    }
    this.eventHandlers.get(eventType)!.add(handler)
  }
  
  private handleMessage(message: any): void {
    if (message.type === 'event' && message.event_type) {
      const handlers = this.eventHandlers.get(message.event_type)
      if (handlers) {
        handlers.forEach(handler => handler(message.data))
      }
    }
  }
}
```

### React Hook Integration

```typescript
import { useEffect, useRef, useState } from 'react'

export function useUnifiedWebSocket(token: string) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const wsService = useRef<UnifiedWebSocketService>()
  
  useEffect(() => {
    wsService.current = new UnifiedWebSocketService()
    
    wsService.current.connect(token).then(() => {
      setIsConnected(true)
    })
    
    return () => {
      wsService.current?.disconnect()
    }
  }, [token])
  
  const subscribe = (eventTypes: string[]) => {
    wsService.current?.subscribe(eventTypes)
  }
  
  const on = (eventType: string, handler: Function) => {
    wsService.current?.on(eventType, handler)
  }
  
  return { isConnected, subscribe, on, lastMessage }
}
```

This unified WebSocket API provides a more efficient, scalable, and maintainable real-time communication system for the Hybrid DNS Server.