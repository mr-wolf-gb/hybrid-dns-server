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

export const useWebSocket = (config: WebSocketConfig): [WebSocketState, WebSocketActions] => {
  const { token } = useAuth();
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
    if (!token || state.isConnecting || state.isConnected) {
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/websocket/ws/${config.connectionType}?token=${encodeURIComponent(token)}`;

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
  }, [token, state.isConnecting, state.isConnected, config.connectionType, cleanup]);

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

  // Auto-connect when token is available
  useEffect(() => {
    if (token && !state.isConnected && !state.isConnecting) {
      connect();
    }
  }, [token, connect, state.isConnected, state.isConnecting]);

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

export default useWebSocket;