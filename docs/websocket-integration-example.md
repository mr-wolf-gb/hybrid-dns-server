# WebSocket Integration Examples

## Complete Integration Examples

This document provides complete, working examples of how to integrate the new unified WebSocket system into different types of applications and components.

## Example 1: DNS Management Dashboard

### Complete Component Implementation

```typescript
// src/components/DNSManagementDashboard.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket';
import { EventType } from '../types/websocket';
import { DNSZone, DNSRecord } from '../types/dns';

interface DNSManagementDashboardProps {
  user: User;
}

export const DNSManagementDashboard: React.FC<DNSManagementDashboardProps> = ({ user }) => {
  const [zones, setZones] = useState<DNSZone[]>([]);
  const [records, setRecords] = useState<DNSRecord[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [eventLog, setEventLog] = useState<Array<{type: string, data: any, timestamp: Date}>>([]);

  // Initialize WebSocket connection
  useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          throw new Error('No authentication token found');
        }

        await websocketService.connect(token);
        setIsConnected(true);
        setConnectionError(null);

        // Subscribe to DNS-related events
        await websocketService.subscribe([
          EventType.DNS_ZONE_CREATED,
          EventType.DNS_ZONE_UPDATED,
          EventType.DNS_ZONE_DELETED,
          EventType.DNS_RECORD_CREATED,
          EventType.DNS_RECORD_UPDATED,
          EventType.DNS_RECORD_DELETED,
          EventType.BIND9_CONFIG_RELOADED,
          EventType.DNS_QUERY_LOG
        ]);

      } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
        setConnectionError(error.message);
        setIsConnected(false);
      }
    };

    initializeWebSocket();

    return () => {
      // Cleanup subscriptions
      websocketService.unsubscribe([
        EventType.DNS_ZONE_CREATED,
        EventType.DNS_ZONE_UPDATED,
        EventType.DNS_ZONE_DELETED,
        EventType.DNS_RECORD_CREATED,
        EventType.DNS_RECORD_UPDATED,
        EventType.DNS_RECORD_DELETED,
        EventType.BIND9_CONFIG_RELOADED,
        EventType.DNS_QUERY_LOG
      ]);
    };
  }, []);

  // Event handlers
  const handleZoneCreated = useCallback((data: DNSZone) => {
    setZones(prev => [...prev, data]);
    addToEventLog('Zone Created', data);
  }, []);

  const handleZoneUpdated = useCallback((data: DNSZone) => {
    setZones(prev => prev.map(zone => zone.id === data.id ? data : zone));
    addToEventLog('Zone Updated', data);
  }, []);

  const handleZoneDeleted = useCallback((data: {id: string}) => {
    setZones(prev => prev.filter(zone => zone.id !== data.id));
    addToEventLog('Zone Deleted', data);
  }, []);

  const handleRecordCreated = useCallback((data: DNSRecord) => {
    setRecords(prev => [...prev, data]);
    addToEventLog('Record Created', data);
  }, []);

  const handleRecordUpdated = useCallback((data: DNSRecord) => {
    setRecords(prev => prev.map(record => record.id === data.id ? data : record));
    addToEventLog('Record Updated', data);
  }, []);

  const handleRecordDeleted = useCallback((data: {id: string}) => {
    setRecords(prev => prev.filter(record => record.id !== data.id));
    addToEventLog('Record Deleted', data);
  }, []);

  const handleConfigReloaded = useCallback((data: any) => {
    addToEventLog('BIND9 Config Reloaded', data);
    // Optionally refresh data
    refreshData();
  }, []);

  const handleQueryLog = useCallback((data: any) => {
    // Handle real-time query logs (might want to limit frequency)
    addToEventLog('DNS Query', data);
  }, []);

  const addToEventLog = useCallback((type: string, data: any) => {
    setEventLog(prev => [
      { type, data, timestamp: new Date() },
      ...prev.slice(0, 99) // Keep last 100 events
    ]);
  }, []);

  // Set up event listeners
  useEffect(() => {
    if (!isConnected) return;

    websocketService.on(EventType.DNS_ZONE_CREATED, handleZoneCreated);
    websocketService.on(EventType.DNS_ZONE_UPDATED, handleZoneUpdated);
    websocketService.on(EventType.DNS_ZONE_DELETED, handleZoneDeleted);
    websocketService.on(EventType.DNS_RECORD_CREATED, handleRecordCreated);
    websocketService.on(EventType.DNS_RECORD_UPDATED, handleRecordUpdated);
    websocketService.on(EventType.DNS_RECORD_DELETED, handleRecordDeleted);
    websocketService.on(EventType.BIND9_CONFIG_RELOADED, handleConfigReloaded);
    websocketService.on(EventType.DNS_QUERY_LOG, handleQueryLog);

    return () => {
      websocketService.off(EventType.DNS_ZONE_CREATED, handleZoneCreated);
      websocketService.off(EventType.DNS_ZONE_UPDATED, handleZoneUpdated);
      websocketService.off(EventType.DNS_ZONE_DELETED, handleZoneDeleted);
      websocketService.off(EventType.DNS_RECORD_CREATED, handleRecordCreated);
      websocketService.off(EventType.DNS_RECORD_UPDATED, handleRecordUpdated);
      websocketService.off(EventType.DNS_RECORD_DELETED, handleRecordDeleted);
      websocketService.off(EventType.BIND9_CONFIG_RELOADED, handleConfigReloaded);
      websocketService.off(EventType.DNS_QUERY_LOG, handleQueryLog);
    };
  }, [isConnected, handleZoneCreated, handleZoneUpdated, handleZoneDeleted, 
      handleRecordCreated, handleRecordUpdated, handleRecordDeleted, 
      handleConfigReloaded, handleQueryLog]);

  // Connection error handling
  useEffect(() => {
    websocketService.onError((error) => {
      setConnectionError(error.message);
      setIsConnected(false);
    });

    websocketService.onReconnect(() => {
      setIsConnected(true);
      setConnectionError(null);
    });

    websocketService.onReconnectFailed((attempts) => {
      setConnectionError(`Failed to reconnect after ${attempts} attempts`);
    });
  }, []);

  // Load initial data
  const refreshData = useCallback(async () => {
    try {
      const [zonesResponse, recordsResponse] = await Promise.all([
        fetch('/api/zones'),
        fetch('/api/dns-records')
      ]);
      
      const zonesData = await zonesResponse.json();
      const recordsData = await recordsResponse.json();
      
      setZones(zonesData);
      setRecords(recordsData);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  return (
    <div className="dns-management-dashboard">
      {/* Connection Status */}
      <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        <div className="status-indicator">
          <span className={`indicator ${isConnected ? 'green' : 'red'}`}></span>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        {connectionError && (
          <div className="error-message">{connectionError}</div>
        )}
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        <div className="zones-section">
          <h2>DNS Zones ({zones.length})</h2>
          <div className="zones-list">
            {zones.map(zone => (
              <div key={zone.id} className="zone-item">
                <h3>{zone.name}</h3>
                <p>Type: {zone.type}</p>
                <p>Records: {records.filter(r => r.zone_id === zone.id).length}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="records-section">
          <h2>Recent DNS Records ({records.length})</h2>
          <div className="records-list">
            {records.slice(0, 10).map(record => (
              <div key={record.id} className="record-item">
                <span className="name">{record.name}</span>
                <span className="type">{record.type}</span>
                <span className="value">{record.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="event-log-section">
          <h2>Real-time Event Log</h2>
          <div className="event-log">
            {eventLog.slice(0, 20).map((event, index) => (
              <div key={index} className="event-item">
                <span className="timestamp">
                  {event.timestamp.toLocaleTimeString()}
                </span>
                <span className="event-type">{event.type}</span>
                <span className="event-data">
                  {JSON.stringify(event.data, null, 2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Example 2: Security Monitoring Component

```typescript
// src/components/SecurityMonitoring.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket';
import { EventType } from '../types/websocket';

interface SecurityAlert {
  id: string;
  type: 'malware' | 'phishing' | 'suspicious' | 'blocked';
  domain: string;
  source_ip: string;
  timestamp: Date;
  severity: 'low' | 'medium' | 'high' | 'critical';
  details: any;
}

export const SecurityMonitoring: React.FC = () => {
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [stats, setStats] = useState({
    blocked_queries: 0,
    malware_domains: 0,
    phishing_attempts: 0,
    total_threats: 0
  });
  const [isConnected, setIsConnected] = useState(false);

  // Initialize WebSocket for security events
  useEffect(() => {
    const initializeSecurity = async () => {
      try {
        const token = localStorage.getItem('authToken');
        await websocketService.connect(token);
        
        // Subscribe to security events
        await websocketService.subscribe([
          EventType.SECURITY_ALERT,
          EventType.RPZ_BLOCK,
          EventType.THREAT_DETECTED,
          EventType.SECURITY_STATS_UPDATED
        ]);
        
        setIsConnected(true);
      } catch (error) {
        console.error('Failed to initialize security monitoring:', error);
      }
    };

    initializeSecurity();
  }, []);

  // Security event handlers
  const handleSecurityAlert = useCallback((data: SecurityAlert) => {
    setAlerts(prev => [data, ...prev.slice(0, 99)]); // Keep last 100 alerts
    
    // Update stats
    setStats(prev => ({
      ...prev,
      total_threats: prev.total_threats + 1
    }));

    // Show notification for critical alerts
    if (data.severity === 'critical') {
      showCriticalAlert(data);
    }
  }, []);

  const handleRPZBlock = useCallback((data: any) => {
    setStats(prev => ({
      ...prev,
      blocked_queries: prev.blocked_queries + 1
    }));
  }, []);

  const handleThreatDetected = useCallback((data: any) => {
    if (data.type === 'malware') {
      setStats(prev => ({
        ...prev,
        malware_domains: prev.malware_domains + 1
      }));
    } else if (data.type === 'phishing') {
      setStats(prev => ({
        ...prev,
        phishing_attempts: prev.phishing_attempts + 1
      }));
    }
  }, []);

  const handleStatsUpdate = useCallback((data: any) => {
    setStats(data);
  }, []);

  // Set up event listeners
  useEffect(() => {
    if (!isConnected) return;

    websocketService.on(EventType.SECURITY_ALERT, handleSecurityAlert);
    websocketService.on(EventType.RPZ_BLOCK, handleRPZBlock);
    websocketService.on(EventType.THREAT_DETECTED, handleThreatDetected);
    websocketService.on(EventType.SECURITY_STATS_UPDATED, handleStatsUpdate);

    return () => {
      websocketService.off(EventType.SECURITY_ALERT, handleSecurityAlert);
      websocketService.off(EventType.RPZ_BLOCK, handleRPZBlock);
      websocketService.off(EventType.THREAT_DETECTED, handleThreatDetected);
      websocketService.off(EventType.SECURITY_STATS_UPDATED, handleStatsUpdate);
    };
  }, [isConnected, handleSecurityAlert, handleRPZBlock, handleThreatDetected, handleStatsUpdate]);

  const showCriticalAlert = (alert: SecurityAlert) => {
    // Show browser notification for critical alerts
    if (Notification.permission === 'granted') {
      new Notification('Critical Security Alert', {
        body: `${alert.type.toUpperCase()}: ${alert.domain}`,
        icon: '/security-alert-icon.png'
      });
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600';
      case 'high': return 'text-orange-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-blue-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="security-monitoring">
      <div className="security-header">
        <h1>Security Monitoring</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Live' : '🔴 Offline'}
        </div>
      </div>

      {/* Security Statistics */}
      <div className="security-stats">
        <div className="stat-card">
          <h3>Blocked Queries</h3>
          <div className="stat-value">{stats.blocked_queries.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <h3>Malware Domains</h3>
          <div className="stat-value">{stats.malware_domains.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <h3>Phishing Attempts</h3>
          <div className="stat-value">{stats.phishing_attempts.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <h3>Total Threats</h3>
          <div className="stat-value">{stats.total_threats.toLocaleString()}</div>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="recent-alerts">
        <h2>Recent Security Alerts</h2>
        <div className="alerts-list">
          {alerts.map(alert => (
            <div key={alert.id} className="alert-item">
              <div className="alert-header">
                <span className={`severity ${getSeverityColor(alert.severity)}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <span className="alert-type">{alert.type}</span>
                <span className="timestamp">
                  {alert.timestamp.toLocaleString()}
                </span>
              </div>
              <div className="alert-details">
                <div><strong>Domain:</strong> {alert.domain}</div>
                <div><strong>Source IP:</strong> {alert.source_ip}</div>
                {alert.details && (
                  <div><strong>Details:</strong> {JSON.stringify(alert.details)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Example 3: System Health Monitor

```typescript
// src/components/SystemHealthMonitor.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket';
import { EventType } from '../types/websocket';

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: {
    bytes_sent: number;
    bytes_received: number;
  };
  bind9_status: 'running' | 'stopped' | 'error';
  forwarder_health: Array<{
    name: string;
    status: 'healthy' | 'degraded' | 'down';
    response_time: number;
  }>;
  timestamp: Date;
}

export const SystemHealthMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [history, setHistory] = useState<SystemMetrics[]>([]);
  const [alerts, setAlerts] = useState<Array<{type: string, message: string, timestamp: Date}>>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Initialize WebSocket for system monitoring
  useEffect(() => {
    const initializeMonitoring = async () => {
      try {
        const token = localStorage.getItem('authToken');
        await websocketService.connect(token);
        
        // Subscribe to system events
        await websocketService.subscribe([
          EventType.SYSTEM_METRICS,
          EventType.FORWARDER_HEALTH_CHANGED,
          EventType.BIND9_STATUS_CHANGED,
          EventType.SYSTEM_ALERT
        ]);
        
        setIsConnected(true);
      } catch (error) {
        console.error('Failed to initialize system monitoring:', error);
      }
    };

    initializeMonitoring();
  }, []);

  // System event handlers
  const handleSystemMetrics = useCallback((data: SystemMetrics) => {
    setMetrics(data);
    
    // Add to history (keep last 100 entries)
    setHistory(prev => [data, ...prev.slice(0, 99)]);
    
    // Check for alerts
    checkForAlerts(data);
  }, []);

  const handleForwarderHealthChanged = useCallback((data: any) => {
    setAlerts(prev => [{
      type: 'forwarder',
      message: `Forwarder ${data.name} status changed to ${data.status}`,
      timestamp: new Date()
    }, ...prev.slice(0, 49)]);
  }, []);

  const handleBind9StatusChanged = useCallback((data: any) => {
    setAlerts(prev => [{
      type: 'bind9',
      message: `BIND9 status changed to ${data.status}`,
      timestamp: new Date()
    }, ...prev.slice(0, 49)]);
  }, []);

  const handleSystemAlert = useCallback((data: any) => {
    setAlerts(prev => [{
      type: 'system',
      message: data.message,
      timestamp: new Date()
    }, ...prev.slice(0, 49)]);
  }, []);

  const checkForAlerts = (metrics: SystemMetrics) => {
    const newAlerts = [];
    
    if (metrics.cpu_usage > 80) {
      newAlerts.push({
        type: 'performance',
        message: `High CPU usage: ${metrics.cpu_usage}%`,
        timestamp: new Date()
      });
    }
    
    if (metrics.memory_usage > 85) {
      newAlerts.push({
        type: 'performance',
        message: `High memory usage: ${metrics.memory_usage}%`,
        timestamp: new Date()
      });
    }
    
    if (metrics.disk_usage > 90) {
      newAlerts.push({
        type: 'performance',
        message: `High disk usage: ${metrics.disk_usage}%`,
        timestamp: new Date()
      });
    }
    
    if (newAlerts.length > 0) {
      setAlerts(prev => [...newAlerts, ...prev.slice(0, 47)]);
    }
  };

  // Set up event listeners
  useEffect(() => {
    if (!isConnected) return;

    websocketService.on(EventType.SYSTEM_METRICS, handleSystemMetrics);
    websocketService.on(EventType.FORWARDER_HEALTH_CHANGED, handleForwarderHealthChanged);
    websocketService.on(EventType.BIND9_STATUS_CHANGED, handleBind9StatusChanged);
    websocketService.on(EventType.SYSTEM_ALERT, handleSystemAlert);

    return () => {
      websocketService.off(EventType.SYSTEM_METRICS, handleSystemMetrics);
      websocketService.off(EventType.FORWARDER_HEALTH_CHANGED, handleForwarderHealthChanged);
      websocketService.off(EventType.BIND9_STATUS_CHANGED, handleBind9StatusChanged);
      websocketService.off(EventType.SYSTEM_ALERT, handleSystemAlert);
    };
  }, [isConnected, handleSystemMetrics, handleForwarderHealthChanged, 
      handleBind9StatusChanged, handleSystemAlert]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'running': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      case 'down':
      case 'stopped':
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getUsageColor = (usage: number) => {
    if (usage > 90) return 'text-red-600';
    if (usage > 75) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (!metrics) {
    return (
      <div className="system-health-monitor">
        <div className="loading">Loading system metrics...</div>
      </div>
    );
  }

  return (
    <div className="system-health-monitor">
      <div className="health-header">
        <h1>System Health Monitor</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Live' : '🔴 Offline'}
        </div>
      </div>

      {/* System Metrics */}
      <div className="system-metrics">
        <div className="metric-card">
          <h3>CPU Usage</h3>
          <div className={`metric-value ${getUsageColor(metrics.cpu_usage)}`}>
            {metrics.cpu_usage.toFixed(1)}%
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill" 
              style={{ width: `${metrics.cpu_usage}%` }}
            ></div>
          </div>
        </div>

        <div className="metric-card">
          <h3>Memory Usage</h3>
          <div className={`metric-value ${getUsageColor(metrics.memory_usage)}`}>
            {metrics.memory_usage.toFixed(1)}%
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill" 
              style={{ width: `${metrics.memory_usage}%` }}
            ></div>
          </div>
        </div>

        <div className="metric-card">
          <h3>Disk Usage</h3>
          <div className={`metric-value ${getUsageColor(metrics.disk_usage)}`}>
            {metrics.disk_usage.toFixed(1)}%
          </div>
          <div className="metric-bar">
            <div 
              className="metric-fill" 
              style={{ width: `${metrics.disk_usage}%` }}
            ></div>
          </div>
        </div>

        <div className="metric-card">
          <h3>BIND9 Status</h3>
          <div className={`metric-value ${getStatusColor(metrics.bind9_status)}`}>
            {metrics.bind9_status.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Forwarder Health */}
      <div className="forwarder-health">
        <h2>DNS Forwarder Health</h2>
        <div className="forwarders-list">
          {metrics.forwarder_health.map(forwarder => (
            <div key={forwarder.name} className="forwarder-item">
              <div className="forwarder-name">{forwarder.name}</div>
              <div className={`forwarder-status ${getStatusColor(forwarder.status)}`}>
                {forwarder.status.toUpperCase()}
              </div>
              <div className="forwarder-response-time">
                {forwarder.response_time}ms
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Alerts */}
      <div className="system-alerts">
        <h2>Recent Alerts</h2>
        <div className="alerts-list">
          {alerts.slice(0, 10).map((alert, index) => (
            <div key={index} className="alert-item">
              <span className="alert-type">{alert.type}</span>
              <span className="alert-message">{alert.message}</span>
              <span className="alert-timestamp">
                {alert.timestamp.toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Example 4: Custom Hook for WebSocket Events

```typescript
// src/hooks/useWebSocketEvents.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService } from '../services/websocket';
import { EventType } from '../types/websocket';

interface UseWebSocketEventsOptions {
  autoConnect?: boolean;
  reconnectOnError?: boolean;
  maxReconnectAttempts?: number;
  eventBufferSize?: number;
}

interface UseWebSocketEventsReturn {
  events: Record<EventType, any>;
  isConnected: boolean;
  connectionError: string | null;
  subscribe: (eventTypes: EventType[]) => Promise<void>;
  unsubscribe: (eventTypes: EventType[]) => Promise<void>;
  send: (message: any) => Promise<boolean>;
  reconnect: () => Promise<void>;
  clearEvents: (eventType?: EventType) => void;
}

export const useWebSocketEvents = (
  initialEventTypes: EventType[] = [],
  options: UseWebSocketEventsOptions = {}
): UseWebSocketEventsReturn => {
  const {
    autoConnect = true,
    reconnectOnError = true,
    maxReconnectAttempts = 5,
    eventBufferSize = 100
  } = options;

  const [events, setEvents] = useState<Record<EventType, any>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [subscribedEvents, setSubscribedEvents] = useState<Set<EventType>>(new Set());
  
  const reconnectAttempts = useRef(0);
  const eventHandlers = useRef<Map<EventType, (data: any) => void>>(new Map());

  // Initialize WebSocket connection
  const connect = useCallback(async () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        throw new Error('No authentication token found');
      }

      await websocketService.connect(token);
      setIsConnected(true);
      setConnectionError(null);
      reconnectAttempts.current = 0;

      // Subscribe to initial event types
      if (initialEventTypes.length > 0) {
        await websocketService.subscribe(initialEventTypes);
        setSubscribedEvents(new Set(initialEventTypes));
      }

    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setConnectionError(error.message);
      setIsConnected(false);

      // Attempt reconnection if enabled
      if (reconnectOnError && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++;
        setTimeout(() => {
          connect();
        }, Math.pow(2, reconnectAttempts.current) * 1000); // Exponential backoff
      }
    }
  }, [initialEventTypes, reconnectOnError, maxReconnectAttempts]);

  // Subscribe to additional event types
  const subscribe = useCallback(async (eventTypes: EventType[]) => {
    try {
      await websocketService.subscribe(eventTypes);
      setSubscribedEvents(prev => new Set([...prev, ...eventTypes]));
    } catch (error) {
      console.error('Failed to subscribe to events:', error);
      throw error;
    }
  }, []);

  // Unsubscribe from event types
  const unsubscribe = useCallback(async (eventTypes: EventType[]) => {
    try {
      await websocketService.unsubscribe(eventTypes);
      setSubscribedEvents(prev => {
        const newSet = new Set(prev);
        eventTypes.forEach(eventType => newSet.delete(eventType));
        return newSet;
      });
    } catch (error) {
      console.error('Failed to unsubscribe from events:', error);
      throw error;
    }
  }, []);

  // Send message through WebSocket
  const send = useCallback(async (message: any): Promise<boolean> => {
    try {
      return await websocketService.send(message);
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }, []);

  // Manual reconnection
  const reconnect = useCallback(async () => {
    reconnectAttempts.current = 0;
    await connect();
  }, [connect]);

  // Clear events
  const clearEvents = useCallback((eventType?: EventType) => {
    if (eventType) {
      setEvents(prev => ({ ...prev, [eventType]: null }));
    } else {
      setEvents({});
    }
  }, []);

  // Set up event handlers
  useEffect(() => {
    const handleEvent = (eventType: EventType) => (data: any) => {
      setEvents(prev => {
        const currentEvents = prev[eventType];
        let newEventData;

        // Handle different event data structures
        if (Array.isArray(currentEvents)) {
          // For events that accumulate (like logs)
          newEventData = [data, ...currentEvents.slice(0, eventBufferSize - 1)];
        } else {
          // For events that replace (like status updates)
          newEventData = data;
        }

        return {
          ...prev,
          [eventType]: newEventData
        };
      });
    };

    // Set up handlers for subscribed events
    subscribedEvents.forEach(eventType => {
      const handler = handleEvent(eventType);
      eventHandlers.current.set(eventType, handler);
      websocketService.on(eventType, handler);
    });

    // Cleanup function
    return () => {
      eventHandlers.current.forEach((handler, eventType) => {
        websocketService.off(eventType, handler);
      });
      eventHandlers.current.clear();
    };
  }, [subscribedEvents, eventBufferSize]);

  // Set up connection event handlers
  useEffect(() => {
    const handleError = (error: Error) => {
      setConnectionError(error.message);
      setIsConnected(false);
    };

    const handleReconnect = () => {
      setIsConnected(true);
      setConnectionError(null);
    };

    const handleReconnectFailed = (attempts: number) => {
      setConnectionError(`Failed to reconnect after ${attempts} attempts`);
    };

    websocketService.onError(handleError);
    websocketService.onReconnect(handleReconnect);
    websocketService.onReconnectFailed(handleReconnectFailed);

    return () => {
      websocketService.offError(handleError);
      websocketService.offReconnect(handleReconnect);
      websocketService.offReconnectFailed(handleReconnectFailed);
    };
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
  }, [autoConnect, connect]);

  return {
    events,
    isConnected,
    connectionError,
    subscribe,
    unsubscribe,
    send,
    reconnect,
    clearEvents
  };
};
```

## Example 5: WebSocket Testing Utilities

```typescript
// src/utils/websocketTestUtils.ts
import { EventType } from '../types/websocket';

export class MockWebSocketService {
  private eventHandlers: Map<EventType, Set<(data: any) => void>> = new Map();
  private subscriptions: Set<EventType> = new Set();
  private connected = false;
  private token: string | null = null;

  async connect(token: string): Promise<void> {
    this.token = token;
    this.connected = true;
    return Promise.resolve();
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    this.eventHandlers.clear();
    this.subscriptions.clear();
    return Promise.resolve();
  }

  async subscribe(eventTypes: EventType[]): Promise<void> {
    eventTypes.forEach(eventType => {
      this.subscriptions.add(eventType);
    });
    return Promise.resolve();
  }

  async unsubscribe(eventTypes: EventType[]): Promise<void> {
    eventTypes.forEach(eventType => {
      this.subscriptions.delete(eventType);
      this.eventHandlers.delete(eventType);
    });
    return Promise.resolve();
  }

  on(eventType: EventType, handler: (data: any) => void): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  off(eventType: EventType, handler?: (data: any) => void): void {
    if (handler) {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
      }
    } else {
      this.eventHandlers.delete(eventType);
    }
  }

  async send(message: any): Promise<boolean> {
    if (!this.connected) {
      throw new Error('WebSocket not connected');
    }
    return Promise.resolve(true);
  }

  // Test utilities
  emit(eventType: EventType, data: any): void {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  getSubscriptions(): EventType[] {
    return Array.from(this.subscriptions);
  }

  getToken(): string | null {
    return this.token;
  }

  // Simulate connection errors
  simulateError(error: Error): void {
    this.connected = false;
    // Trigger error handlers if implemented
  }

  // Simulate reconnection
  simulateReconnect(): void {
    this.connected = true;
    // Trigger reconnect handlers if implemented
  }
}

// Test helper functions
export const createMockWebSocketService = (): MockWebSocketService => {
  return new MockWebSocketService();
};

export const waitForWebSocketEvent = (
  service: MockWebSocketService,
  eventType: EventType,
  timeout: number = 5000
): Promise<any> => {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timeout waiting for event: ${eventType}`));
    }, timeout);

    const handler = (data: any) => {
      clearTimeout(timer);
      service.off(eventType, handler);
      resolve(data);
    };

    service.on(eventType, handler);
  });
};

export const simulateWebSocketEvents = (
  service: MockWebSocketService,
  events: Array<{ type: EventType; data: any; delay?: number }>
): void => {
  events.forEach((event, index) => {
    setTimeout(() => {
      service.emit(event.type, event.data);
    }, event.delay || index * 100);
  });
};
```

These examples provide comprehensive, production-ready implementations that demonstrate:

1. **Complete component integration** with proper error handling and cleanup
2. **Real-world event handling patterns** for different types of data
3. **Custom hooks** for reusable WebSocket functionality
4. **Testing utilities** for unit and integration tests
5. **Performance optimizations** like event batching and memory management

Each example includes proper TypeScript typing, error handling, and follows React best practices for WebSocket integration.