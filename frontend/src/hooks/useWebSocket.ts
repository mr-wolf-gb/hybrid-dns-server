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

  const connect = useCallback(() => {
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
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/websocket/ws/${config.connectionType}?token=${encodeURIComponent(accessToken)}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          reconnectAttempts: 0
        }));

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', data: {} }));
          }
        }, 30000); // Ping every 30 seconds

        configRef.current.onConnect?.();
      };

      ws.onmessage = (event) => {
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
      };

      ws.onclose = (event) => {
        cleanup();
        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false
        }));

        configRef.current.onDisconnect?.();

        // Check if close was due to authentication issues
        if (event.code === 1008 || event.code === 4001) {
          // Authentication failed - don't reconnect
          console.warn('WebSocket closed due to authentication issues, not reconnecting');
          setState(prev => ({
            ...prev,
            error: 'Authentication failed'
          }));
          return;
        }

        // Auto-reconnect if enabled and not a normal closure
        if (configRef.current.autoReconnect !== false && event.code !== 1000) {
          const maxAttempts = configRef.current.maxReconnectAttempts || 5;
          const interval = configRef.current.reconnectInterval || 5000;

          if (state.reconnectAttempts < maxAttempts) {
            setState(prev => ({ ...prev, reconnectAttempts: prev.reconnectAttempts + 1 }));
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, interval);
          } else {
            setState(prev => ({
              ...prev,
              error: 'Max reconnection attempts reached'
            }));
          }
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket connection error:', error);
        setState(prev => ({
          ...prev,
          error: 'WebSocket connection error',
          isConnecting: false
        }));
        configRef.current.onError?.(error);
      };

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: `Failed to create WebSocket connection: ${error}`,
        isConnecting: false
      }));
    }
  }, [accessToken, state.isConnecting, state.isConnected, config.connectionType, cleanup]);

  const disconnect = useCallback(() => {
    cleanup();
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
  }, [cleanup]);

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
export const useHealthWebSocket = (userId: string, options?: any) =>
  useWebSocketService('health', userId, options);

export const useDNSWebSocket = (userId: string, options?: any) =>
  useWebSocketService('dns_management', userId, options);

export const useSecurityWebSocket = (userId: string, options?: any) =>
  useWebSocketService('security', userId, options);

export const useSystemWebSocket = (userId: string, options?: any) =>
  useWebSocketService('system', userId, options);

export const useAdminWebSocket = (userId: string, options?: any) =>
  useWebSocketService('admin', userId, options);

export default useWebSocket;