# WebSocket Setup for Fresh Installation

## Overview
The frontend WebSocket implementation has been optimized to prevent connection storms and ensure reliable real-time communication with the backend.

## Key Changes Made

### 1. Single Connection Architecture
- **Before**: Multiple WebSocket connections (health, dns_management, security, system, admin)
- **After**: Single admin connection that receives all event types
- **Benefit**: Eliminates connection storms and reduces server load

### 2. Global WebSocket Service
- **File**: `src/services/GlobalWebSocketService.ts`
- **Purpose**: Manages WebSocket connections globally to prevent duplicates
- **Features**: 
  - Connection deduplication
  - Automatic reconnection
  - Subscriber management
  - Event broadcasting

### 3. Updated WebSocket Context
- **File**: `src/contexts/WebSocketContext.tsx`
- **Changes**: 
  - Uses GlobalWebSocketService
  - Single admin connection
  - Backward compatibility maintained
  - Proper cleanup on logout

### 4. Fixed RealTimeEventContext
- **File**: `src/contexts/RealTimeEventContext.tsx`
- **Changes**:
  - No longer creates additional WebSocket connections
  - Uses existing WebSocketContext
  - Proper event handling and routing

### 5. Component Updates
Updated components to use WebSocketContext instead of deprecated hooks:
- `src/components/system/LiveConfigurationMonitor.tsx`
- `src/components/dashboard/RealTimeQueryMonitor.tsx`
- `src/components/dashboard/RealTimeDashboard.tsx`
- `src/components/dashboard/RealTimeChart.tsx`

### 6. Deprecated Hook Safety
- **File**: `src/hooks/useWebSocket.ts`
- **Changes**: Specialized hooks now return mock objects with warnings
- **Purpose**: Prevents accidental creation of additional connections

## Configuration Files

### WebSocket Configuration
- **File**: `src/config/websocket.ts`
- **Contains**: 
  - Connection settings
  - Event types
  - Default subscriptions
  - URL construction helpers

## Provider Setup

The WebSocket providers are properly nested in `src/main.tsx`:

```tsx
<AuthProvider>
  <WebSocketProvider>
    <RealTimeEventProvider>
      <App />
    </RealTimeEventProvider>
  </WebSocketProvider>
</AuthProvider>
```

## Connection Flow

1. User logs in → AuthContext provides access token
2. WebSocketContext creates single admin connection using GlobalWebSocketService
3. RealTimeEventContext subscribes to events from WebSocketContext
4. Components use WebSocketContext for real-time updates
5. User logs out → All connections properly cleaned up

## Event Types Supported

- **Health Events**: health_update, health_alert, forwarder_status_change
- **DNS Events**: zone_created, zone_updated, zone_deleted, record_created, record_updated, record_deleted
- **Security Events**: security_alert, rpz_update, threat_detected
- **System Events**: system_status, bind_reload, config_change
- **User Events**: user_login, user_logout, session_expired

## Benefits of New Architecture

1. **No Connection Storms**: Single connection prevents rapid connection/disconnection cycles
2. **Better Resource Usage**: Reduced server load and client-side resource consumption
3. **Improved Reliability**: Proper connection management and cleanup
4. **Backward Compatibility**: Existing components continue to work without changes
5. **Centralized Management**: All WebSocket logic in one place for easier maintenance

## Testing the Setup

After fresh installation, verify:

1. Only one WebSocket connection is created per user
2. Real-time events are properly received and displayed
3. Connection is properly cleaned up on logout
4. No connection storms in server logs
5. All dashboard components receive real-time updates

## Troubleshooting

If issues occur:

1. Check browser developer tools → Network tab for WebSocket connections
2. Verify only one WebSocket connection exists
3. Check server logs for connection patterns
4. Ensure proper authentication token is being used
5. Verify WebSocketProvider is properly wrapped around the app

## Files Modified/Created

### Modified:
- `src/contexts/WebSocketContext.tsx`
- `src/contexts/RealTimeEventContext.tsx`
- `src/hooks/useWebSocket.ts`
- `src/components/system/LiveConfigurationMonitor.tsx`
- `src/components/dashboard/RealTimeQueryMonitor.tsx`
- `src/components/dashboard/RealTimeDashboard.tsx`
- `src/components/dashboard/RealTimeChart.tsx`

### Created:
- `src/services/GlobalWebSocketService.ts`
- `src/services/WebSocketConnectionManager.ts`
- `src/config/websocket.ts`
- `frontend/WEBSOCKET_SETUP.md`

This setup ensures a clean, efficient WebSocket implementation that will work reliably on the fresh server installation.