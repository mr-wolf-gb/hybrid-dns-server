/**
 * WebSocket context for managing real-time event broadcasting across the application
 * Uses a global WebSocket service to prevent connection storms
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode, useRef } from 'react';
import { useAuth } from './AuthContext';
import { toast } from 'react-toastify';
import globalWebSocketService from '../services/GlobalWebSocketService';

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

// Notification throttling to prevent spam
const notificationThrottle = new Map<string, number>();
let notificationPreferences: any = null;

// Load notification preferences
const loadNotificationPreferences = () => {
  // Listen for preference updates
  window.addEventListener('notificationPreferencesUpdated', (event: any) => {
    notificationPreferences = event.detail;
  });
};

const shouldShowNotification = (type: string, event?: any): boolean => {
  const now = Date.now();
  
  // Use dynamic throttle duration from preferences
  const throttleDuration = notificationPreferences?.throttle_duration || 5000;
  const lastShown = notificationThrottle.get(type) || 0;

  if (now - lastShown > throttleDuration) {
    // Check if notification should be shown based on preferences
    if (notificationPreferences && event) {
      // Check severity filter
      const severity = event.severity || 'info';
      if (!notificationPreferences.enabled_severities.includes(severity)) {
        return false;
      }
      
      // Check category filter
      const category = getEventCategory(event.type || type);
      if (!notificationPreferences.enabled_categories.includes(category)) {
        return false;
      }
      
      // Special handling for health updates
      if (category === 'health' && !notificationPreferences.show_health_updates) {
        return false;
      }
    }
    
    notificationThrottle.set(type, now);
    return true;
  }
  return false;
};

const getEventCategory = (eventType: string): string => {
  if (eventType.includes('health') || eventType.includes('forwarder')) {
    return 'health';
  }
  if (eventType.includes('zone') || eventType.includes('record') || eventType.includes('dns')) {
    return 'dns';
  }
  if (eventType.includes('security') || eventType.includes('threat') || eventType.includes('rpz')) {
    return 'security';
  }
  if (eventType.includes('system') || eventType.includes('bind') || eventType.includes('config')) {
    return 'system';
  }
  return 'system';
};

// Initialize preference loading
loadNotificationPreferences();

interface EventHandler {
  id: string;
  eventTypes: string[];
  handler: (message: WebSocketMessage) => void;
}

interface WebSocketContextType {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;

  // Legacy compatibility - return the same connection state for all types
  healthConnection: [WebSocketState, WebSocketActions];
  dnsConnection: [WebSocketState, WebSocketActions];
  securityConnection: [WebSocketState, WebSocketActions];
  systemConnection: [WebSocketState, WebSocketActions];
  adminConnection?: [WebSocketState, WebSocketActions];

  // Global event handling
  registerEventHandler: (id: string, eventTypes: string[], handler: (message: WebSocketMessage) => void) => void;
  unregisterEventHandler: (id: string) => void;

  // Event broadcasting
  broadcastEvent: (eventData: any, connectionType?: string) => void;

  // Event replay
  startEventReplay: (replayConfig: any) => void;
  stopEventReplay: (replayId: string) => void;

  // Connection management
  connectAll: () => void;
  disconnectAll: () => void;

  // Statistics
  getConnectionStats: () => any;

  // Direct messaging
  sendMessage: (message: any) => boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user, accessToken, isLoading } = useAuth();
  const [eventHandlers, setEventHandlers] = useState<EventHandler[]>([]);
  const [connectionStats, setConnectionStats] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const subscriberIdRef = useRef<string>(`websocket-context-${Date.now()}`);
  const hasInitialized = useRef(false);

  // Global message handler with throttling
  const handleMessage = useCallback((message: WebSocketMessage) => {
    setLastMessage(message);

    // Handle global events with notification throttling
    if (message.type === 'health_alert' && message.severity === 'critical') {
      if (shouldShowNotification('health_alert_critical', message)) {
        toast.error(`Health Alert: ${message.data?.message || 'Critical system issue detected'}`);
      }
    } else if (message.type === 'security_alert') {
      if (shouldShowNotification('security_alert', message)) {
        toast.error(`Security Alert: ${message.data?.message || 'Security threat detected'}`);
      }
    } else if (message.type === 'bind_reload') {
      if (shouldShowNotification('bind_reload', message)) {
        toast.success('DNS configuration reloaded successfully');
      }
    } else if (message.type === 'system_status' && message.data?.bind9_running === false) {
      if (shouldShowNotification('bind9_down', message)) {
        toast.error('BIND9 service is not running');
      }
    }

    // Call registered event handlers
    eventHandlers.forEach(handler => {
      if (handler.eventTypes.includes('*') || handler.eventTypes.includes(message.type)) {
        try {
          handler.handler(message);
        } catch (error) {
          console.error(`Error in event handler ${handler.id}:`, error);
        }
      }
    });
  }, [eventHandlers]);

  // Connection handlers
  const handleConnect = useCallback(() => {
    setIsConnected(true);
    setIsConnecting(false);
    setError(null);
    if (shouldShowNotification('connection_established', { type: 'system', severity: 'info' })) {
      toast.success('Real-time connection established');
    }
  }, []);

  const handleDisconnect = useCallback(() => {
    setIsConnected(false);
    setIsConnecting(false);
    if (shouldShowNotification('connection_lost', { type: 'system', severity: 'warning' })) {
      toast.error('Real-time connection lost');
    }
  }, []);

  const handleError = useCallback((error: Event) => {
    setError('WebSocket connection error');
    setIsConnecting(false);
    console.error('WebSocket error:', error);
    toast.error('WebSocket connection error');
  }, []);

  // Create mock WebSocket state and actions for backward compatibility
  const createMockConnection = useCallback((): [WebSocketState, WebSocketActions] => {
    const state: WebSocketState = {
      isConnected,
      isConnecting,
      error,
      lastMessage,
      connectionStats,
      reconnectAttempts: 0
    };

    const actions: WebSocketActions = {
      connect: () => {
        if (user && accessToken && !isConnecting && !isConnected) {
          setIsConnecting(true);
          globalWebSocketService.subscribe('admin', subscriberIdRef.current, accessToken, {
            onMessage: handleMessage,
            onConnect: handleConnect,
            onDisconnect: handleDisconnect,
            onError: handleError
          });
        }
      },
      disconnect: () => {
        globalWebSocketService.unsubscribe('admin', subscriberIdRef.current);
        setIsConnected(false);
        setIsConnecting(false);
      },
      sendMessage: (message: any) => {
        return globalWebSocketService.sendMessage('admin', message);
      },
      subscribeToEvents: (eventTypes: string[]) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'subscribe_events',
          data: { event_types: eventTypes }
        });
      },
      emitEvent: (eventData: any) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'emit_event',
          data: eventData
        });
      },
      getRecentEvents: (limit: number = 50) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'get_recent_events',
          data: { limit }
        });
      },
      startReplay: (replayConfig: any) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'start_replay',
          data: replayConfig
        });
      },
      stopReplay: (replayId: string) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'stop_replay',
          data: { replay_id: replayId }
        });
      },
      getReplayStatus: (replayId: string) => {
        globalWebSocketService.sendMessage('admin', {
          type: 'get_replay_status',
          data: { replay_id: replayId }
        });
      },
      ping: () => {
        globalWebSocketService.sendMessage('admin', { type: 'ping', data: {} });
      }
    };

    return [state, actions];
  }, [isConnected, isConnecting, error, lastMessage, connectionStats, user, accessToken, handleMessage, handleConnect, handleDisconnect, handleError]);

  // For backward compatibility, return the same connection for all types
  const connection = createMockConnection();
  const healthConnection = connection;
  const dnsConnection = connection;
  const securityConnection = connection;
  const systemConnection = connection;
  const adminConnection = user?.is_superuser ? connection : undefined;

  // Register event handler
  const registerEventHandler = useCallback((
    id: string,
    eventTypes: string[],
    handler: (message: WebSocketMessage) => void
  ) => {
    setEventHandlers(prev => {
      // Remove existing handler with same id
      const filtered = prev.filter(h => h.id !== id);
      return [...filtered, { id, eventTypes, handler }];
    });
  }, []);

  // Unregister event handler
  const unregisterEventHandler = useCallback((id: string) => {
    setEventHandlers(prev => prev.filter(h => h.id !== id));
  }, []);

  // Broadcast event
  const broadcastEvent = useCallback((eventData: any, _connectionType?: string) => {
    globalWebSocketService.sendMessage('admin', {
      type: 'emit_event',
      data: eventData
    });
  }, []);

  // Start event replay
  const startEventReplay = useCallback((replayConfig: any) => {
    if (isConnected) {
      globalWebSocketService.sendMessage('admin', {
        type: 'start_replay',
        data: replayConfig
      });
    } else {
      toast.error('No active connection for event replay');
    }
  }, [isConnected]);

  // Stop event replay
  const stopEventReplay = useCallback((replayId: string) => {
    if (isConnected) {
      globalWebSocketService.sendMessage('admin', {
        type: 'stop_replay',
        data: { replay_id: replayId }
      });
    } else {
      toast.error('No active connection to stop replay');
    }
  }, [isConnected]);

  // Connect all connections (now just one)
  const connectAll = useCallback(() => {
    if (user && accessToken && !isConnecting && !isConnected) {
      setIsConnecting(true);
      globalWebSocketService.subscribe('admin', subscriberIdRef.current, accessToken, {
        onMessage: handleMessage,
        onConnect: handleConnect,
        onDisconnect: handleDisconnect,
        onError: handleError
      });
    }
  }, [user, accessToken, isConnecting, isConnected, handleMessage, handleConnect, handleDisconnect, handleError]);

  // Disconnect all connections (now just one)
  const disconnectAll = useCallback(() => {
    globalWebSocketService.unsubscribe('admin', subscriberIdRef.current);
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  // Send message directly
  const sendMessage = useCallback((message: any) => {
    return globalWebSocketService.sendMessage('admin', message);
  }, []);

  // Get connection statistics
  const getConnectionStats = useCallback(() => {
    const globalStats = globalWebSocketService.getStats();
    const baseStats = {
      connected: isConnected,
      error: error,
      reconnectAttempts: 0
    };

    // Return the same stats for all connection types for backward compatibility
    const stats = {
      health: baseStats,
      dns: baseStats,
      security: baseStats,
      system: baseStats,
      admin: user?.is_superuser ? baseStats : null,
      global: globalStats
    };

    return stats;
  }, [isConnected, error, user?.is_superuser]);

  // Update connection stats periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setConnectionStats(getConnectionStats());
    }, 5000);

    return () => clearInterval(interval);
  }, [getConnectionStats]);

  // Auto-connect when user is available
  useEffect(() => {
    // Don't do anything while auth is still loading
    if (isLoading) return;

    if (user && accessToken && !isConnecting && !isConnected) {
      console.log('Auto-connecting WebSocket for user:', user.username);
      hasInitialized.current = true;
      connectAll();
    } else if (!user && hasInitialized.current && (isConnected || isConnecting)) {
      // Only disconnect if we were previously initialized and connected
      console.log('User logged out, disconnecting WebSocket');
      disconnectAll();
      // Clear event handlers
      setEventHandlers([]);
      setError(null);
      setLastMessage(null);
      hasInitialized.current = false;
    }
  }, [user, accessToken, isLoading, connectAll, disconnectAll, isConnecting, isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnectAll();
    };
  }, [disconnectAll]);

  const contextValue: WebSocketContextType = {
    isConnected,
    isConnecting,
    error,
    lastMessage,
    healthConnection,
    dnsConnection,
    securityConnection,
    systemConnection,
    adminConnection,
    registerEventHandler,
    unregisterEventHandler,
    broadcastEvent,
    startEventReplay,
    stopEventReplay,
    connectAll,
    disconnectAll,
    getConnectionStats,
    sendMessage
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

export default WebSocketContext;