# Forwarder Health Checking

This document describes the comprehensive health checking functionality implemented for DNS forwarders in the Hybrid DNS Server.

## Overview

The health checking system continuously monitors the availability and performance of DNS forwarders to ensure reliable DNS resolution. It provides real-time status updates, historical data, and automated alerting capabilities.

## Features

### 1. Automatic Health Monitoring
- **Continuous Monitoring**: Background service performs health checks at configurable intervals (default: 5 minutes)
- **Per-Server Checking**: Each server in a forwarder configuration is monitored individually
- **DNS Query Testing**: Performs actual DNS queries to verify server responsiveness
- **Response Time Tracking**: Measures and records DNS query response times

### 2. Health Status Classification
- **Healthy**: All servers responding normally
- **Degraded**: Some servers responding, others failing
- **Unhealthy**: No servers responding
- **Unknown**: No health check data available or health checking disabled

### 3. Comprehensive API Endpoints

#### Forwarder-Specific Endpoints
- `GET /api/forwarders/{id}/health` - Get current health status
- `GET /api/forwarders/{id}/health/history` - Get health check history
- `POST /api/forwarders/{id}/health/check` - Trigger manual health check
- `POST /api/forwarders/{id}/health/toggle` - Enable/disable health checking
- `POST /api/forwarders/{id}/test` - Test connectivity with custom domains

#### System-Wide Health Endpoints
- `GET /api/health/summary` - Overall health summary for all forwarders
- `GET /api/health/unhealthy` - List of currently unhealthy forwarders
- `POST /api/health/check/all` - Trigger health checks for all forwarders
- `GET /api/health/service/status` - Health monitoring service status

### 4. Health Check Data Storage
- **ForwarderHealth Model**: Stores individual health check results
- **Historical Data**: Maintains health check history with configurable retention
- **Automatic Cleanup**: Removes old health records to prevent database bloat

## Configuration

### Environment Variables
```bash
# Health check interval (seconds)
HEALTH_CHECK_INTERVAL=300

# DNS query timeout (seconds)
DNS_QUERY_TIMEOUT=5

# Health check timeout (seconds)
HEALTH_CHECK_TIMEOUT=10

# Cleanup interval (seconds)
CLEANUP_INTERVAL=3600

# Health record retention (days)
HEALTH_RECORD_RETENTION_DAYS=30
```

### Forwarder Configuration
```json
{
  "name": "Active Directory DNS",
  "domains": ["corp.example.com", "ad.example.com"],
  "forwarder_type": "active_directory",
  "servers": [
    {"ip": "192.168.1.10", "port": 53, "priority": 1},
    {"ip": "192.168.1.11", "port": 53, "priority": 2}
  ],
  "health_check_enabled": true,
  "description": "Corporate AD DNS servers"
}
```

## Health Check Process

### 1. DNS Query Testing
For each server in a forwarder:
1. Create DNS resolver with server as nameserver
2. Perform DNS query for test domain (uses forwarder's first domain or 'google.com')
3. Measure response time
4. Record result (healthy/unhealthy/timeout/error)

### 2. Status Determination
- **Individual Server**: Based on DNS query success/failure
- **Overall Forwarder**: Calculated from all server statuses
  - All servers healthy → Healthy
  - No servers healthy → Unhealthy  
  - Mixed results → Degraded

### 3. Data Storage
- Store individual server results in `forwarder_health` table
- Include timestamp, response time, error messages
- Maintain foreign key relationship to forwarder

## API Response Examples

### Health Status Response
```json
{
  "overall_status": "degraded",
  "healthy_servers": 1,
  "total_servers": 2,
  "last_checked": "2024-08-19T07:48:32.157980Z",
  "server_statuses": {
    "192.168.1.10": {
      "status": "healthy",
      "response_time": 45,
      "error_message": null,
      "checked_at": "2024-08-19T07:48:32.157980Z"
    },
    "192.168.1.11": {
      "status": "timeout",
      "response_time": null,
      "error_message": "DNS query timeout after 5 seconds",
      "checked_at": "2024-08-19T07:48:32.157980Z"
    }
  }
}
```

### Health Summary Response
```json
{
  "total_forwarders": 5,
  "active_forwarders": 4,
  "health_check_enabled": 3,
  "healthy_forwarders": 2,
  "unhealthy_forwarders": 0,
  "degraded_forwarders": 1,
  "unknown_forwarders": 2,
  "last_updated": "2024-08-19T07:48:52.632919Z",
  "forwarder_details": [...]
}
```

## Background Services

### Health Service
- **Purpose**: Manages health monitoring lifecycle
- **Functions**: 
  - Continuous health checking
  - Health data aggregation
  - Service status management

### Background Task Service
- **Purpose**: Coordinates all background operations
- **Functions**:
  - Health service management
  - Periodic cleanup tasks
  - Service lifecycle management

## Database Schema

### ForwarderHealth Table
```sql
CREATE TABLE forwarder_health (
    id INTEGER PRIMARY KEY,
    forwarder_id INTEGER NOT NULL,
    server_ip VARCHAR(45) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time INTEGER,
    error_message TEXT,
    checked_at DATETIME NOT NULL,
    FOREIGN KEY (forwarder_id) REFERENCES forwarders(id) ON DELETE CASCADE
);
```

### Indexes for Performance
- `idx_forwarder_health_forwarder_status` - Query by forwarder and status
- `idx_forwarder_health_checked_at` - Query by timestamp
- `idx_forwarder_health_server_status` - Query by server and status

## Error Handling

### DNS Query Errors
- **Timeout**: Server not responding within timeout period
- **NXDOMAIN**: Domain doesn't exist (considered healthy response)
- **NoAnswer**: No answer for query type (considered healthy response)
- **Network Error**: Connection or network issues
- **Invalid IP**: Malformed server IP address

### Service Errors
- **Database Errors**: Graceful handling with logging
- **Configuration Errors**: Validation and user feedback
- **Service Failures**: Automatic restart and recovery

## Monitoring and Alerting

### Health Status Monitoring
- Real-time status updates via WebSocket (planned)
- Historical trend analysis
- Performance metrics tracking

### Alert Conditions
- Forwarder becomes unhealthy
- All servers in forwarder fail
- Health check service stops
- Database connectivity issues

## Testing

### Manual Testing
```bash
# Run health check test
python backend/test_health_check.py
```

### API Testing
```bash
# Test health endpoints
curl -X GET "http://localhost:8000/api/health/summary"
curl -X POST "http://localhost:8000/api/forwarders/1/health/check"
```

## Performance Considerations

### Optimization Strategies
- **Concurrent Checks**: Multiple servers checked in parallel
- **Timeout Management**: Configurable timeouts prevent hanging
- **Database Indexing**: Optimized queries for health data
- **Data Retention**: Automatic cleanup of old records

### Scalability
- **Horizontal Scaling**: Health checks can be distributed
- **Resource Management**: Configurable check intervals
- **Memory Efficiency**: Streaming health data processing

## Troubleshooting

### Common Issues
1. **Health checks timing out**: Check network connectivity and DNS server availability
2. **Service not starting**: Verify database connectivity and configuration
3. **High resource usage**: Adjust check intervals and cleanup settings
4. **Missing health data**: Ensure health checking is enabled for forwarders

### Debug Commands
```bash
# Check service status
curl -X GET "http://localhost:8000/api/health/service/status"

# View health logs
tail -f /var/log/hybrid-dns/health.log

# Manual health check
curl -X POST "http://localhost:8000/api/health/check/all"
```

## Future Enhancements

### Planned Features
- **Real-time Notifications**: WebSocket-based status updates
- **Advanced Metrics**: Latency percentiles, availability SLAs
- **Custom Health Checks**: User-defined health check scripts
- **Integration Alerts**: Email, Slack, webhook notifications
- **Health Dashboards**: Graphical health status visualization