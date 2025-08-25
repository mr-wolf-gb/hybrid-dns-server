/**
 * React hook for using the Unified WebSocket Service
 * Provides easy integration with React components
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { 
  UnifiedWebSocketService, 
  getUnifiedWebSocketService, 
  disconnectUnifiedWebSocket,
  EventType,
  WebSocketMessage 
} from '../services/UnifiedWebSocketService'
import { ConnectionStatus, ConnectionHealth } from '../services/ConnectionHealthManager'

export interface UseUnifiedWebSocketOptions {
  autoConnect?: boolean
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

export interface UseUnifiedWebSocketReturn {
  // Connection state
  isConnected: boolean
  isHealthy: boolean
  connectionStatus: ConnectionStatus
  connectionHealth: ConnectionHealth
  
  // Connection methods
  connect: () => Promise<void>
  disconnect: () => void
  
  // Subscription methods
  subscribe: (eventTypes: EventType[]) => Promise<void>
  unsubscribe: (eventTypes: EventType[]) => Promise<void>
  getSubscriptions: () => EventType[]
  
  // Event handling
  registerEventHandler: (id: string, eventTypes: EventType[], handler: (data: any) => void) => void
  unregisterEventHandler: (id: string) => void
  
  // Messaging
  sendMessage: (message: any) => boolean
  
  // Health and stats
  performHealthCheck: () => void
  getConnectionStats: () => any
  
  // Service instance (for advanced usage)
  service: UnifiedWebSocketService | null
}

export const useUnifiedWebSocket = (options: UseUnifiedWebSocketOptions = {}): UseUnifiedWebSocketReturn => {
  const { accessToken } = useAuth()
  const [service, setService] = useState<UnifiedWebSocketService | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isHealthy, setIsHealthy] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
  const [connectionHealth, setConnectionHealth] = useState<ConnectionHealth>({
    isHealthy: false,
    lastPing: null,
    lastPong: null,
    latency: 0,
    consecutiveFailures: 0,
    uptime: 0,
    reconnectAttempts: 0,
    status: ConnectionStatus.DISCONNECTED
  })

  const optionsRef = useRef(options)
  const eventHandlersRef = useRef<Map<string, { eventTypes: EventType[], handler: (data: any) => void }>>(new Map())

  // Update options ref when options change
  useEffect(() => {
    optionsRef.current = options
  }, [options])

  // Initialize service when token is available
  useEffect(() => {
    if (accessToken && !service) {
      const newService = getUnifiedWebSocketService(accessToken, {
        onMessage: (message) => {
          optionsRef.current.onMessage?.(message)
        },
        onConnect: () => {
          setIsConnected(true)
          optionsRef.current.onConnect?.()
        },
        onDisconnect: () => {
          setIsConnected(false)
          optionsRef.current.onDisconnect?.()
        },
        onError: (error) => {
          optionsRef.current.onError?.(error)
        }
      })

      setService(newService)

      // Auto-connect if enabled
      if (options.autoConnect !== false) {
        newService.connect().catch(error => {
          console.error('Failed to auto-connect WebSocket:', error)
        })
      }
    }
  }, [accessToken, service, options.autoConnect])

  // Update connection state periodically
  useEffect(() => {
    if (!service) return

    const updateConnectionState = () => {
      setIsConnected(service.isConnectionOpen())
      setIsHealthy(service.isConnectionHealthy())
      setConnectionStatus(service.getConnectionStatus())
      setConnectionHealth(service.getConnectionHealth())
    }

    // Initial update
    updateConnectionState()

    // Set up periodic updates
    const interval = setInterval(updateConnectionState, 1000)

    return () => clearInterval(interval)
  }, [service])

  // Cleanup on unmount or token change
  useEffect(() => {
    return () => {
      if (!accessToken) {
        disconnectUnifiedWebSocket()
        setService(null)
        setIsConnected(false)
        setIsHealthy(false)
        setConnectionStatus(ConnectionStatus.DISCONNECTED)
      }
    }
  }, [accessToken])

  // Connection methods
  const connect = useCallback(async () => {
    if (service) {
      await service.connect()
    }
  }, [service])

  const disconnect = useCallback(() => {
    if (service) {
      service.disconnect()
    }
  }, [service])

  // Subscription methods
  const subscribe = useCallback(async (eventTypes: EventType[]) => {
    if (service) {
      await service.subscribeToEvents(eventTypes)
    }
  }, [service])

  const unsubscribe = useCallback(async (eventTypes: EventType[]) => {
    if (service) {
      await service.unsubscribeFromEvents(eventTypes)
    }
  }, [service])

  const getSubscriptions = useCallback(() => {
    return service ? service.getSubscriptions() : []
  }, [service])

  // Event handling methods
  const registerEventHandler = useCallback((id: string, eventTypes: EventType[], handler: (data: any) => void) => {
    if (service) {
      service.registerEventHandler(id, eventTypes, handler)
      eventHandlersRef.current.set(id, { eventTypes, handler })
    }
  }, [service])

  const unregisterEventHandler = useCallback((id: string) => {
    if (service) {
      service.unregisterEventHandler(id)
      eventHandlersRef.current.delete(id)
    }
  }, [service])

  // Messaging methods
  const sendMessage = useCallback((message: any) => {
    return service ? service.sendMessage(message) : false
  }, [service])

  // Health and stats methods
  const performHealthCheck = useCallback(() => {
    if (service) {
      service.performHealthCheck()
    }
  }, [service])

  const getConnectionStats = useCallback(() => {
    return service ? service.getConnectionStats() : null
  }, [service])

  return {
    isConnected,
    isHealthy,
    connectionStatus,
    connectionHealth,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    getSubscriptions,
    registerEventHandler,
    unregisterEventHandler,
    sendMessage,
    performHealthCheck,
    getConnectionStats,
    service
  }
}

// Specialized hooks for common use cases

export const useHealthWebSocket = (onHealthUpdate?: (data: any) => void, onHealthAlert?: (data: any) => void) => {
  const websocket = useUnifiedWebSocket()

  useEffect(() => {
    if (websocket.service && (onHealthUpdate || onHealthAlert)) {
      const handlerId = 'health-events'
      
      websocket.registerEventHandler(handlerId, [
        EventType.HEALTH_UPDATE,
        EventType.HEALTH_ALERT,
        EventType.FORWARDER_STATUS_CHANGE
      ], (data) => {
        // This would need to be enhanced to differentiate between event types
        onHealthUpdate?.(data)
        onHealthAlert?.(data)
      })

      websocket.subscribe([
        EventType.HEALTH_UPDATE,
        EventType.HEALTH_ALERT,
        EventType.FORWARDER_STATUS_CHANGE
      ])

      return () => {
        websocket.unregisterEventHandler(handlerId)
      }
    }
  }, [websocket, onHealthUpdate, onHealthAlert])

  return websocket
}

export const useDNSWebSocket = (onDNSChange?: (data: any) => void) => {
  const websocket = useUnifiedWebSocket()

  useEffect(() => {
    if (websocket.service && onDNSChange) {
      const handlerId = 'dns-events'
      
      websocket.registerEventHandler(handlerId, [
        EventType.ZONE_CREATED,
        EventType.ZONE_UPDATED,
        EventType.ZONE_DELETED,
        EventType.RECORD_CREATED,
        EventType.RECORD_UPDATED,
        EventType.RECORD_DELETED
      ], onDNSChange)

      websocket.subscribe([
        EventType.ZONE_CREATED,
        EventType.ZONE_UPDATED,
        EventType.ZONE_DELETED,
        EventType.RECORD_CREATED,
        EventType.RECORD_UPDATED,
        EventType.RECORD_DELETED
      ])

      return () => {
        websocket.unregisterEventHandler(handlerId)
      }
    }
  }, [websocket, onDNSChange])

  return websocket
}

export const useSecurityWebSocket = (onSecurityEvent?: (data: any) => void) => {
  const websocket = useUnifiedWebSocket()

  useEffect(() => {
    if (websocket.service && onSecurityEvent) {
      const handlerId = 'security-events'
      
      websocket.registerEventHandler(handlerId, [
        EventType.SECURITY_ALERT,
        EventType.RPZ_UPDATE,
        EventType.THREAT_DETECTED
      ], onSecurityEvent)

      websocket.subscribe([
        EventType.SECURITY_ALERT,
        EventType.RPZ_UPDATE,
        EventType.THREAT_DETECTED
      ])

      return () => {
        websocket.unregisterEventHandler(handlerId)
      }
    }
  }, [websocket, onSecurityEvent])

  return websocket
}

export const useSystemWebSocket = (onSystemEvent?: (data: any) => void) => {
  const websocket = useUnifiedWebSocket()

  useEffect(() => {
    if (websocket.service && onSystemEvent) {
      const handlerId = 'system-events'
      
      websocket.registerEventHandler(handlerId, [
        EventType.SYSTEM_STATUS,
        EventType.BIND_RELOAD,
        EventType.CONFIG_CHANGE
      ], onSystemEvent)

      websocket.subscribe([
        EventType.SYSTEM_STATUS,
        EventType.BIND_RELOAD,
        EventType.CONFIG_CHANGE
      ])

      return () => {
        websocket.unregisterEventHandler(handlerId)
      }
    }
  }, [websocket, onSystemEvent])

  return websocket
}

export default useUnifiedWebSocket