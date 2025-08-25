/**
 * React hook for WebSocket connections with event broadcasting support
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  event_id?: string;
  category?: string;
  source?: string;
  severity?: string;
  tags?: string[];
  metadata?: any;
}

export interface WebSocketConfig {
  connectionType: 'health' | 'dns_management' | 'security' | 'system' | 'admin';
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
  connectionStats: any;
  reconnectAttempts: number;
}

export interface WebSocketActions {
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
  subscribeToEvents: (eventTypes: string[]) => void;
  emitEvent: (eventData: any) => void;
  getRecentEvents: (limit?: number) => void;
  startReplay: (replayConfig: any) => void;
  stopReplay: (replayId: string) => void;
  getReplayStatus: (replayId: string) => void;
  ping: () => void;
}

// Connection types enum
export enum ConnectionType {
  HEALTH = 'health',
  DNS_MANAGEMENT = 'dns_management',
  SECURITY = 'security',
  SYSTEM = 'system',
  ADMIN = 'admin'
}

// Event types enum
export enum EventType {
  // Health monitoring events
  HEALTH_UPDATE = 'health_update',
  HEALTH_ALERT = 'health_alert',
  FORWARDER_STATUS_CHANGE = 'forwarder_status_change',

  // DNS zone events
  ZONE_CREATED = 'zone_created',
  ZONE_UPDATED = 'zone_updated',
  ZONE_DELETED = 'zone_deleted',
  RECORD_CREATED = 'record_created',
  RECORD_UPDATED = 'record_updated',
  RECORD_DELETED = 'record_deleted',

  // Security events
  SECURITY_ALERT = 'security_alert',
  RPZ_UPDATE = 'rpz_update',
  THREAT_DETECTED = 'threat_detected',

  // System events
  SYSTEM_STATUS = 'system_status',
  BIND_RELOAD = 'bind_reload',
  CONFIG_CHANGE = 'config_change',

  // User events
  USER_LOGIN = 'user_login',
  USER_LOGOUT = 'user_logout',
  SESSION_EXPIRED = 'session_expired',

  // Connection events
  CONNECTION_ESTABLISHED = 'connection_established',
  SUBSCRIPTION_UPDATED = 'subscription_updated'
}

export const useWebSocket = (config: WebSocketConfig): [WebSocketState, WebSocketActions] => {
  const { accessToken } = useAuth();
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    connectionStats: null,
    reconnectAttempts: 0
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const configRef = useRef(config);

  // Update config ref when config changes
  useEffect(() => {
    configRef.current = config;
  }, [config]);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (!accessToken || state.isConnecting || state.isConnected) {
      return;
    }

    // Additional check to ensure token is valid (not empty or expired)
    if (accessToken.trim() === '' || accessToken === 'null' || accessToken === 'undefined') {
      console.warn('Invalid access token, cannot establish WebSocket connection');
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      // Import the connection manager dynamically to avoid circular dependencies
      const { default: webSocketConnectionManager } = await import('../services/WebSocketConnectionManager');
      
      const ws = await webSocketConnectionManager.getConnection(
        config.connectionType,
        'user', // We'll use a generic user ID since we don't have access to actual user ID here
        accessToken,
        // onMessage
        (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            setState(prev => ({ ...prev, lastMessage: message }));
            configRef.current.onMessage?.(message);

            // Handle special message types
            if (message.type === 'connection_stats') {
              setState(prev => ({ ...prev, connectionStats: message.data }));
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        },
        // onConnect
        () => {
          setState(prev => ({
            ...prev,
            isConnected: true,
            isConnecting: false,
            error: null,
            reconnectAttempts: 0
          }));

          // Start ping interval to keep connection alive
          pingIntervalRef.current = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping', data: {} }));
            }
          }, 30000); // Ping every 30 seconds

          configRef.current.onConnect?.();
        },
        // onDisconnect
        () => {
          cleanup();
          setState(prev => ({
            ...prev,
            isConnected: false,
            isConnecting: false
          }));
          configRef.current.onDisconnect?.();
        },
        // onError
        (error) => {
          console.error('WebSocket connection error:', error);
          setState(prev => ({
            ...prev,
            error: 'WebSocket connection error',
            isConnecting: false
          }));
          configRef.current.onError?.(error);
        }
      );

      if (ws) {
        wsRef.current = ws;
      } else {
        setState(prev => ({
          ...prev,
          error: 'Failed to create WebSocket connection - connection manager returned null',
          isConnecting: false
        }));
      }

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: `Failed to create WebSocket connection: ${error}`,
        isConnecting: false
      }));
    }
  }, [accessToken, state.isConnecting, state.isConnected, config.connectionType, cleanup]);

  const disconnect = useCallback(async () => {
    cleanup();
    
    try {
      // Import the connection manager dynamically
      const { default: webSocketConnectionManager } = await import('../services/WebSocketConnectionManager');
      webSocketConnectionManager.disconnect(config.connectionType, 'user');
    } catch (error) {
      console.error('Error disconnecting from WebSocket manager:', error);
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      error: null,
      reconnectAttempts: 0
    }));
  }, [cleanup, config.connectionType]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const subscribeToEvents = useCallback((eventTypes: string[]) => {
    sendMessage({
      type: 'subscribe_events',
      data: { event_types: eventTypes }
    });
  }, [sendMessage]);

  const emitEvent = useCallback((eventData: any) => {
    sendMessage({
      type: 'emit_event',
      data: eventData
    });
  }, [sendMessage]);

  const getRecentEvents = useCallback((limit: number = 50) => {
    sendMessage({
      type: 'get_recent_events',
      data: { limit }
    });
  }, [sendMessage]);

  const startReplay = useCallback((replayConfig: any) => {
    sendMessage({
      type: 'start_replay',
      data: replayConfig
    });
  }, [sendMessage]);

  const stopReplay = useCallback((replayId: string) => {
    sendMessage({
      type: 'stop_replay',
      data: { replay_id: replayId }
    });
  }, [sendMessage]);

  const getReplayStatus = useCallback((replayId: string) => {
    sendMessage({
      type: 'get_replay_status',
      data: { replay_id: replayId }
    });
  }, [sendMessage]);

  const ping = useCallback(() => {
    sendMessage({ type: 'ping', data: {} });
  }, [sendMessage]);

  // Auto-connect when token is available, disconnect when token is removed
  useEffect(() => {
    if (accessToken && !state.isConnected && !state.isConnecting) {
      connect();
    } else if (!accessToken && (state.isConnected || state.isConnecting)) {
      // Token was removed (logout) - disconnect immediately
      disconnect();
    }
  }, [accessToken, connect, disconnect, state.isConnected, state.isConnecting]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [cleanup]);

  const actions: WebSocketActions = {
    connect,
    disconnect,
    sendMessage,
    subscribeToEvents,
    emitEvent,
    getRecentEvents,
    startReplay,
    stopReplay,
    getReplayStatus,
    ping
  };

  return [state, actions];
};

// Enhanced WebSocket service hook
export const useWebSocketService = (
  connectionType: 'health' | 'dns_management' | 'security' | 'system' | 'admin',
  userId: string,
  options: {
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Event) => void;
  } = {}
) => {
  const eventHandlersRef = useRef<Map<string, (data: any) => void>>(new Map());

  const [state, actions] = useWebSocket({
    connectionType,
    autoReconnect: true,
    onMessage: (message: WebSocketMessage) => {
      // Call registered event handlers
      const handler = eventHandlersRef.current.get(message.type);
      if (handler) {
        handler(message.data);
      }
    },
    onConnect: options.onConnect,
    onDisconnect: options.onDisconnect,
    onError: options.onError
  });

  const subscribe = useCallback((eventType: string, handler: (data: any) => void) => {
    eventHandlersRef.current.set(eventType, handler);
  }, []);

  const unsubscribe = useCallback((eventType: string) => {
    eventHandlersRef.current.delete(eventType);
  }, []);

  const getStats = useCallback(() => {
    actions.sendMessage({ type: 'get_connection_stats' });
  }, [actions]);

  return {
    isConnected: state.isConnected,
    isConnecting: state.isConnecting,
    connectionStatus: state.isConnected ? 'connected' : state.isConnecting ? 'connecting' : 'disconnected',
    reconnectAttempts: state.reconnectAttempts,
    error: state.error,
    sendMessage: actions.sendMessage,
    subscribe,
    unsubscribe,
    getStats,
    connect: actions.connect,
    disconnect: actions.disconnect
  };
};

// Specialized hooks for different connection types
// These now use the WebSocketContext to avoid creating multiple connections
export const useHealthWebSocket = (userId: string, options?: any) => {
  console.warn('useHealthWebSocket is deprecated. Use useWebSocketContext instead to avoid connection storms.');
  return {
    isConnected: false,
    isConnecting: false,
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    error: 'Deprecated hook - use useWebSocketContext',
    sendMessage: () => {},
    subscribe: () => {},
    unsubscribe: () => {},
    getStats: () => {},
    connect: () => {},
    disconnect: () => {}
  };
};

export const useDNSWebSocket = (userId: string, options?: any) => {
  console.warn('useDNSWebSocket is deprecated. Use useWebSocketContext instead to avoid connection storms.');
  return {
    isConnected: false,
    isConnecting: false,
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    error: 'Deprecated hook - use useWebSocketContext',
    sendMessage: () => {},
    subscribe: () => {},
    unsubscribe: () => {},
    getStats: () => {},
    connect: () => {},
    disconnect: () => {}
  };
};

export const useSecurityWebSocket = (userId: string, options?: any) => {
  console.warn('useSecurityWebSocket is deprecated. Use useWebSocketContext instead to avoid connection storms.');
  return {
    isConnected: false,
    isConnecting: false,
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    error: 'Deprecated hook - use useWebSocketContext',
    sendMessage: () => {},
    subscribe: () => {},
    unsubscribe: () => {},
    getStats: () => {},
    connect: () => {},
    disconnect: () => {}
  };
};

export const useSystemWebSocket = (userId: string, options?: any) => {
  console.warn('useSystemWebSocket is deprecated. Use useWebSocketContext instead to avoid connection storms.');
  return {
    isConnected: false,
    isConnecting: false,
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    error: 'Deprecated hook - use useWebSocketContext',
    sendMessage: () => {},
    subscribe: () => {},
    unsubscribe: () => {},
    getStats: () => {},
    connect: () => {},
    disconnect: () => {}
  };
};

export const useAdminWebSocket = (userId: string, options?: any) => {
  console.warn('useAdminWebSocket is deprecated. Use useWebSocketContext instead to avoid connection storms.');
  return {
    isConnected: false,
    isConnecting: false,
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    error: 'Deprecated hook - use useWebSocketContext',
    sendMessage: () => {},
    subscribe: () => {},
    unsubscribe: () => {},
    getStats: () => {},
    connect: () => {},
    disconnect: () => {}
  };
};

export default useWebSocket;