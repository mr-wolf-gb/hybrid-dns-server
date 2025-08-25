/**
 * WebSocket Connection Manager
 * Prevents multiple connections of the same type and manages connection lifecycle
 */

interface ConnectionInfo {
    websocket: WebSocket;
    connectionType: string;
    userId: string;
    token: string;
    isConnected: boolean;
    reconnectAttempts: number;
    lastConnectTime: number;
}

class WebSocketConnectionManager {
    private connections: Map<string, ConnectionInfo> = new Map();
    private pendingConnections: Set<string> = new Set();
    private readonly MAX_RECONNECT_ATTEMPTS = 5;
    private readonly RECONNECT_DELAY = 5000;
    private readonly CONNECTION_TIMEOUT = 10000;

    /**
     * Get or create a WebSocket connection
     * Prevents duplicate connections by reusing existing ones
     */
    async getConnection(
        connectionType: string,
        userId: string,
        token: string,
        onMessage?: (event: MessageEvent) => void,
        onConnect?: () => void,
        onDisconnect?: () => void,
        onError?: (error: Event) => void
    ): Promise<WebSocket | null> {
        const connectionKey = `${userId}:${connectionType}`;

        // Check if we already have a connection
        const existingConnection = this.connections.get(connectionKey);
        if (existingConnection && existingConnection.websocket.readyState === WebSocket.OPEN) {
            console.log(`Reusing existing WebSocket connection: ${connectionKey}`);
            return existingConnection.websocket;
        }

        // Check if connection is already pending
        if (this.pendingConnections.has(connectionKey)) {
            console.log(`WebSocket connection already pending: ${connectionKey}`);
            return null;
        }

        // Create new connection
        return this.createConnection(connectionKey, connectionType, userId, token, onMessage, onConnect, onDisconnect, onError);
    }

    private async createConnection(
        connectionKey: string,
        connectionType: string,
        userId: string,
        token: string,
        onMessage?: (event: MessageEvent) => void,
        onConnect?: () => void,
        onDisconnect?: () => void,
        onError?: (error: Event) => void
    ): Promise<WebSocket | null> {
        this.pendingConnections.add(connectionKey);

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/api/websocket/ws/${connectionType}?token=${encodeURIComponent(token)}`;

            console.log(`Creating WebSocket connection: ${connectionKey} -> ${wsUrl}`);

            const websocket = new WebSocket(wsUrl);
            const connectionInfo: ConnectionInfo = {
                websocket,
                connectionType,
                userId,
                token,
                isConnected: false,
                reconnectAttempts: 0,
                lastConnectTime: Date.now()
            };

            // Set up event handlers
            websocket.onopen = () => {
                console.log(`WebSocket connected: ${connectionKey}`);
                connectionInfo.isConnected = true;
                connectionInfo.reconnectAttempts = 0;
                this.pendingConnections.delete(connectionKey);
                onConnect?.();
            };

            websocket.onmessage = (event) => {
                onMessage?.(event);
            };

            websocket.onclose = (event) => {
                console.log(`WebSocket closed: ${connectionKey}, code: ${event.code}`);
                connectionInfo.isConnected = false;
                this.connections.delete(connectionKey);
                this.pendingConnections.delete(connectionKey);
                onDisconnect?.();

                // Auto-reconnect if not a normal closure and within retry limits
                if (event.code !== 1000 && connectionInfo.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
                    setTimeout(() => {
                        this.reconnect(connectionKey, connectionType, userId, token, onMessage, onConnect, onDisconnect, onError);
                    }, this.RECONNECT_DELAY);
                }
            };

            websocket.onerror = (error) => {
                console.error(`WebSocket error: ${connectionKey}`, error);
                this.pendingConnections.delete(connectionKey);
                onError?.(error);
            };

            // Store connection info
            this.connections.set(connectionKey, connectionInfo);

            // Set connection timeout
            setTimeout(() => {
                if (websocket.readyState === WebSocket.CONNECTING) {
                    console.warn(`WebSocket connection timeout: ${connectionKey}`);
                    websocket.close();
                    this.pendingConnections.delete(connectionKey);
                }
            }, this.CONNECTION_TIMEOUT);

            return websocket;

        } catch (error) {
            console.error(`Failed to create WebSocket connection: ${connectionKey}`, error);
            this.pendingConnections.delete(connectionKey);
            return null;
        }
    }

    private async reconnect(
        connectionKey: string,
        connectionType: string,
        userId: string,
        token: string,
        onMessage?: (event: MessageEvent) => void,
        onConnect?: () => void,
        onDisconnect?: () => void,
        onError?: (error: Event) => void
    ) {
        const existingConnection = this.connections.get(connectionKey);
        if (existingConnection) {
            existingConnection.reconnectAttempts++;
            console.log(`Reconnecting WebSocket: ${connectionKey} (attempt ${existingConnection.reconnectAttempts})`);
        }

        await this.createConnection(connectionKey, connectionType, userId, token, onMessage, onConnect, onDisconnect, onError);
    }

    /**
     * Disconnect a specific connection
     */
    disconnect(connectionType: string, userId: string) {
        const connectionKey = `${userId}:${connectionType}`;
        const connection = this.connections.get(connectionKey);

        if (connection) {
            console.log(`Disconnecting WebSocket: ${connectionKey}`);
            connection.websocket.close(1000, 'User disconnected');
            this.connections.delete(connectionKey);
        }

        this.pendingConnections.delete(connectionKey);
    }

    /**
     * Disconnect all connections for a user
     */
    disconnectUser(userId: string) {
        console.log(`Disconnecting all WebSocket connections for user: ${userId}`);

        const connectionsToRemove: string[] = [];

        this.connections.forEach((connection, key) => {
            if (connection.userId === userId) {
                connection.websocket.close(1000, 'User logged out');
                connectionsToRemove.push(key);
            }
        });

        connectionsToRemove.forEach(key => {
            this.connections.delete(key);
            this.pendingConnections.delete(key);
        });
    }

    /**
     * Disconnect all connections
     */
    disconnectAll() {
        console.log('Disconnecting all WebSocket connections');

        this.connections.forEach((connection, key) => {
            connection.websocket.close(1000, 'Application shutdown');
        });

        this.connections.clear();
        this.pendingConnections.clear();
    }

    /**
     * Get connection statistics
     */
    getStats() {
        const stats = {
            totalConnections: this.connections.size,
            pendingConnections: this.pendingConnections.size,
            connectionsByType: {} as Record<string, number>,
            connectionsByUser: {} as Record<string, number>
        };

        this.connections.forEach((connection) => {
            // Count by type
            stats.connectionsByType[connection.connectionType] =
                (stats.connectionsByType[connection.connectionType] || 0) + 1;

            // Count by user
            stats.connectionsByUser[connection.userId] =
                (stats.connectionsByUser[connection.userId] || 0) + 1;
        });

        return stats;
    }

    /**
     * Check if a connection exists and is open
     */
    isConnected(connectionType: string, userId: string): boolean {
        const connectionKey = `${userId}:${connectionType}`;
        const connection = this.connections.get(connectionKey);
        return connection ? connection.isConnected && connection.websocket.readyState === WebSocket.OPEN : false;
    }
}

// Global singleton instance
const webSocketConnectionManager = new WebSocketConnectionManager();

export default webSocketConnectionManager;
export { WebSocketConnectionManager };