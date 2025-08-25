# WebSocket Event Type Reference

## Overview

This document provides a comprehensive reference for all event types available in the Unified WebSocket API, including detailed data structures, examples, and usage patterns.

## Event Categories

### DNS Management Events

#### zone_created
Emitted when a new DNS zone is created.

**Event Data:**
```typescript
interface ZoneCreatedEvent {
  zone_id: string
  zone_name: string
  zone_type: 'master' | 'slave' | 'forward'
  serial: number
  refresh: number
  retry: number
  expire: number
  minimum: number
  created_by: string
  created_at: string
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "zone_created",
  "data": {
    "zone_id": "zone_123",
    "zone_name": "example.com",
    "zone_type": "master",
    "serial": 2024011501,
    "refresh": 3600,
    "retry": 1800,
    "expire": 604800,
    "minimum": 86400,
    "created_by": "admin",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "priority": "normal"
}
```

#### zone_updated
Emitted when a DNS zone is modified.

**Event Data:**
```typescript
interface ZoneUpdatedEvent {
  zone_id: string
  zone_name: string
  changes: Array<{
    field: string
    old_value: any
    new_value: any
  }>
  updated_by: string
  updated_at: string
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "zone_updated",
  "data": {
    "zone_id": "zone_123",
    "zone_name": "example.com",
    "changes": [
      {
        "field": "refresh",
        "old_value": 3600,
        "new_value": 7200
      },
      {
        "field": "serial",
        "old_value": 2024011501,
        "new_value": 2024011502
      }
    ],
    "updated_by": "admin",
    "updated_at": "2024-01-15T11:00:00Z"
  },
  "timestamp": "2024-01-15T11:00:00Z",
  "priority": "normal"
}
```

#### zone_deleted
Emitted when a DNS zone is deleted.

**Event Data:**
```typescript
interface ZoneDeletedEvent {
  zone_id: string
  zone_name: string
  zone_type: string
  record_count: number
  deleted_by: string
  deleted_at: string
}
```

#### record_created
Emitted when a new DNS record is created.

**Event Data:**
```typescript
interface RecordCreatedEvent {
  record_id: string
  zone_id: string
  zone_name: string
  record_name: string
  record_type: 'A' | 'AAAA' | 'CNAME' | 'MX' | 'TXT' | 'SRV' | 'PTR' | 'NS'
  record_value: string
  ttl: number
  priority?: number  // For MX and SRV records
  weight?: number    // For SRV records
  port?: number      // For SRV records
  created_by: string
  created_at: string
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "record_created",
  "data": {
    "record_id": "rec_456",
    "zone_id": "zone_123",
    "zone_name": "example.com",
    "record_name": "www.example.com",
    "record_type": "A",
    "record_value": "192.168.1.100",
    "ttl": 3600,
    "created_by": "admin",
    "created_at": "2024-01-15T10:35:00Z"
  },
  "timestamp": "2024-01-15T10:35:00Z",
  "priority": "normal"
}
```

#### record_updated
Emitted when a DNS record is modified.

**Event Data:**
```typescript
interface RecordUpdatedEvent {
  record_id: string
  zone_id: string
  zone_name: string
  record_name: string
  record_type: string
  changes: Array<{
    field: string
    old_value: any
    new_value: any
  }>
  updated_by: string
  updated_at: string
}
```

#### record_deleted
Emitted when a DNS record is deleted.

**Event Data:**
```typescript
interface RecordDeletedEvent {
  record_id: string
  zone_id: string
  zone_name: string
  record_name: string
  record_type: string
  record_value: string
  deleted_by: string
  deleted_at: string
}
```

#### bulk_operation_progress
Emitted during bulk DNS operations to show progress.

**Event Data:**
```typescript
interface BulkOperationProgressEvent {
  operation_id: string
  operation_type: 'import' | 'export' | 'delete' | 'update'
  total_items: number
  processed_items: number
  success_count: number
  error_count: number
  current_item?: string
  estimated_completion?: string
  errors?: Array<{
    item: string
    error: string
  }>
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "bulk_operation_progress",
  "data": {
    "operation_id": "bulk_789",
    "operation_type": "import",
    "total_items": 1000,
    "processed_items": 250,
    "success_count": 245,
    "error_count": 5,
    "current_item": "test250.example.com",
    "estimated_completion": "2024-01-15T10:45:00Z",
    "errors": [
      {
        "item": "invalid.example.com",
        "error": "Invalid IP address format"
      }
    ]
  },
  "timestamp": "2024-01-15T10:40:00Z",
  "priority": "normal"
}
```

#### bulk_operation_complete
Emitted when a bulk operation completes.

**Event Data:**
```typescript
interface BulkOperationCompleteEvent {
  operation_id: string
  operation_type: string
  total_items: number
  success_count: number
  error_count: number
  duration_seconds: number
  completed_at: string
  summary: {
    zones_affected?: number
    records_created?: number
    records_updated?: number
    records_deleted?: number
  }
}
```

### Security Events

#### security_alert
Emitted when a security threat or violation is detected.

**Event Data:**
```typescript
interface SecurityAlertEvent {
  alert_id: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  category: 'malware' | 'phishing' | 'suspicious' | 'policy_violation' | 'brute_force'
  title: string
  message: string
  source_ip?: string
  target_domain?: string
  query_type?: string
  threat_indicators: string[]
  recommended_actions: string[]
  details: Record<string, any>
  detected_at: string
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "security_alert",
  "data": {
    "alert_id": "alert_999",
    "severity": "high",
    "category": "malware",
    "title": "Malware Domain Query Detected",
    "message": "Query to known malware domain blocked by RPZ",
    "source_ip": "192.168.1.50",
    "target_domain": "malicious-site.com",
    "query_type": "A",
    "threat_indicators": ["domain_reputation", "threat_feed_match"],
    "recommended_actions": [
      "Investigate source IP",
      "Check for malware on client system",
      "Review network access logs"
    ],
    "details": {
      "rpz_rule": "malware.rpz",
      "threat_feed": "abuse.ch",
      "confidence_score": 0.95
    },
    "detected_at": "2024-01-15T10:45:00Z"
  },
  "timestamp": "2024-01-15T10:45:00Z",
  "priority": "high"
}
```

#### threat_detected
Emitted when threat intelligence identifies a new threat.

**Event Data:**
```typescript
interface ThreatDetectedEvent {
  threat_id: string
  threat_type: 'domain' | 'ip' | 'url' | 'hash'
  threat_value: string
  confidence_score: number
  threat_categories: string[]
  source_feeds: string[]
  first_seen: string
  last_seen: string
  additional_info: Record<string, any>
}
```

#### rpz_updated
Emitted when Response Policy Zone rules are updated.

**Event Data:**
```typescript
interface RPZUpdatedEvent {
  rpz_id: string
  rpz_name: string
  action: 'rules_added' | 'rules_removed' | 'rules_updated' | 'policy_changed'
  affected_rules: number
  total_rules: number
  updated_by: string
  updated_at: string
  changes?: Array<{
    rule: string
    action: 'added' | 'removed' | 'modified'
    old_value?: string
    new_value?: string
  }>
}
```

#### threat_feed_updated
Emitted when threat intelligence feeds are updated.

**Event Data:**
```typescript
interface ThreatFeedUpdatedEvent {
  feed_id: string
  feed_name: string
  feed_source: string
  update_type: 'full' | 'incremental'
  new_threats: number
  removed_threats: number
  total_threats: number
  last_updated: string
  next_update: string
  update_status: 'success' | 'partial' | 'failed'
  errors?: string[]
}
```

### System Health Events

#### health_update
Emitted periodically with system health information.

**Event Data:**
```typescript
interface HealthUpdateEvent {
  component: 'bind9' | 'database' | 'system' | 'forwarders' | 'overall'
  status: 'healthy' | 'warning' | 'critical' | 'unknown'
  metrics: {
    cpu_usage?: number
    memory_usage?: number
    disk_usage?: number
    response_time?: number
    error_rate?: number
    uptime?: number
  }
  checks: Array<{
    name: string
    status: 'pass' | 'warn' | 'fail'
    message?: string
    value?: any
    threshold?: any
  }>
  timestamp: string
}
```

**Example:**
```json
{
  "type": "event",
  "event_type": "health_update",
  "data": {
    "component": "system",
    "status": "healthy",
    "metrics": {
      "cpu_usage": 25.5,
      "memory_usage": 68.2,
      "disk_usage": 45.8,
      "uptime": 86400
    },
    "checks": [
      {
        "name": "cpu_usage",
        "status": "pass",
        "value": 25.5,
        "threshold": 80
      },
      {
        "name": "memory_usage",
        "status": "warn",
        "message": "Memory usage approaching threshold",
        "value": 68.2,
        "threshold": 70
      }
    ],
    "timestamp": "2024-01-15T10:50:00Z"
  },
  "timestamp": "2024-01-15T10:50:00Z",
  "priority": "normal"
}
```

#### health_alert
Emitted when health thresholds are exceeded.

**Event Data:**
```typescript
interface HealthAlertEvent {
  alert_id: string
  component: string
  severity: 'warning' | 'critical'
  metric: string
  current_value: number
  threshold_value: number
  message: string
  recommended_actions: string[]
  alert_time: string
}
```

#### forwarder_status_change
Emitted when DNS forwarder status changes.

**Event Data:**
```typescript
interface ForwarderStatusChangeEvent {
  forwarder_id: string
  forwarder_name: string
  forwarder_ip: string
  old_status: 'healthy' | 'degraded' | 'failed' | 'unknown'
  new_status: 'healthy' | 'degraded' | 'failed' | 'unknown'
  response_time?: number
  error_message?: string
  last_check: string
  consecutive_failures?: number
}
```

#### system_metrics
Emitted with detailed system performance metrics.

**Event Data:**
```typescript
interface SystemMetricsEvent {
  metrics: {
    cpu: {
      usage_percent: number
      load_average: [number, number, number]  // 1min, 5min, 15min
      cores: number
    }
    memory: {
      total_bytes: number
      used_bytes: number
      available_bytes: number
      usage_percent: number
      swap_total?: number
      swap_used?: number
    }
    disk: {
      total_bytes: number
      used_bytes: number
      available_bytes: number
      usage_percent: number
      iops?: number
    }
    network: {
      bytes_sent: number
      bytes_received: number
      packets_sent: number
      packets_received: number
      errors: number
    }
    dns: {
      queries_per_second: number
      active_zones: number
      total_records: number
      cache_hit_rate?: number
      recursive_queries?: number
    }
  }
  collection_time: string
}
```

### System Configuration Events

#### bind_reload
Emitted when BIND9 configuration is reloaded.

**Event Data:**
```typescript
interface BindReloadEvent {
  reload_id: string
  reload_type: 'full' | 'zones' | 'configuration'
  success: boolean
  duration_ms: number
  zones_reloaded?: number
  errors?: string[]
  triggered_by: string
  reload_time: string
}
```

#### config_change
Emitted when system configuration changes.

**Event Data:**
```typescript
interface ConfigChangeEvent {
  config_id: string
  config_section: 'forwarders' | 'zones' | 'security' | 'system' | 'users'
  change_type: 'created' | 'updated' | 'deleted'
  changes: Array<{
    setting: string
    old_value?: any
    new_value?: any
  }>
  changed_by: string
  change_time: string
  requires_restart?: boolean
}
```

### User Authentication Events

#### user_login
Emitted when a user successfully logs in.

**Event Data:**
```typescript
interface UserLoginEvent {
  user_id: string
  username: string
  login_method: 'password' | '2fa' | 'token'
  source_ip: string
  user_agent: string
  session_id: string
  login_time: string
}
```

#### user_logout
Emitted when a user logs out.

**Event Data:**
```typescript
interface UserLogoutEvent {
  user_id: string
  username: string
  session_id: string
  logout_type: 'manual' | 'timeout' | 'forced'
  session_duration: number
  logout_time: string
}
```

#### session_expired
Emitted when a user session expires.

**Event Data:**
```typescript
interface SessionExpiredEvent {
  user_id: string
  username: string
  session_id: string
  expiry_reason: 'timeout' | 'token_expired' | 'security_policy'
  last_activity: string
  expired_at: string
}
```

#### permission_changed
Emitted when user permissions are modified.

**Event Data:**
```typescript
interface PermissionChangedEvent {
  user_id: string
  username: string
  changed_by: string
  permission_changes: Array<{
    permission: string
    action: 'granted' | 'revoked'
    resource?: string
  }>
  change_time: string
}
```

## Event Filtering and Permissions

### Admin Users
Admin users can subscribe to all event types and receive full event data.

### Regular Users
Regular users have restricted access:

- **DNS Events**: Only for zones they have access to
- **Security Events**: General alerts only (no sensitive details)
- **Health Events**: System-wide health status only
- **User Events**: Only their own authentication events

### Data Filtering Examples

**Admin receives full security alert:**
```json
{
  "event_type": "security_alert",
  "data": {
    "alert_id": "alert_999",
    "severity": "high",
    "source_ip": "192.168.1.50",
    "target_domain": "malicious-site.com",
    "details": {
      "rpz_rule": "malware.rpz",
      "threat_feed": "abuse.ch"
    }
  }
}
```

**Regular user receives filtered security alert:**
```json
{
  "event_type": "security_alert",
  "data": {
    "alert_id": "alert_999",
    "severity": "high",
    "message": "Security threat detected and blocked",
    "category": "malware"
  }
}
```

## Subscription Patterns

### Subscribe to All DNS Events
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    event_types: [
      'zone_created', 'zone_updated', 'zone_deleted',
      'record_created', 'record_updated', 'record_deleted',
      'bulk_operation_progress', 'bulk_operation_complete'
    ]
  }
}))
```

### Subscribe to Security Events Only
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    event_types: [
      'security_alert', 'threat_detected', 
      'rpz_updated', 'threat_feed_updated'
    ]
  }
}))
```

### Subscribe to Health Monitoring
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    event_types: [
      'health_update', 'health_alert',
      'forwarder_status_change', 'system_metrics'
    ]
  }
}))
```

## Event Handler Examples

### React Component with Event Handling
```typescript
import { useUnifiedWebSocket } from '@/hooks/useUnifiedWebSocket'

const DNSManagement = () => {
  const { subscribe, on } = useUnifiedWebSocket()
  
  useEffect(() => {
    // Subscribe to DNS events
    subscribe(['zone_created', 'zone_updated', 'record_created'])
    
    // Handle zone creation
    on('zone_created', (data: ZoneCreatedEvent) => {
      toast.success(`Zone ${data.zone_name} created successfully`)
      // Refresh zone list
      refetchZones()
    })
    
    // Handle record creation
    on('record_created', (data: RecordCreatedEvent) => {
      toast.info(`Record ${data.record_name} added to ${data.zone_name}`)
      // Update specific zone records
      updateZoneRecords(data.zone_id)
    })
    
    // Handle bulk operations
    on('bulk_operation_progress', (data: BulkOperationProgressEvent) => {
      const progress = (data.processed_items / data.total_items) * 100
      setImportProgress(progress)
    })
    
  }, [subscribe, on])
  
  return <div>DNS Management Interface</div>
}
```

### Security Dashboard Event Handling
```typescript
const SecurityDashboard = () => {
  const [alerts, setAlerts] = useState<SecurityAlertEvent[]>([])
  const { subscribe, on } = useUnifiedWebSocket()
  
  useEffect(() => {
    subscribe(['security_alert', 'threat_detected'])
    
    on('security_alert', (data: SecurityAlertEvent) => {
      setAlerts(prev => [data, ...prev])
      
      // Show critical alerts immediately
      if (data.severity === 'critical') {
        showCriticalAlert(data)
      }
    })
    
    on('threat_detected', (data: ThreatDetectedEvent) => {
      if (data.confidence_score > 0.8) {
        toast.warning(`High confidence threat detected: ${data.threat_value}`)
      }
    })
    
  }, [subscribe, on])
  
  return (
    <div>
      <h2>Security Alerts</h2>
      {alerts.map(alert => (
        <AlertCard key={alert.alert_id} alert={alert} />
      ))}
    </div>
  )
}
```

This comprehensive event reference provides all the information needed to effectively use the Unified WebSocket API for real-time communication in the Hybrid DNS Server.