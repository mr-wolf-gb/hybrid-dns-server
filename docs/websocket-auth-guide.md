# WebSocket Authentication & Authorization Guide

## Overview

The Unified WebSocket API implements comprehensive authentication and authorization to ensure secure real-time communication. This guide covers JWT token authentication, role-based access control, and security best practices.

## Authentication Methods

### JWT Token Authentication

All WebSocket connections require a valid JWT token for authentication.

#### Token-Based Connection
```javascript
const token = localStorage.getItem('access_token')
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`)
```

#### Header-Based Authentication (Alternative)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws')
ws.onopen = () => {
  // Send authentication message immediately after connection
  ws.send(JSON.stringify({
    type: 'authenticate',
    data: { token: localStorage.getItem('access_token') }
  }))
}
```

### Token Validation Process

1. **Connection Establishment**: Client provides JWT token
2. **Token Verification**: Server validates token signature and expiration
3. **User Identification**: Server extracts user information from token
4. **Permission Loading**: Server loads user roles and permissions
5. **Connection Authorization**: Server authorizes connection based on user role

### Token Refresh Handling

```javascript
class WebSocketAuthManager {
  private ws: WebSocket | null = null
  private refreshTimer: NodeJS.Timeout | null = null
  
  async connect(token: string) {
    this.ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`)
    
    // Set up token refresh before expiration
    const tokenData = this.parseJWT(token)
    const expiresIn = tokenData.exp * 1000 - Date.now()
    const refreshTime = expiresIn - 60000 // Refresh 1 minute before expiry
    
    this.refreshTimer = setTimeout(() => {
      this.refreshToken()
    }, refreshTime)
  }
  
  private async refreshToken() {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('refresh_token')}`
        }
      })
      
      const { access_token } = await response.json()
      localStorage.setItem('access_token', access_token)
      
      // Reconnect with new token
      this.disconnect()
      await this.connect(access_token)
      
    } catch (error) {
      console.error('Token refresh failed:', error)
      // Redirect to login
      window.location.href = '/login'
    }
  }
}
```

## Authorization Model

### User Roles

#### Admin Role
- **Full Access**: Can subscribe to all event types
- **System Management**: Receives administrative events and alerts
- **User Management**: Can see user authentication events
- **Security Monitoring**: Full access to security events with sensitive data

#### Regular User Role
- **Limited Access**: Can only subscribe to permitted event types
- **Zone-Specific**: Only receives events for zones they have access to
- **Filtered Data**: Sensitive information is filtered from events
- **Personal Events**: Only receives their own authentication events

### Permission Matrix

| Event Type | Admin | Regular User | Notes |
|------------|-------|--------------|-------|
| zone_created | ✅ Full | ✅ Filtered | Users only see zones they can access |
| zone_updated | ✅ Full | ✅ Filtered | Users only see their zones |
| zone_deleted | ✅ Full | ✅ Filtered | Users only see their zones |
| record_created | ✅ Full | ✅ Filtered | Users only see records in their zones |
| record_updated | ✅ Full | ✅ Filtered | Users only see records in their zones |
| record_deleted | ✅ Full | ✅ Filtered | Users only see records in their zones |
| bulk_operation_progress | ✅ Full | ✅ Own Only | Users only see their own operations |
| bulk_operation_complete | ✅ Full | ✅ Own Only | Users only see their own operations |
| security_alert | ✅ Full | ✅ Filtered | Users get general alerts without sensitive data |
| threat_detected | ✅ Full | ❌ Denied | Admin-only event |
| rpz_updated | ✅ Full | ✅ General | Users get general update notifications |
| threat_feed_updated | ✅ Full | ❌ Denied | Admin-only event |
| health_update | ✅ Full | ✅ General | Users get system-wide health status |
| health_alert | ✅ Full | ✅ General | Users get general health alerts |
| forwarder_status_change | ✅ Full | ✅ General | Users get forwarder status updates |
| system_metrics | ✅ Full | ✅ Limited | Users get basic system metrics |
| bind_reload | ✅ Full | ✅ General | Users get reload notifications |
| config_change | ✅ Full | ❌ Denied | Admin-only event |
| user_login | ✅ All Users | ✅ Own Only | Users only see their own login events |
| user_logout | ✅ All Users | ✅ Own Only | Users only see their own logout events |
| session_expired | ✅ All Users | ✅ Own Only | Users only see their own session events |
| permission_changed | ✅ All Users | ✅ Own Only | Users only see their own permission changes |

### Zone-Level Permissions

Users can have different permission levels for different zones:

```typescript
interface UserZonePermissions {
  user_id: string
  zone_permissions: Array<{
    zone_id: string
    zone_name: string
    permissions: ('read' | 'write' | 'delete' | 'admin')[]
  }>
}
```

**Permission Levels:**
- **read**: Can view zone and record events
- **write**: Can receive record creation/update events
- **delete**: Can receive record deletion events
- **admin**: Can receive all zone-related events including configuration changes

## Event Filtering

### Data Filtering by Role

#### Admin User - Full Security Alert
```json
{
  "type": "event",
  "event_type": "security_alert",
  "data": {
    "alert_id": "alert_123",
    "severity": "high",
    "category": "malware",
    "message": "Malware domain query blocked",
    "source_ip": "192.168.1.50",
    "target_domain": "malicious-site.com",
    "query_type": "A",
    "threat_indicators": ["domain_reputation", "threat_feed_match"],
    "details": {
      "rpz_rule": "malware.rpz",
      "threat_feed": "abuse.ch",
      "confidence_score": 0.95,
      "client_hostname": "workstation-01.internal.com"
    }
  }
}
```

#### Regular User - Filtered Security Alert
```json
{
  "type": "event",
  "event_type": "security_alert",
  "data": {
    "alert_id": "alert_123",
    "severity": "high",
    "category": "malware",
    "message": "Security threat detected and blocked by DNS filtering"
  }
}
```

### Zone-Based Filtering

#### Admin User - All Zone Events
```json
{
  "type": "event",
  "event_type": "zone_created",
  "data": {
    "zone_id": "zone_456",
    "zone_name": "internal.company.com",
    "zone_type": "master",
    "created_by": "admin",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Regular User - Only Accessible Zones
```json
{
  "type": "event",
  "event_type": "zone_created",
  "data": {
    "zone_id": "zone_789",
    "zone_name": "department.company.com",
    "zone_type": "master",
    "created_by": "admin",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## Security Implementation

### Connection Security

#### Secure WebSocket (WSS)
Always use WSS in production:

```javascript
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsUrl = `${protocol}//${window.location.host}/ws?token=${token}`
```

#### Origin Validation
Server validates WebSocket origin:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    # Validate origin
    origin = websocket.headers.get("origin")
    if not is_allowed_origin(origin):
        await websocket.close(code=1008, reason="Invalid origin")
        return
    
    # Continue with authentication...
```

#### Rate Limiting
Implement rate limiting to prevent abuse:

```python
class WebSocketRateLimiter:
    def __init__(self):
        self.user_message_counts = {}
        self.rate_limit = 100  # messages per minute
        self.window_size = 60  # seconds
    
    async def check_rate_limit(self, user_id: str) -> bool:
        now = time.time()
        window_start = now - self.window_size
        
        # Clean old entries
        if user_id in self.user_message_counts:
            self.user_message_counts[user_id] = [
                timestamp for timestamp in self.user_message_counts[user_id]
                if timestamp > window_start
            ]
        else:
            self.user_message_counts[user_id] = []
        
        # Check rate limit
        if len(self.user_message_counts[user_id]) >= self.rate_limit:
            return False
        
        # Record message
        self.user_message_counts[user_id].append(now)
        return True
```

### Authentication Error Handling

#### Invalid Token
```json
{
  "type": "error",
  "error_code": "AUTH_FAILED",
  "message": "Authentication token is invalid or expired",
  "details": {
    "reason": "token_expired",
    "expires_at": "2024-01-15T10:00:00Z"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Permission Denied
```json
{
  "type": "error",
  "error_code": "PERMISSION_DENIED",
  "message": "You do not have permission to subscribe to this event type",
  "details": {
    "requested_event": "threat_detected",
    "required_role": "admin",
    "user_role": "user"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Rate Limited
```json
{
  "type": "error",
  "error_code": "RATE_LIMITED",
  "message": "Rate limit exceeded. Too many messages sent.",
  "details": {
    "limit": 100,
    "window_seconds": 60,
    "retry_after": 45
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Best Practices

### Client-Side Security

#### Secure Token Storage
```javascript
// Use secure storage for tokens
class SecureTokenStorage {
  private static readonly ACCESS_TOKEN_KEY = 'dns_access_token'
  private static readonly REFRESH_TOKEN_KEY = 'dns_refresh_token'
  
  static setTokens(accessToken: string, refreshToken: string) {
    // Use httpOnly cookies in production
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
  }
  
  static getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY)
  }
  
  static clearTokens() {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
  }
}
```

#### Connection Validation
```javascript
class SecureWebSocketClient {
  private validateConnection(): boolean {
    // Check if token exists and is not expired
    const token = SecureTokenStorage.getAccessToken()
    if (!token) {
      this.redirectToLogin()
      return false
    }
    
    // Parse JWT and check expiration
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (payload.exp * 1000 < Date.now()) {
        this.refreshTokenAndReconnect()
        return false
      }
    } catch (error) {
      console.error('Invalid token format:', error)
      this.redirectToLogin()
      return false
    }
    
    return true
  }
}
```

### Server-Side Security

#### Token Validation
```python
from jose import JWTError, jwt
from datetime import datetime, timezone

async def validate_websocket_token(token: str) -> Optional[WSUser]:
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None
        
        # Get user information
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Load user from database
        user = await get_user_by_id(user_id)
        if not user or not user.is_active:
            return None
        
        return WSUser(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            permissions=await get_user_permissions(user.id)
        )
        
    except JWTError:
        return None
```

#### Permission Checking
```python
class EventPermissionChecker:
    @staticmethod
    async def can_subscribe_to_event(user: WSUser, event_type: EventType) -> bool:
        # Admin users can subscribe to all events
        if user.is_admin:
            return True
        
        # Check event-specific permissions
        if event_type in [EventType.THREAT_DETECTED, EventType.CONFIG_CHANGE]:
            return False  # Admin-only events
        
        if event_type in [EventType.SECURITY_ALERT, EventType.RPZ_UPDATED]:
            return True  # General security events allowed
        
        # DNS events require zone permissions
        if event_type.startswith('zone_') or event_type.startswith('record_'):
            return len(user.permissions.accessible_zones) > 0
        
        return True
    
    @staticmethod
    async def filter_event_data(user: WSUser, event: Event) -> Dict[str, Any]:
        if user.is_admin:
            return event.data
        
        # Apply role-based filtering
        if event.type == EventType.SECURITY_ALERT:
            return {
                "alert_id": event.data.get("alert_id"),
                "severity": event.data.get("severity"),
                "category": event.data.get("category"),
                "message": event.data.get("message")
            }
        
        # Zone-based filtering for DNS events
        if event.type.startswith('zone_') or event.type.startswith('record_'):
            zone_id = event.data.get("zone_id")
            if zone_id not in user.permissions.accessible_zones:
                return None  # Filter out completely
        
        return event.data
```

### Audit Logging

#### WebSocket Authentication Events
```python
async def log_websocket_auth_event(
    user_id: str,
    event_type: str,
    success: bool,
    details: Dict[str, Any] = None
):
    await create_audit_log({
        "event_type": "websocket_auth",
        "user_id": user_id,
        "action": event_type,
        "success": success,
        "details": details or {},
        "timestamp": datetime.utcnow(),
        "source": "websocket"
    })

# Usage examples:
await log_websocket_auth_event(
    user_id="user_123",
    event_type="connection_established",
    success=True,
    details={"ip_address": "192.168.1.100"}
)

await log_websocket_auth_event(
    user_id="user_456",
    event_type="subscription_denied",
    success=False,
    details={
        "requested_event": "threat_detected",
        "reason": "insufficient_permissions"
    }
)
```

## Troubleshooting Authentication Issues

### Common Authentication Problems

#### 1. Token Expired
**Symptoms**: Connection immediately closes with AUTH_FAILED error
**Solution**: Implement automatic token refresh

```javascript
ws.onerror = (error) => {
  if (error.code === 1008) { // Authentication failed
    this.refreshTokenAndReconnect()
  }
}
```

#### 2. Invalid Token Format
**Symptoms**: Connection rejected with malformed token error
**Solution**: Validate token format before connection

```javascript
function isValidJWT(token: string): boolean {
  const parts = token.split('.')
  return parts.length === 3 && parts.every(part => part.length > 0)
}
```

#### 3. Permission Denied for Events
**Symptoms**: Subscription requests return PERMISSION_DENIED errors
**Solution**: Check user role and request appropriate events

```javascript
const allowedEvents = user.is_admin 
  ? ALL_EVENT_TYPES 
  : USER_ALLOWED_EVENTS

subscribe(allowedEvents)
```

### Debug Authentication

#### Enable Debug Mode
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}&debug=true`)
```

#### Check Token Payload
```javascript
function debugToken(token: string) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    console.log('Token payload:', payload)
    console.log('Expires at:', new Date(payload.exp * 1000))
    console.log('User ID:', payload.sub)
    console.log('Is Admin:', payload.is_admin)
  } catch (error) {
    console.error('Invalid token:', error)
  }
}
```

This comprehensive authentication and authorization guide ensures secure WebSocket communication while providing the flexibility needed for different user roles and permissions.