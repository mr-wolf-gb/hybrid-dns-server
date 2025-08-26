// Test data for notification filtering
export const sampleNotifications = [
  {
    id: '1',
    type: 'health_update',
    severity: 'info',
    data: { message: 'Forwarder health check completed' },
    timestamp: new Date().toISOString(),
    acknowledged: false
  },
  {
    id: '2',
    type: 'zone_created',
    severity: 'info',
    data: { name: 'example.com' },
    timestamp: new Date().toISOString(),
    acknowledged: false
  },
  {
    id: '3',
    type: 'security_alert',
    severity: 'warning',
    data: { message: 'Suspicious DNS query detected' },
    timestamp: new Date().toISOString(),
    acknowledged: false
  },
  {
    id: '4',
    type: 'bind_reload',
    severity: 'info',
    data: { message: 'Configuration reloaded successfully' },
    timestamp: new Date().toISOString(),
    acknowledged: false
  },
  {
    id: '5',
    type: 'forwarder_status_change',
    severity: 'error',
    data: { 
      forwarder_id: 'fw-1',
      old_status: 'healthy',
      new_status: 'unhealthy'
    },
    timestamp: new Date().toISOString(),
    acknowledged: false
  },
  {
    id: '6',
    type: 'threat_detected',
    severity: 'critical',
    data: { 
      threat_type: 'malware',
      details: 'Malicious domain blocked'
    },
    timestamp: new Date().toISOString(),
    acknowledged: false
  }
]

export default sampleNotifications