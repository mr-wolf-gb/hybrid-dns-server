/**
 * WebSocket context for managing real-time event broadcasting across the application
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useWebSocket, WebSocketMessage, WebSocketState, WebSocketActions } from '../hooks/useWebSocket';
import { useAuth } from './AuthContext';
import { toast } from 'react-toastify';

interface EventHandler {
  id: string;
  eventTypes: string[];
  handler: (message: WebSocketMessage) => void;
}

interface WebSocketContextType {
  // Connection states for different types
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
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const [eventHandlers, setEventHandlers] = useState<EventHandler[]>([]);
  const [connectionStats, setConnectionStats] = useState<any>(null);

  // Global message handler
  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Handle global events
    if (message.type === 'health_alert' && message.severity === 'critical') {
      toast.error(`Health Alert: ${message.data?.message || 'Critical system issue detected'}`);
    } else if (message.type === 'security_alert') {
      toast.error(`Security Alert: ${message.data?.message || 'Security threat detected'}`);
    } else if (message.type === 'bind_reload') {
      toast.success('DNS configuration reloaded successfully');
    } else if (message.type === 'system_status' && message.data?.bind9_running === false) {
      toast.error('BIND9 service is not running');
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

  // Connection error handler
  const handleError = useCallback((error: Event) => {
    console.error('WebSocket error:', error);
    toast.error('WebSocket connection error');
  }, []);

  // Connection handlers
  const handleConnect = useCallback(() => {
    toast.success('Real-time connection established');
  }, []);

  const handleDisconnect = useCallback(() => {
    toast.error('Real-time connection lost');
  }, []);

  // Health monitoring connection
  const healthConnection = useWebSocket({
    connectionType: 'health',
    autoReconnect: true,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  // DNS management connection
  const dnsConnection = useWebSocket({
    connectionType: 'dns_management',
    autoReconnect: true,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  // Security monitoring connection
  const securityConnection = useWebSocket({
    connectionType: 'security',
    autoReconnect: true,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  // System monitoring connection
  const systemConnection = useWebSocket({
    connectionType: 'system',
    autoReconnect: true,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  // Admin connection (only for admin users)
  const adminConnection = user?.is_admin ? useWebSocket({
    connectionType: 'admin',
    autoReconnect: true,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  }) : undefined;

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
  const broadcastEvent = useCallback((eventData: any, connectionType?: string) => {
    const connections = [
      healthConnection,
      dnsConnection,
      securityConnection,
      systemConnection,
      ...(adminConnection ? [adminConnection] : [])
    ];

    if (connectionType) {
      const targetConnection = connections.find(([state, actions]) => {
        // This is a simplified check - in practice you'd need to track connection types
        return true; // For now, broadcast to all
      });

      if (targetConnection) {
        targetConnection[1].emitEvent(eventData);
      }
    } else {
      // Broadcast to all connections
      connections.forEach(([state, actions]) => {
        if (state.isConnected) {
          actions.emitEvent(eventData);
        }
      });
    }
  }, [healthConnection, dnsConnection, securityConnection, systemConnection, adminConnection]);

  // Start event replay
  const startEventReplay = useCallback((replayConfig: any) => {
    // Use admin connection if available, otherwise use system connection
    const connection = adminConnection || systemConnection;
    if (connection[0].isConnected) {
      connection[1].startReplay(replayConfig);
    } else {
      toast.error('No active connection for event replay');
    }
  }, [adminConnection, systemConnection]);

  // Stop event replay
  const stopEventReplay = useCallback((replayId: string) => {
    const connection = adminConnection || systemConnection;
    if (connection[0].isConnected) {
      connection[1].stopReplay(replayId);
    } else {
      toast.error('No active connection to stop replay');
    }
  }, [adminConnection, systemConnection]);

  // Connect all connections
  const connectAll = useCallback(() => {
    healthConnection[1].connect();
    dnsConnection[1].connect();
    securityConnection[1].connect();
    systemConnection[1].connect();
    if (adminConnection) {
      adminConnection[1].connect();
    }
  }, [healthConnection, dnsConnection, securityConnection, systemConnection, adminConnection]);

  // Disconnect all connections
  const disconnectAll = useCallback(() => {
    healthConnection[1].disconnect();
    dnsConnection[1].disconnect();
    securityConnection[1].disconnect();
    systemConnection[1].disconnect();
    if (adminConnection) {
      adminConnection[1].disconnect();
    }
  }, [healthConnection, dnsConnection, securityConnection, systemConnection, adminConnection]);

  // Get connection statistics
  const getConnectionStats = useCallback(() => {
    const stats = {
      health: {
        connected: healthConnection[0].isConnected,
        error: healthConnection[0].error,
        reconnectAttempts: healthConnection[0].reconnectAttempts
      },
      dns: {
        connected: dnsConnection[0].isConnected,
        error: dnsConnection[0].error,
        reconnectAttempts: dnsConnection[0].reconnectAttempts
      },
      security: {
        connected: securityConnection[0].isConnected,
        error: securityConnection[0].error,
        reconnectAttempts: securityConnection[0].reconnectAttempts
      },
      system: {
        connected: systemConnection[0].isConnected,
        error: systemConnection[0].error,
        reconnectAttempts: systemConnection[0].reconnectAttempts
      },
      admin: adminConnection ? {
        connected: adminConnection[0].isConnected,
        error: adminConnection[0].error,
        reconnectAttempts: adminConnection[0].reconnectAttempts
      } : null
    };

    return stats;
  }, [healthConnection, dnsConnection, securityConnection, systemConnection, adminConnection]);

  // Update connection stats periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setConnectionStats(getConnectionStats());
    }, 5000);

    return () => clearInterval(interval);
  }, [getConnectionStats]);

  // Auto-connect when user is available
  useEffect(() => {
    if (user) {
      connectAll();
    } else {
      disconnectAll();
    }
  }, [user, connectAll, disconnectAll]);

  const contextValue: WebSocketContextType = {
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
    getConnectionStats
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