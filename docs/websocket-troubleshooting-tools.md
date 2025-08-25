# WebSocket Troubleshooting Tools and Utilities

## Debugging Tools

### WebSocket Debug Console

```typescript
// src/utils/websocketDebugger.ts
export class WebSocketDebugger {
  private logs: Array<{
    timestamp: Date;
    type: 'connection' | 'message' | 'error' | 'subscription';
    direction: 'in' | 'out';
    data: any;
  }> = [];
  
  private maxLogs = 1000;
  private enabled = false;

  constructor(enabled: boolean = false) {
    this.enabled = enabled;
  }

  enable(): void {
    this.enabled = true;
    console.log('WebSocket debugging enabled');
  }

  disable(): void {
    this.enabled = false;
    console.log('WebSocket debugging disabled');
  }

  logConnection(event: string, data?: any): void {
    if (!this.enabled) return;
    
    this.addLog({
      timestamp: new Date(),
      type: 'connection',
      direction: 'out',
      data: { event, ...data }
    });
    
    console.log(`[WS Connection] ${event}`, data);
  }

  logMessage(direction: 'in' | 'out', message: any): void {
    if (!this.enabled) return;
    
    this.addLog({
      timestamp: new Date(),
      type: 'message',
      direction,
      data: message
    });
    
    console.log(`[WS ${direction.toUpperCase()}]`, message);
  }

  logError(error: Error, context?: string): void {
    if (!this.enabled) return;
    
    this.addLog({
      timestamp: new Date(),
      type: 'error',
      direction: 'in',
      data: { error: error.message, context }
    });
    
    console.error(`[WS Error] ${context || ''}`, error);
  }

  logSubscription(action: 'subscribe' | 'unsubscribe', eventTypes: string[]): void {
    if (!this.enabled) return;
    
    this.addLog({
      timestamp: new Date(),
      type: 'subscription',
      direction: 'out',
      data: { action, eventTypes }
    });
    
    console.log(`[WS Subscription] ${action}`, eventTypes);
  }

  private addLog(log: any): void {
    this.logs.push(log);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }

  getLogs(): any[] {
    return [...this.logs];
  }

  getLogsSince(timestamp: Date): any[] {
    return this.logs.filter(log => log.timestamp >= timestamp);
  }

  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  clearLogs(): void {
    this.logs = [];
    console.log('WebSocket logs cleared');
  }

  getStats(): {
    totalLogs: number;
    connectionEvents: number;
    messagesIn: number;
    messagesOut: number;
    errors: number;
    subscriptionEvents: number;
  } {
    return {
      totalLogs: this.logs.length,
      connectionEvents: this.logs.filter(log => log.type === 'connection').length,
      messagesIn: this.logs.filter(log => log.type === 'message' && log.direction === 'in').length,
      messagesOut: this.logs.filter(log => log.type === 'message' && log.direction === 'out').length,
      errors: this.logs.filter(log => log.type === 'error').length,
      subscriptionEvents: this.logs.filter(log => log.type === 'subscription').length
    };
  }
}

// Global debugger instance
export const wsDebugger = new WebSocketDebugger(
  process.env.NODE_ENV === 'development'
);
```

### Connection Health Monitor

```typescript
// src/utils/connectionHealthMonitor.ts
export class ConnectionHealthMonitor {
  private healthChecks: Array<{
    timestamp: Date;
    latency: number;
    success: boolean;
    error?: string;
  }> = [];
  
  private intervalId: NodeJS.Timeout | null = null;
  private websocketService: any;
  private checkInterval = 30000; // 30 seconds
  private maxHealthChecks = 100;

  constructor(websocketService: any) {
    this.websocketService = websocketService;
  }

  start(): void {
    if (this.intervalId) {
      this.stop();
    }

    this.intervalId = setInterval(() => {
      this.performHealthCheck();
    }, this.checkInterval);

    console.log('Connection health monitoring started');
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    console.log('Connection health monitoring stopped');
  }

  private async performHealthCheck(): Promise<void> {
    const startTime = Date.now();
    
    try {
      // Send ping message
      const success = await this.websocketService.send({
        type: 'ping',
        timestamp: startTime
      });

      const latency = Date.now() - startTime;

      this.addHealthCheck({
        timestamp: new Date(),
        latency,
        success
      });

    } catch (error) {
      this.addHealthCheck({
        timestamp: new Date(),
        latency: -1,
        success: false,
        error: error.message
      });
    }
  }

  private addHealthCheck(check: any): void {
    this.healthChecks.push(check);
    if (this.healthChecks.length > this.maxHealthChecks) {
      this.healthChecks.shift();
    }
  }

  getHealthStats(): {
    averageLatency: number;
    successRate: number;
    lastCheck: Date | null;
    recentFailures: number;
  } {
    if (this.healthChecks.length === 0) {
      return {
        averageLatency: 0,
        successRate: 0,
        lastCheck: null,
        recentFailures: 0
      };
    }

    const successfulChecks = this.healthChecks.filter(check => check.success);
    const recentChecks = this.healthChecks.slice(-10); // Last 10 checks
    const recentFailures = recentChecks.filter(check => !check.success).length;

    return {
      averageLatency: successfulChecks.length > 0 
        ? successfulChecks.reduce((sum, check) => sum + check.latency, 0) / successfulChecks.length
        : 0,
      successRate: (successfulChecks.length / this.healthChecks.length) * 100,
      lastCheck: this.healthChecks[this.healthChecks.length - 1]?.timestamp || null,
      recentFailures
    };
  }

  getHealthHistory(): any[] {
    return [...this.healthChecks];
  }

  isHealthy(): boolean {
    const stats = this.getHealthStats();
    return stats.successRate > 80 && stats.recentFailures < 3;
  }
}
```

### Event Flow Analyzer

```typescript
// src/utils/eventFlowAnalyzer.ts
export class EventFlowAnalyzer {
  private eventFlow: Array<{
    eventType: string;
    timestamp: Date;
    processingTime: number;
    handlerCount: number;
    dataSize: number;
  }> = [];
  
  private maxEvents = 1000;
  private websocketService: any;

  constructor(websocketService: any) {
    this.websocketService = websocketService;
    this.setupEventInterception();
  }

  private setupEventInterception(): void {
    // Intercept event handling to measure performance
    const originalOn = this.websocketService.on.bind(this.websocketService);
    const originalEmit = this.websocketService.emit?.bind(this.websocketService);

    this.websocketService.on = (eventType: string, handler: Function) => {
      const wrappedHandler = (data: any) => {
        const startTime = Date.now();
        
        try {
          handler(data);
          
          const processingTime = Date.now() - startTime;
          this.recordEvent(eventType, processingTime, data);
          
        } catch (error) {
          console.error(`Error in event handler for ${eventType}:`, error);
          this.recordEvent(eventType, Date.now() - startTime, data, error);
        }
      };

      return originalOn(eventType, wrappedHandler);
    };

    if (originalEmit) {
      this.websocketService.emit = (eventType: string, data: any) => {
        const result = originalEmit(eventType, data);
        this.recordEventEmission(eventType, data);
        return result;
      };
    }
  }

  private recordEvent(eventType: string, processingTime: number, data: any, error?: Error): void {
    this.eventFlow.push({
      eventType,
      timestamp: new Date(),
      processingTime,
      handlerCount: this.getHandlerCount(eventType),
      dataSize: this.calculateDataSize(data)
    });

    if (this.eventFlow.length > this.maxEvents) {
      this.eventFlow.shift();
    }

    // Log slow events
    if (processingTime > 100) {
      console.warn(`Slow event processing: ${eventType} took ${processingTime}ms`);
    }

    if (error) {
      console.error(`Event processing error: ${eventType}`, error);
    }
  }

  private recordEventEmission(eventType: string, data: any): void {
    // Record when events are emitted (for testing/debugging)
    console.log(`Event emitted: ${eventType}`, data);
  }

  private getHandlerCount(eventType: string): number {
    // This would need to be implemented based on your WebSocket service structure
    return 1; // Placeholder
  }

  private calculateDataSize(data: any): number {
    try {
      return JSON.stringify(data).length;
    } catch {
      return 0;
    }
  }

  getEventStats(): {
    totalEvents: number;
    averageProcessingTime: number;
    slowestEvent: { eventType: string; processingTime: number } | null;
    mostFrequentEvent: { eventType: string; count: number } | null;
    eventTypeDistribution: Record<string, number>;
  } {
    if (this.eventFlow.length === 0) {
      return {
        totalEvents: 0,
        averageProcessingTime: 0,
        slowestEvent: null,
        mostFrequentEvent: null,
        eventTypeDistribution: {}
      };
    }

    const totalProcessingTime = this.eventFlow.reduce((sum, event) => sum + event.processingTime, 0);
    const slowestEvent = this.eventFlow.reduce((slowest, event) => 
      event.processingTime > (slowest?.processingTime || 0) ? event : slowest
    );

    const eventCounts: Record<string, number> = {};
    this.eventFlow.forEach(event => {
      eventCounts[event.eventType] = (eventCounts[event.eventType] || 0) + 1;
    });

    const mostFrequentEventType = Object.keys(eventCounts).reduce((a, b) => 
      eventCounts[a] > eventCounts[b] ? a : b
    );

    return {
      totalEvents: this.eventFlow.length,
      averageProcessingTime: totalProcessingTime / this.eventFlow.length,
      slowestEvent: slowestEvent ? {
        eventType: slowestEvent.eventType,
        processingTime: slowestEvent.processingTime
      } : null,
      mostFrequentEvent: {
        eventType: mostFrequentEventType,
        count: eventCounts[mostFrequentEventType]
      },
      eventTypeDistribution: eventCounts
    };
  }

  getRecentEvents(minutes: number = 5): any[] {
    const cutoff = new Date(Date.now() - minutes * 60 * 1000);
    return this.eventFlow.filter(event => event.timestamp >= cutoff);
  }

  exportEventFlow(): string {
    return JSON.stringify(this.eventFlow, null, 2);
  }

  clearEventFlow(): void {
    this.eventFlow = [];
  }
}
```

### Memory Leak Detector

```typescript
// src/utils/memoryLeakDetector.ts
export class MemoryLeakDetector {
  private snapshots: Array<{
    timestamp: Date;
    heapUsed: number;
    heapTotal: number;
    external: number;
    connectionCount: number;
    eventHandlerCount: number;
  }> = [];
  
  private intervalId: NodeJS.Timeout | null = null;
  private websocketService: any;
  private snapshotInterval = 60000; // 1 minute
  private maxSnapshots = 100;

  constructor(websocketService: any) {
    this.websocketService = websocketService;
  }

  start(): void {
    if (this.intervalId) {
      this.stop();
    }

    this.intervalId = setInterval(() => {
      this.takeSnapshot();
    }, this.snapshotInterval);

    console.log('Memory leak detection started');
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    console.log('Memory leak detection stopped');
  }

  private takeSnapshot(): void {
    // Note: performance.memory is only available in Chrome
    const memoryInfo = (performance as any).memory;
    
    if (!memoryInfo) {
      console.warn('Memory information not available in this browser');
      return;
    }

    const snapshot = {
      timestamp: new Date(),
      heapUsed: memoryInfo.usedJSHeapSize,
      heapTotal: memoryInfo.totalJSHeapSize,
      external: memoryInfo.usedJSHeapSize, // Approximation
      connectionCount: this.getConnectionCount(),
      eventHandlerCount: this.getEventHandlerCount()
    };

    this.snapshots.push(snapshot);
    
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots.shift();
    }

    // Check for potential memory leaks
    this.checkForLeaks(snapshot);
  }

  private getConnectionCount(): number {
    // This would need to be implemented based on your WebSocket service
    return this.websocketService.getConnectionCount?.() || 0;
  }

  private getEventHandlerCount(): number {
    // This would need to be implemented based on your WebSocket service
    return this.websocketService.getEventHandlerCount?.() || 0;
  }

  private checkForLeaks(currentSnapshot: any): void {
    if (this.snapshots.length < 10) return; // Need enough data

    const recentSnapshots = this.snapshots.slice(-10);
    const oldestRecent = recentSnapshots[0];
    
    // Check for consistent memory growth
    const memoryGrowth = currentSnapshot.heapUsed - oldestRecent.heapUsed;
    const timeSpan = currentSnapshot.timestamp.getTime() - oldestRecent.timestamp.getTime();
    const growthRate = memoryGrowth / (timeSpan / 1000); // bytes per second

    if (growthRate > 1000) { // More than 1KB/second growth
      console.warn(`Potential memory leak detected: ${(growthRate / 1024).toFixed(2)} KB/s growth`);
    }

    // Check for handler accumulation
    const handlerGrowth = currentSnapshot.eventHandlerCount - oldestRecent.eventHandlerCount;
    if (handlerGrowth > 10) {
      console.warn(`Event handler accumulation detected: ${handlerGrowth} new handlers`);
    }
  }

  getMemoryStats(): {
    currentHeapUsed: number;
    currentHeapTotal: number;
    averageGrowthRate: number;
    peakMemoryUsage: number;
    potentialLeaks: string[];
  } {
    if (this.snapshots.length === 0) {
      return {
        currentHeapUsed: 0,
        currentHeapTotal: 0,
        averageGrowthRate: 0,
        peakMemoryUsage: 0,
        potentialLeaks: []
      };
    }

    const latest = this.snapshots[this.snapshots.length - 1];
    const oldest = this.snapshots[0];
    const timeSpan = latest.timestamp.getTime() - oldest.timestamp.getTime();
    const memoryGrowth = latest.heapUsed - oldest.heapUsed;
    const averageGrowthRate = timeSpan > 0 ? memoryGrowth / (timeSpan / 1000) : 0;

    const peakMemoryUsage = Math.max(...this.snapshots.map(s => s.heapUsed));

    const potentialLeaks: string[] = [];
    if (averageGrowthRate > 500) {
      potentialLeaks.push('Consistent memory growth detected');
    }
    if (latest.eventHandlerCount > 100) {
      potentialLeaks.push('High number of event handlers');
    }

    return {
      currentHeapUsed: latest.heapUsed,
      currentHeapTotal: latest.heapTotal,
      averageGrowthRate,
      peakMemoryUsage,
      potentialLeaks
    };
  }

  exportSnapshots(): string {
    return JSON.stringify(this.snapshots, null, 2);
  }

  clearSnapshots(): void {
    this.snapshots = [];
  }
}
```

## Diagnostic Components

### WebSocket Debug Panel

```typescript
// src/components/WebSocketDebugPanel.tsx
import React, { useState, useEffect } from 'react';
import { wsDebugger } from '../utils/websocketDebugger';
import { ConnectionHealthMonitor } from '../utils/connectionHealthMonitor';
import { EventFlowAnalyzer } from '../utils/eventFlowAnalyzer';
import { MemoryLeakDetector } from '../utils/memoryLeakDetector';
import { websocketService } from '../services/websocket';

export const WebSocketDebugPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('logs');
  const [logs, setLogs] = useState<any[]>([]);
  const [healthStats, setHealthStats] = useState<any>({});
  const [eventStats, setEventStats] = useState<any>({});
  const [memoryStats, setMemoryStats] = useState<any>({});

  const healthMonitor = new ConnectionHealthMonitor(websocketService);
  const eventAnalyzer = new EventFlowAnalyzer(websocketService);
  const memoryDetector = new MemoryLeakDetector(websocketService);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;

    // Start monitoring
    healthMonitor.start();
    eventAnalyzer.start?.();
    memoryDetector.start();

    // Update stats periodically
    const interval = setInterval(() => {
      setLogs(wsDebugger.getLogs());
      setHealthStats(healthMonitor.getHealthStats());
      setEventStats(eventAnalyzer.getEventStats());
      setMemoryStats(memoryDetector.getMemoryStats());
    }, 1000);

    return () => {
      clearInterval(interval);
      healthMonitor.stop();
      memoryDetector.stop();
    };
  }, []);

  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="websocket-debug-panel">
      <button
        className="debug-toggle"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 9999,
          padding: '10px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '5px'
        }}
      >
        🔧 WebSocket Debug
      </button>

      {isOpen && (
        <div
          className="debug-panel"
          style={{
            position: 'fixed',
            bottom: '70px',
            right: '20px',
            width: '600px',
            height: '400px',
            backgroundColor: 'white',
            border: '1px solid #ccc',
            borderRadius: '5px',
            zIndex: 9998,
            overflow: 'hidden',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }}
        >
          <div className="debug-header" style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
            <div className="debug-tabs">
              {['logs', 'health', 'events', 'memory'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    marginRight: '10px',
                    padding: '5px 10px',
                    backgroundColor: activeTab === tab ? '#007bff' : '#f8f9fa',
                    color: activeTab === tab ? 'white' : 'black',
                    border: '1px solid #ccc',
                    borderRadius: '3px'
                  }}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="debug-content" style={{ padding: '10px', height: '320px', overflow: 'auto' }}>
            {activeTab === 'logs' && (
              <div className="logs-tab">
                <div className="logs-controls" style={{ marginBottom: '10px' }}>
                  <button onClick={() => wsDebugger.clearLogs()}>Clear Logs</button>
                  <button onClick={() => wsDebugger.enable()}>Enable</button>
                  <button onClick={() => wsDebugger.disable()}>Disable</button>
                </div>
                <div className="logs-list">
                  {logs.slice(-50).map((log, index) => (
                    <div key={index} style={{ 
                      fontSize: '12px', 
                      marginBottom: '5px',
                      padding: '5px',
                      backgroundColor: log.type === 'error' ? '#ffe6e6' : '#f8f9fa'
                    }}>
                      <span style={{ fontWeight: 'bold' }}>
                        {log.timestamp.toLocaleTimeString()}
                      </span>
                      <span style={{ marginLeft: '10px', color: '#666' }}>
                        [{log.type}] {log.direction}
                      </span>
                      <pre style={{ margin: '5px 0', fontSize: '11px' }}>
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'health' && (
              <div className="health-tab">
                <div className="health-stats">
                  <div>Average Latency: {healthStats.averageLatency?.toFixed(2)}ms</div>
                  <div>Success Rate: {healthStats.successRate?.toFixed(1)}%</div>
                  <div>Recent Failures: {healthStats.recentFailures}</div>
                  <div>Last Check: {healthStats.lastCheck?.toLocaleTimeString()}</div>
                  <div style={{ 
                    color: healthMonitor.isHealthy() ? 'green' : 'red',
                    fontWeight: 'bold'
                  }}>
                    Status: {healthMonitor.isHealthy() ? 'Healthy' : 'Unhealthy'}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'events' && (
              <div className="events-tab">
                <div className="event-stats">
                  <div>Total Events: {eventStats.totalEvents}</div>
                  <div>Average Processing Time: {eventStats.averageProcessingTime?.toFixed(2)}ms</div>
                  {eventStats.slowestEvent && (
                    <div>Slowest Event: {eventStats.slowestEvent.eventType} ({eventStats.slowestEvent.processingTime}ms)</div>
                  )}
                  {eventStats.mostFrequentEvent && (
                    <div>Most Frequent: {eventStats.mostFrequentEvent.eventType} ({eventStats.mostFrequentEvent.count})</div>
                  )}
                </div>
                <div className="event-distribution">
                  <h4>Event Distribution:</h4>
                  {Object.entries(eventStats.eventTypeDistribution || {}).map(([eventType, count]) => (
                    <div key={eventType}>
                      {eventType}: {count as number}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'memory' && (
              <div className="memory-tab">
                <div className="memory-stats">
                  <div>Current Heap Used: {(memoryStats.currentHeapUsed / 1024 / 1024).toFixed(2)} MB</div>
                  <div>Current Heap Total: {(memoryStats.currentHeapTotal / 1024 / 1024).toFixed(2)} MB</div>
                  <div>Average Growth Rate: {(memoryStats.averageGrowthRate / 1024).toFixed(2)} KB/s</div>
                  <div>Peak Memory Usage: {(memoryStats.peakMemoryUsage / 1024 / 1024).toFixed(2)} MB</div>
                  {memoryStats.potentialLeaks?.length > 0 && (
                    <div style={{ color: 'red' }}>
                      <h4>Potential Leaks:</h4>
                      {memoryStats.potentialLeaks.map((leak: string, index: number) => (
                        <div key={index}>⚠️ {leak}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
```

## Automated Testing Tools

### WebSocket Integration Test Suite

```typescript
// src/tests/websocketIntegration.test.ts
import { MockWebSocketService, waitForWebSocketEvent, simulateWebSocketEvents } from '../utils/websocketTestUtils';
import { EventType } from '../types/websocket';

describe('WebSocket Integration Tests', () => {
  let mockService: MockWebSocketService;

  beforeEach(() => {
    mockService = new MockWebSocketService();
  });

  afterEach(() => {
    mockService.disconnect();
  });

  describe('Connection Management', () => {
    test('should connect with valid token', async () => {
      await mockService.connect('valid-token');
      expect(mockService.isConnected()).toBe(true);
      expect(mockService.getToken()).toBe('valid-token');
    });

    test('should handle connection failure', async () => {
      const invalidService = new MockWebSocketService();
      // Simulate connection failure
      invalidService.simulateError(new Error('Connection failed'));
      expect(invalidService.isConnected()).toBe(false);
    });

    test('should reconnect after connection loss', async () => {
      await mockService.connect('token');
      expect(mockService.isConnected()).toBe(true);

      // Simulate connection loss
      mockService.simulateError(new Error('Connection lost'));
      expect(mockService.isConnected()).toBe(false);

      // Simulate reconnection
      mockService.simulateReconnect();
      expect(mockService.isConnected()).toBe(true);
    });
  });

  describe('Event Subscription', () => {
    beforeEach(async () => {
      await mockService.connect('token');
    });

    test('should subscribe to events', async () => {
      const eventTypes = [EventType.DNS_RECORD_CHANGED, EventType.SECURITY_ALERT];
      await mockService.subscribe(eventTypes);
      
      const subscriptions = mockService.getSubscriptions();
      expect(subscriptions).toEqual(expect.arrayContaining(eventTypes));
    });

    test('should unsubscribe from events', async () => {
      const eventTypes = [EventType.DNS_RECORD_CHANGED, EventType.SECURITY_ALERT];
      await mockService.subscribe(eventTypes);
      await mockService.unsubscribe([EventType.DNS_RECORD_CHANGED]);
      
      const subscriptions = mockService.getSubscriptions();
      expect(subscriptions).toContain(EventType.SECURITY_ALERT);
      expect(subscriptions).not.toContain(EventType.DNS_RECORD_CHANGED);
    });

    test('should receive subscribed events', async () => {
      await mockService.subscribe([EventType.DNS_RECORD_CHANGED]);
      
      const eventPromise = waitForWebSocketEvent(mockService, EventType.DNS_RECORD_CHANGED);
      
      mockService.emit(EventType.DNS_RECORD_CHANGED, { id: '123', name: 'test.com' });
      
      const eventData = await eventPromise;
      expect(eventData).toEqual({ id: '123', name: 'test.com' });
    });
  });

  describe('Event Flow', () => {
    beforeEach(async () => {
      await mockService.connect('token');
    });

    test('should handle multiple events in sequence', async () => {
      await mockService.subscribe([
        EventType.DNS_RECORD_CHANGED,
        EventType.SECURITY_ALERT,
        EventType.SYSTEM_METRICS
      ]);

      const receivedEvents: any[] = [];
      
      mockService.on(EventType.DNS_RECORD_CHANGED, (data) => {
        receivedEvents.push({ type: 'dns', data });
      });
      
      mockService.on(EventType.SECURITY_ALERT, (data) => {
        receivedEvents.push({ type: 'security', data });
      });
      
      mockService.on(EventType.SYSTEM_METRICS, (data) => {
        receivedEvents.push({ type: 'system', data });
      });

      // Simulate multiple events
      simulateWebSocketEvents(mockService, [
        { type: EventType.DNS_RECORD_CHANGED, data: { id: '1' } },
        { type: EventType.SECURITY_ALERT, data: { severity: 'high' } },
        { type: EventType.SYSTEM_METRICS, data: { cpu: 75 } }
      ]);

      // Wait for events to be processed
      await new Promise(resolve => setTimeout(resolve, 500));

      expect(receivedEvents).toHaveLength(3);
      expect(receivedEvents[0].type).toBe('dns');
      expect(receivedEvents[1].type).toBe('security');
      expect(receivedEvents[2].type).toBe('system');
    });

    test('should handle high-frequency events', async () => {
      await mockService.subscribe([EventType.DNS_QUERY_LOG]);
      
      const receivedEvents: any[] = [];
      mockService.on(EventType.DNS_QUERY_LOG, (data) => {
        receivedEvents.push(data);
      });

      // Simulate 100 rapid events
      const events = Array.from({ length: 100 }, (_, i) => ({
        type: EventType.DNS_QUERY_LOG,
        data: { query: `query-${i}` },
        delay: i * 10 // 10ms apart
      }));

      simulateWebSocketEvents(mockService, events);

      // Wait for all events to be processed
      await new Promise(resolve => setTimeout(resolve, 2000));

      expect(receivedEvents).toHaveLength(100);
    });
  });

  describe('Error Handling', () => {
    test('should handle malformed event data', async () => {
      await mockService.connect('token');
      await mockService.subscribe([EventType.DNS_RECORD_CHANGED]);
      
      let errorCaught = false;
      mockService.on(EventType.DNS_RECORD_CHANGED, (data) => {
        try {
          // This should handle malformed data gracefully
          JSON.parse(data.malformedJson);
        } catch (error) {
          errorCaught = true;
        }
      });

      mockService.emit(EventType.DNS_RECORD_CHANGED, { malformedJson: 'invalid json {' });
      
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(errorCaught).toBe(true);
    });

    test('should handle event handler exceptions', async () => {
      await mockService.connect('token');
      await mockService.subscribe([EventType.DNS_RECORD_CHANGED]);
      
      let handlerExecuted = false;
      mockService.on(EventType.DNS_RECORD_CHANGED, (data) => {
        handlerExecuted = true;
        throw new Error('Handler error');
      });

      // Should not crash the service
      expect(() => {
        mockService.emit(EventType.DNS_RECORD_CHANGED, { id: '123' });
      }).not.toThrow();

      expect(handlerExecuted).toBe(true);
    });
  });

  describe('Performance', () => {
    test('should handle concurrent subscriptions', async () => {
      await mockService.connect('token');
      
      const subscriptionPromises = Array.from({ length: 10 }, (_, i) => 
        mockService.subscribe([EventType.DNS_RECORD_CHANGED])
      );

      await Promise.all(subscriptionPromises);
      
      // Should still be connected and functional
      expect(mockService.isConnected()).toBe(true);
    });

    test('should handle memory cleanup on unsubscribe', async () => {
      await mockService.connect('token');
      
      // Subscribe and unsubscribe multiple times
      for (let i = 0; i < 100; i++) {
        await mockService.subscribe([EventType.DNS_RECORD_CHANGED]);
        await mockService.unsubscribe([EventType.DNS_RECORD_CHANGED]);
      }
      
      // Should not accumulate subscriptions
      const subscriptions = mockService.getSubscriptions();
      expect(subscriptions).toHaveLength(0);
    });
  });
});
```

## Production Monitoring Tools

### WebSocket Metrics Collector

```typescript
// src/utils/websocketMetrics.ts
export class WebSocketMetricsCollector {
  private metrics = {
    connections: {
      total: 0,
      active: 0,
      failed: 0
    },
    messages: {
      sent: 0,
      received: 0,
      failed: 0
    },
    events: {
      processed: 0,
      errors: 0,
      averageProcessingTime: 0
    },
    performance: {
      averageLatency: 0,
      maxLatency: 0,
      minLatency: Infinity
    }
  };

  private startTime = Date.now();

  recordConnection(success: boolean): void {
    this.metrics.connections.total++;
    if (success) {
      this.metrics.connections.active++;
    } else {
      this.metrics.connections.failed++;
    }
  }

  recordDisconnection(): void {
    this.metrics.connections.active = Math.max(0, this.metrics.connections.active - 1);
  }

  recordMessage(direction: 'sent' | 'received', success: boolean = true): void {
    if (success) {
      this.metrics.messages[direction]++;
    } else {
      this.metrics.messages.failed++;
    }
  }

  recordEventProcessing(processingTime: number, success: boolean = true): void {
    if (success) {
      this.metrics.events.processed++;
      
      // Update average processing time
      const totalTime = this.metrics.events.averageProcessingTime * (this.metrics.events.processed - 1);
      this.metrics.events.averageProcessingTime = (totalTime + processingTime) / this.metrics.events.processed;
    } else {
      this.metrics.events.errors++;
    }
  }

  recordLatency(latency: number): void {
    this.metrics.performance.maxLatency = Math.max(this.metrics.performance.maxLatency, latency);
    this.metrics.performance.minLatency = Math.min(this.metrics.performance.minLatency, latency);
    
    // Simple moving average for latency
    this.metrics.performance.averageLatency = 
      (this.metrics.performance.averageLatency * 0.9) + (latency * 0.1);
  }

  getMetrics(): any {
    const uptime = Date.now() - this.startTime;
    
    return {
      ...this.metrics,
      uptime,
      rates: {
        messagesPerSecond: (this.metrics.messages.sent + this.metrics.messages.received) / (uptime / 1000),
        eventsPerSecond: this.metrics.events.processed / (uptime / 1000),
        errorRate: this.metrics.events.errors / Math.max(1, this.metrics.events.processed)
      }
    };
  }

  reset(): void {
    this.metrics = {
      connections: { total: 0, active: 0, failed: 0 },
      messages: { sent: 0, received: 0, failed: 0 },
      events: { processed: 0, errors: 0, averageProcessingTime: 0 },
      performance: { averageLatency: 0, maxLatency: 0, minLatency: Infinity }
    };
    this.startTime = Date.now();
  }

  exportMetrics(): string {
    return JSON.stringify(this.getMetrics(), null, 2);
  }
}

// Global metrics collector
export const wsMetrics = new WebSocketMetricsCollector();
```

These troubleshooting tools provide comprehensive debugging and monitoring capabilities for the WebSocket system, including:

1. **Debug Console** - Real-time logging and message inspection
2. **Health Monitor** - Connection health tracking and latency monitoring
3. **Event Flow Analyzer** - Performance analysis of event processing
4. **Memory Leak Detector** - Memory usage monitoring and leak detection
5. **Debug Panel Component** - Visual debugging interface for development
6. **Integration Test Suite** - Comprehensive automated testing
7. **Metrics Collector** - Production monitoring and performance tracking

These tools help developers identify and resolve issues quickly during development and provide ongoing monitoring capabilities in production.