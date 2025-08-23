/**
 * WebSocket cleanup utilities for logout and session management
 */

import { forceDisconnectAll } from '@/services/websocketService'

/**
 * Clean up all WebSocket connections on logout
 * This ensures no connections remain active after user logs out
 */
export const cleanupWebSocketsOnLogout = (): void => {
    try {
        forceDisconnectAll()
        console.log('WebSocket connections cleaned up on logout')
    } catch (error) {
        console.error('Error cleaning up WebSocket connections:', error)
    }
}

/**
 * Handle session expiration by disconnecting all WebSockets
 */
export const handleSessionExpiration = (): void => {
    try {
        forceDisconnectAll()
        console.log('WebSocket connections cleaned up due to session expiration')
    } catch (error) {
        console.error('Error cleaning up WebSocket connections on session expiration:', error)
    }
}

/**
 * Check if there are any active WebSocket connections
 * Useful for debugging connection leaks
 */
export const checkActiveConnections = (): boolean => {
    // This would need to be implemented in the websocketService
    // For now, we'll just return false as a placeholder
    return false
}