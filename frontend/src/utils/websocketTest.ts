/**
 * WebSocket connection testing utilities
 */

/**
 * Test WebSocket connection health
 */
export const testWebSocketConnection = async (
    connectionType: string = 'health',
    token?: string
): Promise<{
    success: boolean;
    error?: string;
    latency?: number;
}> => {
    return new Promise((resolve) => {
        const startTime = Date.now();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        // Use provided token or get from localStorage
        const authToken = token || localStorage.getItem('access_token');

        if (!authToken) {
            resolve({
                success: false,
                error: 'No authentication token available'
            });
            return;
        }

        const wsUrl = `${protocol}//${host}/api/websocket/ws/${connectionType}?token=${encodeURIComponent(authToken)}`;

        try {
            const ws = new WebSocket(wsUrl);

            const timeout = setTimeout(() => {
                ws.close();
                resolve({
                    success: false,
                    error: 'Connection timeout (10 seconds)'
                });
            }, 10000);

            ws.onopen = () => {
                const latency = Date.now() - startTime;
                clearTimeout(timeout);
                ws.close(1000, 'Test completed');
                resolve({
                    success: true,
                    latency
                });
            };

            ws.onerror = (error) => {
                clearTimeout(timeout);
                console.error('WebSocket test error:', error);
                resolve({
                    success: false,
                    error: 'Connection failed - check console for details'
                });
            };

            ws.onclose = (event) => {
                clearTimeout(timeout);
                if (event.code !== 1000) {
                    resolve({
                        success: false,
                        error: `Connection closed with code ${event.code}: ${event.reason || 'Unknown reason'}`
                    });
                }
            };

        } catch (error) {
            resolve({
                success: false,
                error: `Failed to create WebSocket: ${error}`
            });
        }
    });
};

/**
 * Test all WebSocket connection types
 */
export const testAllWebSocketConnections = async (token?: string) => {
    const connectionTypes = ['health', 'dns_management', 'security', 'system'];
    const results: Record<string, any> = {};

    for (const type of connectionTypes) {
        console.log(`Testing WebSocket connection: ${type}`);
        results[type] = await testWebSocketConnection(type, token);

        // Add small delay between tests
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    return results;
};

/**
 * Check WebSocket service health via REST API
 */
export const checkWebSocketHealth = async (): Promise<any> => {
    try {
        const response = await fetch('/api/websocket/ws/health-check');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('WebSocket health check failed:', error);
        throw error;
    }
};