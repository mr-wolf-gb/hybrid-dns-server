/**
 * Global WebSocket Service
 * Ensures only one WebSocket connection per connection type to prevent connection storms
 */

interface WebSocketConnection {
  websocket: WebSocket;
  connectionType: string;
  isConnected: boolean;
  subscribers: Set<string>;
  messageHandlers: Map<string, (message: any) => void>;
  connectHandlers: Map<string, () => void>;
  disconnectHandlers: Map<string, () => void>;
  errorHandlers: Map<string, (error: Event) => void>;
}

class GlobalWebSocketService {
  private connections: Map<string, WebSocketConnection> = new Map();
  private reconnectTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private readonly MAX_RECONNECT_ATTEMPTS = 5;
  private readonly RECONNECT_DELAY = 5000;

  /**
   * Subscribe to a WebSocket connection
   * Creates the connection if it doesn't exist, otherwise reuses existing connection
   */
  subscribe(
    connectionType: string,
    subscriberId: string,
    token: string,
    handlers: {
      onMessage?: (message: any) => void;
      onConnect?: () => void;
      onDisconnect?: () => void;
      onError?: (error: Event) => void;
    } = {}
  ): boolean {
    const connection = this.connections.get(connectionType);

    if (connection) {
      // Add subscriber to existing connection
      connection.subscribers.add(subscriberId);
      
      if (handlers.onMessage) {
        connection.messageHandlers.set(subscriberId, handlers.onMessage);
      }
      if (handlers.onConnect) {
        connection.connectHandlers.set(subscriberId, handlers.onConnect);
      }
      if (handlers.onDisconnect) {
        connection.disconnectHandlers.set(subscriberId, handlers.onDisconnect);
      }
      if (handlers.onError) {
        connection.errorHandlers.set(subscriberId, handlers.onError);
      }

      // If already connected, call connect handler immediately
      if (connection.isConnected && handlers.onConnect) {
        handlers.onConnect();
      }

      console.log(`Subscribed to existing WebSocket connection: ${connectionType} (${connection.subscribers.size} subscribers)`);
      return true;
    }

    // Create new connection
    return this.createConnection(connectionType, subscriberId, token, handlers);
  }

  /**
   * Unsubscribe from a WebSocket connection
   * Closes the connection if no more subscribers
   */
  unsubscribe(connectionType: string, subscriberId: string): void {
    const connection = this.connections.get(connectionType);
    if (!connection) return;

    // Remove subscriber
    connection.subscribers.delete(subscriberId);
    connection.messageHandlers.delete(subscriberId);
    connection.connectHandlers.delete(subscriberId);
    connection.disconnectHandlers.delete(subscriberId);
    connection.errorHandlers.delete(subscriberId);

    console.log(`Unsubscribed from WebSocket connection: ${connectionType} (${connection.subscribers.size} subscribers remaining)`);

    // If no more subscribers, close the connection
    if (connection.subscribers.size === 0) {
      console.log(`Closing WebSocket connection (no subscribers): ${connectionType}`);
      connection.websocket.close(1000, 'No more subscribers');
      this.connections.delete(connectionType);
      
      // Clear reconnect timeout if exists
      const timeout = this.reconnectTimeouts.get(connectionType);
      if (timeout) {
        clearTimeout(timeout);
        this.reconnectTimeouts.delete(connectionType);
      }
    }
  }

  /**
   * Send a message through a WebSocket connection
   */
  sendMessage(connectionType: string, message: any): boolean {
    const connection = this.connections.get(connectionType);
    if (!connection || !connection.isConnected) {
      console.warn(`Cannot send message: WebSocket connection ${connectionType} not available`);
      return false;
    }

    try {
      connection.websocket.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error(`Error sending WebSocket message to ${connectionType}:`, error);
      return false;
    }
  }

  /**
   * Check if a connection is active
   */
  isConnected(connectionType: string): boolean {
    const connection = this.connections.get(connectionType);
    return connection ? connection.isConnected : false;
  }

  /**
   * Get connection statistics
   */
  getStats() {
    const stats = {
      totalConnections: this.connections.size,
      connections: {} as Record<string, { subscribers: number; isConnected: boolean }>
    };

    this.connections.forEach((connection, type) => {
      stats.connections[type] = {
        subscribers: connection.subscribers.size,
        isConnected: connection.isConnected
      };
    });

    return stats;
  }

  /**
   * Disconnect all connections
   */
  disconnectAll(): void {
    console.log('Disconnecting all WebSocket connections');
    
    this.connections.forEach((connection, type) => {
      connection.websocket.close(1000, 'Service shutdown');
    });

    this.connections.clear();
    
    // Clear all reconnect timeouts
    this.reconnectTimeouts.forEach(timeout => clearTimeout(timeout));
    this.reconnectTimeouts.clear();
  }

  private createConnection(
    connectionType: string,
    subscriberId: string,
    token: string,
    handlers: {
      onMessage?: (message: any) => void;
      onConnect?: () => void;
      onDisconnect?: () => void;
      onError?: (error: Event) => void;
    }
  ): boolean {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/websocket/ws/${connectionType}?token=${encodeURIComponent(token)}`;

      console.log(`Creating WebSocket connection: ${connectionType} -> ${wsUrl}`);

      const websocket = new WebSocket(wsUrl);
      
      const connection: WebSocketConnection = {
        websocket,
        connectionType,
        isConnected: false,
        subscribers: new Set([subscriberId]),
        messageHandlers: new Map(),
        connectHandlers: new Map(),
        disconnectHandlers: new Map(),
        errorHandlers: new Map()
      };

      // Add handlers for this subscriber
      if (handlers.onMessage) {
        connection.messageHandlers.set(subscriberId, handlers.onMessage);
      }
      if (handlers.onConnect) {
        connection.connectHandlers.set(subscriberId, handlers.onConnect);
      }
      if (handlers.onDisconnect) {
        connection.disconnectHandlers.set(subscriberId, handlers.onDisconnect);
      }
      if (handlers.onError) {
        connection.errorHandlers.set(subscriberId, handlers.onError);
      }

      // Set up WebSocket event handlers
      websocket.onopen = () => {
        console.log(`WebSocket connected: ${connectionType}`);
        connection.isConnected = true;
        
        // Call all connect handlers
        connection.connectHandlers.forEach(handler => {
          try {
            handler();
          } catch (error) {
            console.error(`Error in connect handler for ${connectionType}:`, error);
          }
        });
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Call all message handlers
          connection.messageHandlers.forEach(handler => {
            try {
              handler(message);
            } catch (error) {
              console.error(`Error in message handler for ${connectionType}:`, error);
            }
          });
        } catch (error) {
          console.error(`Error parsing WebSocket message for ${connectionType}:`, error);
        }
      };

      websocket.onclose = (event) => {
        console.log(`WebSocket closed: ${connectionType}, code: ${event.code}`);
        connection.isConnected = false;
        
        // Call all disconnect handlers
        connection.disconnectHandlers.forEach(handler => {
          try {
            handler();
          } catch (error) {
            console.error(`Error in disconnect handler for ${connectionType}:`, error);
          }
        });

        // Auto-reconnect if not a normal closure and we still have subscribers
        if (event.code !== 1000 && connection.subscribers.size > 0) {
          console.log(`Scheduling reconnect for ${connectionType}`);
          const timeout = setTimeout(() => {
            this.reconnect(connectionType, token);
          }, this.RECONNECT_DELAY);
          
          this.reconnectTimeouts.set(connectionType, timeout);
        } else {
          // Clean up connection
          this.connections.delete(connectionType);
        }
      };

      websocket.onerror = (error) => {
        console.error(`WebSocket error: ${connectionType}`, error);
        
        // Call all error handlers
        connection.errorHandlers.forEach(handler => {
          try {
            handler(error);
          } catch (handlerError) {
            console.error(`Error in error handler for ${connectionType}:`, handlerError);
          }
        });
      };

      // Store the connection
      this.connections.set(connectionType, connection);
      
      return true;

    } catch (error) {
      console.error(`Failed to create WebSocket connection ${connectionType}:`, error);
      return false;
    }
  }

  private reconnect(connectionType: string, token: string): void {
    const connection = this.connections.get(connectionType);
    if (!connection || connection.subscribers.size === 0) {
      console.log(`Skipping reconnect for ${connectionType}: no subscribers`);
      return;
    }

    console.log(`Reconnecting WebSocket: ${connectionType}`);
    
    // Remove the old connection
    this.connections.delete(connectionType);
    
    // Create new connection with existing handlers
    const handlers = {
      onMessage: (message: any) => {
        connection.messageHandlers.forEach(handler => {
          try {
            handler(message);
          } catch (error) {
            console.error(`Error in message handler during reconnect for ${connectionType}:`, error);
          }
        });
      },
      onConnect: () => {
        connection.connectHandlers.forEach(handler => {
          try {
            handler();
          } catch (error) {
            console.error(`Error in connect handler during reconnect for ${connectionType}:`, error);
          }
        });
      },
      onDisconnect: () => {
        connection.disconnectHandlers.forEach(handler => {
          try {
            handler();
          } catch (error) {
            console.error(`Error in disconnect handler during reconnect for ${connectionType}:`, error);
          }
        });
      },
      onError: (error: Event) => {
        connection.errorHandlers.forEach(handler => {
          try {
            handler(error);
          } catch (handlerError) {
            console.error(`Error in error handler during reconnect for ${connectionType}:`, handlerError);
          }
        });
      }
    };

    this.createConnection(connectionType, 'reconnect', token, handlers);
  }
}

// Global singleton instance
const globalWebSocketService = new GlobalWebSocketService();

export default globalWebSocketService;
export { GlobalWebSocketService };