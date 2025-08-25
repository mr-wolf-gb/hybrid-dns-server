/**
 * Unified WebSocket Context for managing single WebSocket connection
 * Replaces the old multi-connection WebSocket context
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { toast } from 'react-toastify'
import { 
  UnifiedWebSocketService, 
  getUnifiedWebSocketService, 
  disconnectUnifiedWebSocket,
  EventType,
  WebSocketMessage 
} from '../services/UnifiedWebSocketService'
import { EventManager, getDefaultEventManager, EventHandlerRegistration } from '../services/EventManager'
import { ConnectionStatus, ConnectionHealth } from '../services/ConnectionHealthManager'

// Notification throttling to prevent spam
const notificationThrottle = new Map<string, number>()
const THROTTLE_DURATION = 5000 // 5 seconds

const shouldShowNotification = (type: string): boolean => {
  const now = Date.now()
  const lastShown = notificationThrottle.get(type) || 0

  if (now - lastShown > THROTTLE_DURATION) {
    notificationThrottle.set(type, now)
    return true
  }
  return false
}

interface UnifiedWebSocketContextType {
  // Connection state
  isConnected: boolean
  isHealthy: boolean
  connectionStatus: ConnectionStatus
  connectionHealth: ConnectionHealth
  
  // Connection management
  connect: () => Promise<void>
  disconnect: () => void
  
  // Event subscription
  subscribe: (eventTypes: EventType[]) => Promise<void>
  unsubscribe: (eventTypes: EventType[]) => Promise<void>
  getSubscriptions: () => EventType[]
  
  // Event handling
  registerEventHandler: (registration: EventHandlerRegistration) => void
  unregisterEventHandler: (id: string) => void
  
  // Messaging
  sendMessage: (message: any) => boolean
  
  // Health and statistics
  performHealthCheck: () => void
  getConnectionStats: () => any
  getEventStats: () => any
  
  // Service instances (for advanced usage)
  webSocketService: UnifiedWebSocketService | null
  eventManager: EventManager
}

const UnifiedWebSocketContext = createContext<UnifiedWebSocketContextType | undefined>(undefined)

interface UnifiedWebSocketProviderProps {
  children: ReactNode
}

export const UnifiedWebSocketProvider: React.FC<UnifiedWebSocketProviderProps> = ({ children }) => {
  const { user, accessToken } = useAuth()
  const [webSocketService, setWebSocketService] = useState<UnifiedWebSocketService | null>(null)
  const [eventManager] = useState(() => getDefaultEventManager())
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

  // Global message handler with notification system
  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Handle global notifications with throttling
    switch (message.type) {
      case EventType.HEALTH_ALERT:
        if (message.data?.severity === 'critical' && shouldShowNotification('health_alert_critical')) {
          toast.error(`Health Alert: ${message.data?.message || 'Critical system issue detected'}`)
        }
        break
      
      case EventType.SECURITY_ALERT:
        if (shouldShowNotification('security_alert')) {
          toast.error(`Security Alert: ${message.data?.message || 'Security threat detected'}`)
        }
        break
      
      case EventType.BIND_RELOAD:
        if (shouldShowNotification('bind_reload')) {
          toast.success('DNS configuration reloaded successfully')
        }
        break
      
      case EventType.SYSTEM_STATUS:
        if (message.data?.bind9_running === false && shouldShowNotification('bind9_down')) {
          toast.error('BIND9 service is not running')
        }
        break
      
      case EventType.SESSION_EXPIRED:
        toast.error('Session expired, please log in again')
        // The service will handle the redirect
        break
    }

    // Pass message to event manager for processing
    eventManager.handleEvent(message)
  }, [eventManager])

  // Connection event handlers
  const handleConnect = useCallback(() => {
    setIsConnected(true)
    if (shouldShowNotification('connection_established')) {
      toast.success('Real-time connection established')
    }
  }, [])

  const handleDisconnect = useCallback(() => {
    setIsConnected(false)
    if (shouldShowNotification('connection_lost')) {
      toast.error('Real-time connection lost')
    }
  }, [])

  const handleError = useCallback((error: Event) => {
    console.error('WebSocket error:', error)
    if (shouldShowNotification('connection_error')) {
      toast.error('WebSocket connection error')
    }
  }, [])

  // Initialize WebSocket service when token is available
  useEffect(() => {
    if (accessToken && user && !webSocketService) {
      const service = getUnifiedWebSocketService(accessToken, {
        onMessage: handleMessage,
        onConnect: handleConnect,
        onDisconnect: handleDisconnect,
        onError: handleError
      })

      setWebSocketService(service)

      // Auto-connect
      service.connect().catch(error => {
        console.error('Failed to connect WebSocket:', error)
      })
    }
  }, [accessToken, user, webSocketService, handleMessage, handleConnect, handleDisconnect, handleError])

  // Update connection state periodically
  useEffect(() => {
    if (!webSocketService) return

    const updateConnectionState = () => {
      setIsConnected(webSocketService.isConnectionOpen())
      setIsHealthy(webSocketService.isConnectionHealthy())
      setConnectionStatus(webSocketService.getConnectionStatus())
      setConnectionHealth(webSocketService.getConnectionHealth())
    }

    // Initial update
    updateConnectionState()

    // Set up periodic updates
    const interval = setInterval(updateConnectionState, 2000)

    return () => clearInterval(interval)
  }, [webSocketService])

  // Cleanup when user logs out
  useEffect(() => {
    if (!user || !accessToken) {
      if (webSocketService) {
        webSocketService.disconnect()
      }
      disconnectUnifiedWebSocket()
      setWebSocketService(null)
      setIsConnected(false)
      setIsHealthy(false)
      setConnectionStatus(ConnectionStatus.DISCONNECTED)
    }
  }, [user, accessToken, webSocketService])

  // Context methods
  const connect = useCallback(async () => {
    if (webSocketService) {
      await webSocketService.connect()
    }
  }, [webSocketService])

  const disconnect = useCallback(() => {
    if (webSocketService) {
      webSocketService.disconnect()
    }
  }, [webSocketService])

  const subscribe = useCallback(async (eventTypes: EventType[]) => {
    if (webSocketService) {
      await webSocketService.subscribeToEvents(eventTypes)
    }
  }, [webSocketService])

  const unsubscribe = useCallback(async (eventTypes: EventType[]) => {
    if (webSocketService) {
      await webSocketService.unsubscribeFromEvents(eventTypes)
    }
  }, [webSocketService])

  const getSubscriptions = useCallback(() => {
    return webSocketService ? webSocketService.getSubscriptions() : []
  }, [webSocketService])

  const registerEventHandler = useCallback((registration: EventHandlerRegistration) => {
    eventManager.registerHandler(registration)
  }, [eventManager])

  const unregisterEventHandler = useCallback((id: string) => {
    eventManager.unregisterHandler(id)
  }, [eventManager])

  const sendMessage = useCallback((message: any) => {
    return webSocketService ? webSocketService.sendMessage(message) : false
  }, [webSocketService])

  const performHealthCheck = useCallback(() => {
    if (webSocketService) {
      webSocketService.performHealthCheck()
    }
  }, [webSocketService])

  const getConnectionStats = useCallback(() => {
    return webSocketService ? webSocketService.getConnectionStats() : null
  }, [webSocketService])

  const getEventStats = useCallback(() => {
    return eventManager.getStats()
  }, [eventManager])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (webSocketService) {
        webSocketService.disconnect()
      }
      disconnectUnifiedWebSocket()
    }
  }, [webSocketService])

  const contextValue: UnifiedWebSocketContextType = {
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
    getEventStats,
    webSocketService,
    eventManager
  }

  return (
    <UnifiedWebSocketContext.Provider value={contextValue}>
      {children}
    </UnifiedWebSocketContext.Provider>
  )
}

export const useUnifiedWebSocketContext = (): UnifiedWebSocketContextType => {
  const context = useContext(UnifiedWebSocketContext)
  if (!context) {
    throw new Error('useUnifiedWebSocketContext must be used within a UnifiedWebSocketProvider')
  }
  return context
}

// Convenience hooks for specific event types
export const useHealthEvents = (onHealthUpdate?: (data: any) => void, onHealthAlert?: (data: any) => void) => {
  const { registerEventHandler, unregisterEventHandler, subscribe } = useUnifiedWebSocketContext()

  useEffect(() => {
    const handlerId = 'health-events-hook'
    
    if (onHealthUpdate || onHealthAlert) {
      registerEventHandler({
        id: handlerId,
        eventTypes: [EventType.HEALTH_UPDATE, EventType.HEALTH_ALERT, EventType.FORWARDER_STATUS_CHANGE],
        handler: async (event: WebSocketMessage) => {
          switch (event.type) {
            case EventType.HEALTH_UPDATE:
            case EventType.FORWARDER_STATUS_CHANGE:
              onHealthUpdate?.(event.data)
              break
            case EventType.HEALTH_ALERT:
              onHealthAlert?.(event.data)
              break
          }
        },
        priority: 10
      })

      subscribe([EventType.HEALTH_UPDATE, EventType.HEALTH_ALERT, EventType.FORWARDER_STATUS_CHANGE])
    }

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [registerEventHandler, unregisterEventHandler, subscribe, onHealthUpdate, onHealthAlert])
}

export const useDNSEvents = (onDNSChange?: (data: any) => void) => {
  const { registerEventHandler, unregisterEventHandler, subscribe } = useUnifiedWebSocketContext()

  useEffect(() => {
    const handlerId = 'dns-events-hook'
    
    if (onDNSChange) {
      registerEventHandler({
        id: handlerId,
        eventTypes: [
          EventType.ZONE_CREATED,
          EventType.ZONE_UPDATED,
          EventType.ZONE_DELETED,
          EventType.RECORD_CREATED,
          EventType.RECORD_UPDATED,
          EventType.RECORD_DELETED
        ],
        handler: async (event: WebSocketMessage) => {
          onDNSChange(event.data)
        },
        priority: 5
      })

      subscribe([
        EventType.ZONE_CREATED,
        EventType.ZONE_UPDATED,
        EventType.ZONE_DELETED,
        EventType.RECORD_CREATED,
        EventType.RECORD_UPDATED,
        EventType.RECORD_DELETED
      ])
    }

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [registerEventHandler, unregisterEventHandler, subscribe, onDNSChange])
}

export const useSecurityEvents = (onSecurityEvent?: (data: any) => void) => {
  const { registerEventHandler, unregisterEventHandler, subscribe } = useUnifiedWebSocketContext()

  useEffect(() => {
    const handlerId = 'security-events-hook'
    
    if (onSecurityEvent) {
      registerEventHandler({
        id: handlerId,
        eventTypes: [EventType.SECURITY_ALERT, EventType.RPZ_UPDATE, EventType.THREAT_DETECTED],
        handler: async (event: WebSocketMessage) => {
          onSecurityEvent(event.data)
        },
        priority: 15 // High priority for security events
      })

      subscribe([EventType.SECURITY_ALERT, EventType.RPZ_UPDATE, EventType.THREAT_DETECTED])
    }

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [registerEventHandler, unregisterEventHandler, subscribe, onSecurityEvent])
}

export const useSystemEvents = (onSystemEvent?: (data: any) => void) => {
  const { registerEventHandler, unregisterEventHandler, subscribe } = useUnifiedWebSocketContext()

  useEffect(() => {
    const handlerId = 'system-events-hook'
    
    if (onSystemEvent) {
      registerEventHandler({
        id: handlerId,
        eventTypes: [EventType.SYSTEM_STATUS, EventType.BIND_RELOAD, EventType.CONFIG_CHANGE],
        handler: async (event: WebSocketMessage) => {
          onSystemEvent(event.data)
        },
        priority: 8
      })

      subscribe([EventType.SYSTEM_STATUS, EventType.BIND_RELOAD, EventType.CONFIG_CHANGE])
    }

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [registerEventHandler, unregisterEventHandler, subscribe, onSystemEvent])
}

export default UnifiedWebSocketContext