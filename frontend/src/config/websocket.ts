/**
 * WebSocket Configuration
 * Centralized configuration for WebSocket connections
 */

export const WEBSOCKET_CONFIG = {
  // Connection settings
  RECONNECT_INTERVAL: 5000, // 5 seconds
  MAX_RECONNECT_ATTEMPTS: 5,
  PING_INTERVAL: 30000, // 30 seconds
  CONNECTION_TIMEOUT: 10000, // 10 seconds

  // Event throttling
  NOTIFICATION_THROTTLE_DURATION: 5000, // 5 seconds

  // Connection types
  CONNECTION_TYPES: {
    HEALTH: 'health',
    DNS_MANAGEMENT: 'dns_management',
    SECURITY: 'security',
    SYSTEM: 'system',
    ADMIN: 'admin'
  } as const,

  // Event types
  EVENT_TYPES: {
    // Health monitoring events
    HEALTH_UPDATE: 'health_update',
    HEALTH_ALERT: 'health_alert',
    FORWARDER_STATUS_CHANGE: 'forwarder_status_change',

    // DNS zone events
    ZONE_CREATED: 'zone_created',
    ZONE_UPDATED: 'zone_updated',
    ZONE_DELETED: 'zone_deleted',
    RECORD_CREATED: 'record_created',
    RECORD_UPDATED: 'record_updated',
    RECORD_DELETED: 'record_deleted',

    // Security events
    SECURITY_ALERT: 'security_alert',
    RPZ_UPDATE: 'rpz_update',
    RPZ_RULE_CREATED: 'rpz_rule_created',
    RPZ_RULE_UPDATED: 'rpz_rule_updated',
    RPZ_RULE_DELETED: 'rpz_rule_deleted',
    THREAT_DETECTED: 'threat_detected',
    THREAT_FEED_UPDATED: 'threat_feed_updated',
    THREAT_FEED_ERROR: 'threat_feed_error',

    // System events
    SYSTEM_STATUS: 'system_status',
    BIND_RELOAD: 'bind_reload',
    CONFIG_CHANGE: 'config_change',

    // User events
    USER_LOGIN: 'user_login',
    USER_LOGOUT: 'user_logout',
    SESSION_EXPIRED: 'session_expired',

    // Connection events
    CONNECTION_ESTABLISHED: 'connection_established',
    SUBSCRIPTION_UPDATED: 'subscription_updated'
  } as const,

  // WebSocket URL construction
  getWebSocketUrl: (connectionType: string, token: string): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/api/websocket/ws/${connectionType}?token=${encodeURIComponent(token)}`;
  },

  // Default event subscriptions by connection type
  DEFAULT_SUBSCRIPTIONS: {
    health: [
      'health_update',
      'health_alert',
      'forwarder_status_change',
      'system_status'
    ],
    dns_management: [
      'zone_created',
      'zone_updated',
      'zone_deleted',
      'record_created',
      'record_updated',
      'record_deleted',
      'bind_reload',
      'config_change'
    ],
    security: [
      'security_alert',
      'rpz_update',
      'rpz_rule_created',
      'rpz_rule_updated',
      'rpz_rule_deleted',
      'threat_detected',
      'threat_feed_updated',
      'threat_feed_error',
      'system_status'
    ],
    system: [
      'system_status',
      'bind_reload',
      'config_change',
      'user_login',
      'user_logout'
    ],
    admin: [
      // Admin receives all events
      'health_update',
      'health_alert',
      'forwarder_status_change',
      'zone_created',
      'zone_updated',
      'zone_deleted',
      'record_created',
      'record_updated',
      'record_deleted',
      'security_alert',
      'rpz_update',
      'threat_detected',
      'system_status',
      'bind_reload',
      'config_change',
      'user_login',
      'user_logout',
      'session_expired'
    ]
  }
} as const;

export type ConnectionType = typeof WEBSOCKET_CONFIG.CONNECTION_TYPES[keyof typeof WEBSOCKET_CONFIG.CONNECTION_TYPES];
export type EventType = typeof WEBSOCKET_CONFIG.EVENT_TYPES[keyof typeof WEBSOCKET_CONFIG.EVENT_TYPES];

export default WEBSOCKET_CONFIG;