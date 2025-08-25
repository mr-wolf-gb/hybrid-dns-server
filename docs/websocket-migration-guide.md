# WebSocket System Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from the legacy multi-connection WebSocket system to the new unified WebSocket system. The new system uses a single connection per user with dynamic event subscriptions, providing better performance and resource utilization.

## Migration Timeline

### Phase 1: Preparation (Week 1)
- Review existing WebSocket usage in your codebase
- Update dependencies and prepare development environment
- Test new WebSocket service in development

### Phase 2: Frontend Migration (Week 2-3)
- Replace legacy WebSocket connections with unified service
- Update event handlers and subscription management
- Test all WebSocket functionality

### Phase 3: Cleanup (Week 4)
- Remove legacy WebSocket code
- Update documentation and examples
- Deploy to production with monitoring

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] Reviewed all existing WebSocket usage in your application
- [ ] Identified all event types currently being used
- [ ] Documented current authentication and authorization patterns
- [ ] Set up development environment with new WebSocket system
- [ ] Created backup of existing WebSocket implementation

## Step-by-Step Migration

### Step 1: Install New WebSocket Service

First, add the new unified WebSocket service to your frontend:

```typescript
// src/services/UnifiedWebSocketService.ts
import { UnifiedWebSocketService } from './websocket/UnifiedWebSocketService';

// Create singleton instance
export const websocketService = new UnifiedWebSocketService();
```

### Step 2: Replace Legacy Connection Management

**Before (Legacy System):**
```typescript
// Multiple connections - OLD WAY
const healthWs = new WebSocket('/ws/health');
const dnsWs = new WebSocket('/ws/dns_management');
const securityWs = new WebSocket('/ws/security');
const systemWs = new WebSocket('/ws/system');
const adminWs = new WebSocket('/ws/admin');

// Separate event handlers
healthWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleHealthEvent(data);
};

dnsWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleDnsEvent(data);
};
```

**After (Unified System):**
```typescript
// Single connection - NEW WAY
import { websocketService } from '../services/websocket';
import { EventType } from '../types/websocket';

// Connect once
await websocketService.connect(authToken);

// Subscribe to specific event types
await websocketService.subscribe([
  EventType.HEALTH_STATUS,
  EventType.DNS_RECORD_CHANGED,
  EventType.SECURITY_ALERT,
  EventType.SYSTEM_METRICS
]);

// Single event handler with routing
websocketService.on(EventType.HEALTH_STATUS, handleHealthEvent);
websocketService.on(EventType.DNS_RECORD_CHANGED, handleDnsEvent);
websocketService.on(EventType.SECURITY_ALERT, handleSecurityEvent);
```

### Step 3: Update React Components

**Before (Legacy Hooks):**
```typescript
// Legacy custom hooks - OLD WAY
const useHealthWebSocket = () => {
  const [healthData, setHealthData] = useState(null);
  
  useEffect(() => {
    const ws = new WebSocket('/ws/health');
    ws.onmessage = (event) => {
      setHealthData(JSON.parse(event.data));
    };
    
    return () => ws.close();
  }, []);
  
  return healthData;
};

const useDnsWebSocket = () => {
  const [dnsEvents, setDnsEvents] = useState([]);
  
  useEffect(() => {
    const ws = new WebSocket('/ws/dns_management');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setDnsEvents(prev => [...prev, data]);
    };
    
    return () => ws.close();
  }, []);
  
  return dnsEvents;
};
```

**After (Unified Hook):**
```typescript
// New unified hook - NEW WAY
const useWebSocketEvents = (eventTypes: EventType[]) => {
  const [events, setEvents] = useState<Record<EventType, any>>({});
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        const token = getAuthToken();
        await websocketService.connect(token);
        await websocketService.subscribe(eventTypes);
        setIsConnected(true);
        
        // Set up event handlers
        eventTypes.forEach(eventType => {
          websocketService.on(eventType, (data) => {
            setEvents(prev => ({
              ...prev,
              [eventType]: data
            }));
          });
        });
        
      } catch (error) {
        console.error('WebSocket connection failed:', error);
        setIsConnected(false);
      }
    };
    
    initializeWebSocket();
    
    return () => {
      eventTypes.forEach(eventType => {
        websocketService.off(eventType);
      });
    };
  }, [eventTypes]);
  
  return { events, isConnected };
};

// Usage in components
const HealthDashboard = () => {
  const { events, isConnected } = useWebSocketEvents([
    EventType.HEALTH_STATUS,
    EventType.SYSTEM_METRICS
  ]);
  
  const healthData = events[EventType.HEALTH_STATUS];
  const systemMetrics = events[EventType.SYSTEM_METRICS];
  
  return (
    <div>
      <ConnectionStatus connected={isConnected} />
      <HealthMetrics data={healthData} />
      <SystemMetrics data={systemMetrics} />
    </div>
  );
};
```

### Step 4: Update Authentication Handling

**Before (Legacy Auth):**
```typescript
// Multiple auth tokens - OLD WAY
const connectWebSockets = async () => {
  const token = await getAuthToken();
  
  const healthWs = new WebSocket(`/ws/health?token=${token}`);
  const dnsWs = new WebSocket(`/ws/dns_management?token=${token}`);
  const securityWs = new WebSocket(`/ws/security?token=${token}`);
  // ... more connections
};
```

**After (Unified Auth):**
```typescript
// Single auth with automatic refresh - NEW WAY
const connectWebSocket = async () => {
  try {
    const token = await getAuthToken();
    await websocketService.connect(token);
    
    // Handle token refresh automatically
    websocketService.onAuthError(async () => {
      const newToken = await refreshAuthToken();
      await websocketService.reconnectWithToken(newToken);
    });
    
  } catch (error) {
    handleAuthError(error);
  }
};
```

### Step 5: Update Event Handling Patterns

**Before (Legacy Event Handling):**
```typescript
// Scattered event handling - OLD WAY
healthWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'forwarder_status') {
    updateForwarderStatus(data.payload);
  } else if (data.type === 'system_health') {
    updateSystemHealth(data.payload);
  }
};

dnsWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'zone_updated') {
    refreshZoneList();
  } else if (data.type === 'record_changed') {
    updateRecordInList(data.payload);
  }
};
```

**After (Centralized Event Handling):**
```typescript
// Centralized event management - NEW WAY
class EventManager {
  private handlers: Map<EventType, Set<EventHandler>> = new Map();
  
  constructor() {
    this.initializeWebSocket();
  }
  
  private async initializeWebSocket() {
    await websocketService.connect(getAuthToken());
    
    // Subscribe to all required events
    await websocketService.subscribe([
      EventType.FORWARDER_STATUS_CHANGED,
      EventType.SYSTEM_HEALTH_UPDATED,
      EventType.DNS_ZONE_UPDATED,
      EventType.DNS_RECORD_CHANGED
    ]);
    
    // Set up centralized routing
    Object.values(EventType).forEach(eventType => {
      websocketService.on(eventType, (data) => {
        this.handleEvent(eventType, data);
      });
    });
  }
  
  private handleEvent(eventType: EventType, data: any) {
    const handlers = this.handlers.get(eventType);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }
  
  public subscribe(eventType: EventType, handler: EventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
  }
  
  public unsubscribe(eventType: EventType, handler: EventHandler) {
    const handlers = this.handlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }
}

// Usage
const eventManager = new EventManager();

// Subscribe to specific events
eventManager.subscribe(EventType.FORWARDER_STATUS_CHANGED, updateForwarderStatus);
eventManager.subscribe(EventType.DNS_ZONE_UPDATED, refreshZoneList);
eventManager.subscribe(EventType.DNS_RECORD_CHANGED, updateRecordInList);
```

### Step 6: Update Error Handling

**Before (Legacy Error Handling):**
```typescript
// Individual error handling - OLD WAY
healthWs.onerror = (error) => {
  console.error('Health WebSocket error:', error);
  // Reconnect logic for health WS
};

dnsWs.onerror = (error) => {
  console.error('DNS WebSocket error:', error);
  // Reconnect logic for DNS WS
};
```

**After (Unified Error Handling):**
```typescript
// Centralized error handling - NEW WAY
websocketService.onError((error) => {
  console.error('WebSocket error:', error);
  
  // Show user-friendly error message
  showNotification({
    type: 'error',
    message: 'Connection lost. Attempting to reconnect...',
    duration: 5000
  });
});

websocketService.onReconnect(() => {
  showNotification({
    type: 'success',
    message: 'Connection restored',
    duration: 3000
  });
});

websocketService.onReconnectFailed((attempts) => {
  showNotification({
    type: 'error',
    message: `Failed to reconnect after ${attempts} attempts. Please refresh the page.`,
    persistent: true
  });
});
```

## Common Migration Patterns

### Pattern 1: Dashboard Components

**Before:**
```typescript
const Dashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [dnsStats, setDnsStats] = useState(null);
  const [securityAlerts, setSecurityAlerts] = useState([]);
  
  useEffect(() => {
    // Multiple WebSocket connections
    const healthWs = new WebSocket('/ws/health');
    const dnsWs = new WebSocket('/ws/dns_management');
    const securityWs = new WebSocket('/ws/security');
    
    healthWs.onmessage = (e) => setHealthData(JSON.parse(e.data));
    dnsWs.onmessage = (e) => setDnsStats(JSON.parse(e.data));
    securityWs.onmessage = (e) => setSecurityAlerts(prev => [...prev, JSON.parse(e.data)]);
    
    return () => {
      healthWs.close();
      dnsWs.close();
      securityWs.close();
    };
  }, []);
  
  return (
    <div>
      <HealthWidget data={healthData} />
      <DNSStats data={dnsStats} />
      <SecurityAlerts alerts={securityAlerts} />
    </div>
  );
};
```

**After:**
```typescript
const Dashboard = () => {
  const { events, isConnected } = useWebSocketEvents([
    EventType.HEALTH_STATUS,
    EventType.DNS_STATISTICS,
    EventType.SECURITY_ALERT
  ]);
  
  return (
    <div>
      <ConnectionIndicator connected={isConnected} />
      <HealthWidget data={events[EventType.HEALTH_STATUS]} />
      <DNSStats data={events[EventType.DNS_STATISTICS]} />
      <SecurityAlerts alerts={events[EventType.SECURITY_ALERT]} />
    </div>
  );
};
```

### Pattern 2: Real-time Lists

**Before:**
```typescript
const DNSRecordsList = () => {
  const [records, setRecords] = useState([]);
  
  useEffect(() => {
    // Initial load
    fetchRecords().then(setRecords);
    
    // WebSocket for updates
    const ws = new WebSocket('/ws/dns_management');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'record_changed') {
        setRecords(prev => updateRecordInList(prev, data.payload));
      }
    };
    
    return () => ws.close();
  }, []);
  
  return (
    <div>
      {records.map(record => (
        <RecordItem key={record.id} record={record} />
      ))}
    </div>
  );
};
```

**After:**
```typescript
const DNSRecordsList = () => {
  const [records, setRecords] = useState([]);
  const { events } = useWebSocketEvents([EventType.DNS_RECORD_CHANGED]);
  
  useEffect(() => {
    fetchRecords().then(setRecords);
  }, []);
  
  useEffect(() => {
    const recordEvent = events[EventType.DNS_RECORD_CHANGED];
    if (recordEvent) {
      setRecords(prev => updateRecordInList(prev, recordEvent));
    }
  }, [events]);
  
  return (
    <div>
      {records.map(record => (
        <RecordItem key={record.id} record={record} />
      ))}
    </div>
  );
};
```

### Pattern 3: Admin Panels

**Before:**
```typescript
const AdminPanel = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminData, setAdminData] = useState(null);
  
  useEffect(() => {
    if (user.role === 'admin') {
      setIsAdmin(true);
      const adminWs = new WebSocket('/ws/admin');
      adminWs.onmessage = (e) => setAdminData(JSON.parse(e.data));
      return () => adminWs.close();
    }
  }, [user]);
  
  if (!isAdmin) return <div>Access denied</div>;
  
  return <AdminDashboard data={adminData} />;
};
```

**After:**
```typescript
const AdminPanel = () => {
  const { events, isConnected } = useWebSocketEvents(
    user.role === 'admin' ? [
      EventType.ADMIN_METRICS,
      EventType.USER_ACTIVITY,
      EventType.SYSTEM_ALERTS
    ] : []
  );
  
  if (user.role !== 'admin') {
    return <div>Access denied</div>;
  }
  
  return (
    <AdminDashboard 
      metrics={events[EventType.ADMIN_METRICS]}
      userActivity={events[EventType.USER_ACTIVITY]}
      alerts={events[EventType.SYSTEM_ALERTS]}
      connected={isConnected}
    />
  );
};
```

## Testing Migration

### Unit Tests

```typescript
// Test unified WebSocket service
describe('UnifiedWebSocketService', () => {
  let service: UnifiedWebSocketService;
  let mockWebSocket: jest.Mocked<WebSocket>;
  
  beforeEach(() => {
    service = new UnifiedWebSocketService();
    mockWebSocket = createMockWebSocket();
    (global as any).WebSocket = jest.fn(() => mockWebSocket);
  });
  
  test('should connect and authenticate', async () => {
    const token = 'test-token';
    await service.connect(token);
    
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'auth',
        token: token
      })
    );
  });
  
  test('should subscribe to events', async () => {
    await service.connect('token');
    await service.subscribe([EventType.DNS_RECORD_CHANGED]);
    
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'subscribe',
        eventTypes: [EventType.DNS_RECORD_CHANGED]
      })
    );
  });
  
  test('should handle reconnection', async () => {
    await service.connect('token');
    
    // Simulate connection loss
    mockWebSocket.onclose({ code: 1006, reason: 'Connection lost' });
    
    // Should attempt reconnection
    await new Promise(resolve => setTimeout(resolve, 1100)); // Wait for reconnect delay
    
    expect(global.WebSocket).toHaveBeenCalledTimes(2);
  });
});
```

### Integration Tests

```typescript
// Test component integration
describe('Dashboard Integration', () => {
  test('should receive and display WebSocket events', async () => {
    const { getByTestId } = render(<Dashboard />);
    
    // Wait for WebSocket connection
    await waitFor(() => {
      expect(getByTestId('connection-status')).toHaveTextContent('Connected');
    });
    
    // Simulate WebSocket event
    const mockEvent = {
      type: EventType.HEALTH_STATUS,
      data: { status: 'healthy', uptime: 3600 }
    };
    
    act(() => {
      websocketService.emit(EventType.HEALTH_STATUS, mockEvent.data);
    });
    
    // Verify event is displayed
    await waitFor(() => {
      expect(getByTestId('health-status')).toHaveTextContent('healthy');
    });
  });
});
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Connection Fails to Establish

**Symptoms:**
- WebSocket connection never opens
- Authentication errors in console
- "Connection failed" messages

**Solutions:**
```typescript
// Check token validity
const token = getAuthToken();
if (!token || isTokenExpired(token)) {
  await refreshAuthToken();
}

// Verify WebSocket URL
const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
console.log('Connecting to:', wsUrl);

// Check network connectivity
try {
  await fetch('/api/health');
} catch (error) {
  console.error('Backend not reachable:', error);
}
```

#### Issue 2: Events Not Received

**Symptoms:**
- WebSocket connects but no events arrive
- Some event types work, others don't
- Intermittent event delivery

**Solutions:**
```typescript
// Verify subscription
const currentSubscriptions = await websocketService.getSubscriptions();
console.log('Current subscriptions:', currentSubscriptions);

// Check user permissions
const userPermissions = await getUserPermissions();
console.log('User can access:', userPermissions.allowedEventTypes);

// Debug event filtering
websocketService.onDebug((message) => {
  console.log('WebSocket debug:', message);
});
```

#### Issue 3: Memory Leaks

**Symptoms:**
- Increasing memory usage over time
- Browser becomes slow
- Multiple WebSocket connections

**Solutions:**
```typescript
// Ensure proper cleanup
useEffect(() => {
  const eventTypes = [EventType.DNS_RECORD_CHANGED];
  
  websocketService.subscribe(eventTypes);
  
  return () => {
    // Important: Clean up subscriptions
    websocketService.unsubscribe(eventTypes);
  };
}, []);

// Check for duplicate connections
const connectionCount = websocketService.getConnectionCount();
if (connectionCount > 1) {
  console.warn('Multiple WebSocket connections detected');
}
```

#### Issue 4: Reconnection Issues

**Symptoms:**
- Connection drops and doesn't reconnect
- Exponential backoff not working
- Authentication fails on reconnect

**Solutions:**
```typescript
// Configure reconnection strategy
websocketService.setReconnectStrategy({
  maxAttempts: 10,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2
});

// Handle token refresh on reconnect
websocketService.onReconnectAttempt(async () => {
  const newToken = await refreshAuthToken();
  websocketService.updateToken(newToken);
});
```

#### Issue 5: Event Handler Not Firing

**Symptoms:**
- Event handlers registered but never called
- Some handlers work, others don't
- Handler called multiple times

**Solutions:**
```typescript
// Check event type matching
const registeredTypes = websocketService.getRegisteredEventTypes();
console.log('Registered event types:', registeredTypes);

// Avoid duplicate handlers
const handleDnsEvent = useCallback((data) => {
  console.log('DNS event:', data);
}, []);

useEffect(() => {
  websocketService.on(EventType.DNS_RECORD_CHANGED, handleDnsEvent);
  
  return () => {
    websocketService.off(EventType.DNS_RECORD_CHANGED, handleDnsEvent);
  };
}, [handleDnsEvent]);
```

### Debugging Tools

#### WebSocket Inspector

```typescript
// Add to development environment
if (process.env.NODE_ENV === 'development') {
  websocketService.enableDebugMode();
  
  // Log all WebSocket messages
  websocketService.onMessage((message) => {
    console.log('WS Message:', message);
  });
  
  // Log connection state changes
  websocketService.onStateChange((state) => {
    console.log('WS State:', state);
  });
}
```

#### Event Monitoring

```typescript
// Monitor event flow
const EventMonitor = () => {
  const [events, setEvents] = useState([]);
  
  useEffect(() => {
    const handleAnyEvent = (eventType, data) => {
      setEvents(prev => [...prev.slice(-99), {
        type: eventType,
        data,
        timestamp: new Date().toISOString()
      }]);
    };
    
    // Monitor all event types
    Object.values(EventType).forEach(eventType => {
      websocketService.on(eventType, (data) => handleAnyEvent(eventType, data));
    });
    
    return () => {
      Object.values(EventType).forEach(eventType => {
        websocketService.off(eventType);
      });
    };
  }, []);
  
  return (
    <div>
      <h3>Event Monitor</h3>
      {events.map((event, index) => (
        <div key={index}>
          <strong>{event.type}</strong> - {event.timestamp}
          <pre>{JSON.stringify(event.data, null, 2)}</pre>
        </div>
      ))}
    </div>
  );
};
```

## Performance Optimization

### Connection Management

```typescript
// Optimize connection lifecycle
class OptimizedWebSocketService extends UnifiedWebSocketService {
  private connectionPool: Map<string, WebSocket> = new Map();
  private messageQueue: Array<{message: any, priority: number}> = [];
  
  async connect(token: string) {
    // Reuse existing connection if available
    const existingConnection = this.connectionPool.get(token);
    if (existingConnection && existingConnection.readyState === WebSocket.OPEN) {
      return existingConnection;
    }
    
    return super.connect(token);
  }
  
  send(message: any, priority: number = 0) {
    // Queue messages by priority
    this.messageQueue.push({ message, priority });
    this.messageQueue.sort((a, b) => b.priority - a.priority);
    
    this.processMessageQueue();
  }
  
  private processMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const { message } = this.messageQueue.shift()!;
      super.send(message);
    }
  }
}
```

### Event Batching

```typescript
// Batch similar events
class EventBatcher {
  private batches: Map<EventType, any[]> = new Map();
  private batchTimeout: Map<EventType, NodeJS.Timeout> = new Map();
  
  addEvent(eventType: EventType, data: any) {
    if (!this.batches.has(eventType)) {
      this.batches.set(eventType, []);
    }
    
    this.batches.get(eventType)!.push(data);
    
    // Clear existing timeout
    const existingTimeout = this.batchTimeout.get(eventType);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }
    
    // Set new timeout
    const timeout = setTimeout(() => {
      this.processBatch(eventType);
    }, 100); // 100ms batch window
    
    this.batchTimeout.set(eventType, timeout);
  }
  
  private processBatch(eventType: EventType) {
    const batch = this.batches.get(eventType);
    if (batch && batch.length > 0) {
      // Process batched events
      this.handleBatchedEvents(eventType, batch);
      
      // Clear batch
      this.batches.set(eventType, []);
      this.batchTimeout.delete(eventType);
    }
  }
  
  private handleBatchedEvents(eventType: EventType, events: any[]) {
    // Emit single batched event instead of multiple individual events
    websocketService.emit(`${eventType}_BATCH`, events);
  }
}
```

## Best Practices

### 1. Connection Management
- Always use the singleton WebSocket service instance
- Implement proper cleanup in useEffect hooks
- Handle authentication token refresh gracefully
- Monitor connection health and implement reconnection logic

### 2. Event Handling
- Use specific event types instead of generic handlers
- Implement proper error boundaries for event handlers
- Avoid heavy processing in event handlers
- Use event batching for high-frequency events

### 3. Performance
- Limit the number of active subscriptions
- Implement client-side event filtering when possible
- Use React.memo and useMemo for expensive computations
- Monitor memory usage and implement cleanup

### 4. Security
- Always validate event data before processing
- Implement proper authentication and authorization
- Use secure WebSocket connections (WSS) in production
- Log security-related events for auditing

### 5. Testing
- Write unit tests for WebSocket service methods
- Test reconnection scenarios and error handling
- Use mock WebSocket implementations for testing
- Test with different user roles and permissions

## Migration Checklist

### Pre-Migration
- [ ] Review existing WebSocket usage
- [ ] Identify all event types and handlers
- [ ] Document current authentication patterns
- [ ] Set up development environment
- [ ] Create migration branch

### During Migration
- [ ] Replace WebSocket connections with unified service
- [ ] Update event handling patterns
- [ ] Migrate authentication and authorization
- [ ] Update error handling and reconnection logic
- [ ] Test all WebSocket functionality

### Post-Migration
- [ ] Remove legacy WebSocket code
- [ ] Update documentation and examples
- [ ] Monitor performance and error rates
- [ ] Deploy to production with feature flags
- [ ] Collect user feedback and iterate

### Validation
- [ ] All event types working correctly
- [ ] Authentication and authorization functional
- [ ] Reconnection working as expected
- [ ] No memory leaks detected
- [ ] Performance meets requirements
- [ ] Error handling working properly
- [ ] User experience maintained or improved

## Support and Resources

### Documentation
- [WebSocket API Reference](./websocket-unified-api.md)
- [Event Type Reference](./websocket-event-reference.md)
- [Authentication Guide](./websocket-auth-guide.md)

### Code Examples
- [Complete migration examples](../examples/websocket-migration/)
- [Testing utilities](../examples/websocket-testing/)
- [Performance optimization examples](../examples/websocket-optimization/)

### Getting Help
- Check the troubleshooting section above
- Review existing GitHub issues
- Create detailed bug reports with reproduction steps
- Include WebSocket debug logs when reporting issues

---

*This migration guide is part of the WebSocket system optimization project. For technical details about the implementation, see the [design document](../.kiro/specs/websocket-optimization/design.md).*