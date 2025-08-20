import React, { createContext, useContext, useReducer, useEffect, ReactNode, useCallback } from 'react'
import { useWebSocketService, ConnectionType, EventType } from '@/hooks/useWebSocket'
import { WebSocketMessage } from '@/services/websocketService'
import { toast } from 'react-toastify'

interface SystemEvent {
  id: string
  type: string
  data: any
  timestamp: string
  acknowledged: boolean
  severity: 'info' | 'warning' | 'error' | 'success'
}

interface ConnectionStats {
  total_users: number
  total_connections: number
  total_messages_sent: number
  broadcasting: boolean
  connection_types: Record<string, number>
  queue_size: number
  active_tasks: number
  supported_events: string[]
  supported_connection_types: string[]
}

interface RealTimeEventState {
  // Connection status
  isConnected: boolean
  connectionStatus: string
  reconnectAttempts: number
  
  // Events
  events: SystemEvent[]
  unreadCount: number
  
  // System status
  systemStatus: any
  connectionStats: ConnectionStats | null
  
  // DNS events
  dnsEvents: SystemEvent[]
  
  // Security events
  securityEvents: SystemEvent[]
  
  // Health events
  healthEvents: SystemEvent[]
}

type RealTimeEventAction =
  | { type: 'SET_CONNECTION_STATUS'; payload: { isConnected: boolean; status: string; attempts: number } }
  | { type: 'ADD_EVENT'; payload: SystemEvent }
  | { type: 'ACKNOWLEDGE_EVENT'; payload: string }
  | { type: 'CLEAR_EVENTS' }
  | { type: 'SET_SYSTEM_STATUS'; payload: any }
  | { type: 'SET_CONNECTION_STATS'; payload: ConnectionStats }
  | { type: 'ADD_DNS_EVENT'; payload: SystemEvent }
  | { type: 'ADD_SECURITY_EVENT'; payload: SystemEvent }
  | { type: 'ADD_HEALTH_EVENT'; payload: SystemEvent }

const initialState: RealTimeEventState = {
  isConnected: false,
  connectionStatus: 'disconnected',
  reconnectAttempts: 0,
  events: [],
  unreadCount: 0,
  systemStatus: null,
  connectionStats: null,
  dnsEvents: [],
  securityEvents: [],
  healthEvents: []
}

function realTimeEventReducer(state: RealTimeEventState, action: RealTimeEventAction): RealTimeEventState {
  switch (action.type) {
    case 'SET_CONNECTION_STATUS':
      return {
        ...state,
        isConnected: action.payload.isConnected,
        connectionStatus: action.payload.status,
        reconnectAttempts: action.payload.attempts
      }
    
    case 'ADD_EVENT':
      return {
        ...state,
        events: [action.payload, ...state.events.slice(0, 99)], // Keep last 100 events
        unreadCount: state.unreadCount + 1
      }
    
    case 'ACKNOWLEDGE_EVENT':
      return {
        ...state,
        events: state.events.map(event =>
          event.id === action.payload
            ? { ...event, acknowledged: true }
            : event
        ),
        unreadCount: Math.max(0, state.unreadCount - 1)
      }
    
    case 'CLEAR_EVENTS':
      return {
        ...state,
        events: [],
        unreadCount: 0
      }
    
    case 'SET_SYSTEM_STATUS':
      return {
        ...state,
        systemStatus: action.payload
      }
    
    case 'SET_CONNECTION_STATS':
      return {
        ...state,
        connectionStats: action.payload
      }
    
    case 'ADD_DNS_EVENT':
      return {
        ...state,
        dnsEvents: [action.payload, ...state.dnsEvents.slice(0, 49)] // Keep last 50 DNS events
      }
    
    case 'ADD_SECURITY_EVENT':
      return {
        ...state,
        securityEvents: [action.payload, ...state.securityEvents.slice(0, 49)] // Keep last 50 security events
      }
    
    case 'ADD_HEALTH_EVENT':
      return {
        ...state,
        healthEvents: [action.payload, ...state.healthEvents.slice(0, 49)] // Keep last 50 health events
      }
    
    default:
      return state
  }
}

interface RealTimeEventContextType extends RealTimeEventState {
  acknowledgeEvent: (eventId: string) => void
  clearEvents: () => void
  getConnectionStats: () => void
  sendMessage: (message: any) => boolean
}

const RealTimeEventContext = createContext<RealTimeEventContextType | undefined>(undefined)

interface RealTimeEventProviderProps {
  children: ReactNode
  userId: string
  connectionType?: ConnectionType
}

export const RealTimeEventProvider: React.FC<RealTimeEventProviderProps> = ({ 
  children, 
  userId, 
  connectionType = ConnectionType.ADMIN 
}) => {
  const [state, dispatch] = useReducer(realTimeEventReducer, initialState)

  // WebSocket connection for real-time events
  const {
    isConnected,
    connectionStatus,
    reconnectAttempts,
    sendMessage,
    subscribe,
    getStats
  } = useWebSocketService(connectionType, userId, {
    onConnect: () => {
      console.log('Real-time event WebSocket connected')
      toast.success('Connected to real-time updates', { autoClose: 2000 })
    },
    onDisconnect: () => {
      console.log('Real-time event WebSocket disconnected')
      toast.warning('Disconnected from real-time updates', { autoClose: 3000 })
    },
    onError: (error) => {
      console.error('Real-time event WebSocket error:', error)
      toast.error('Connection error - some features may not work', { autoClose: 5000 })
    }
  })

  // Update connection status in state
  useEffect(() => {
    dispatch({
      type: 'SET_CONNECTION_STATUS',
      payload: { isConnected, status: connectionStatus, attempts: reconnectAttempts }
    })
  }, [isConnected, connectionStatus, reconnectAttempts])

  // Create event from WebSocket message
  const createEvent = useCallback((message: WebSocketMessage, severity: SystemEvent['severity'] = 'info'): SystemEvent => {
    return {
      id: `${message.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: message.type,
      data: message.data,
      timestamp: message.timestamp,
      acknowledged: false,
      severity
    }
  }, [])

  // Set up event handlers
  useEffect(() => {
    // System events
    subscribe(EventType.SYSTEM_STATUS, (data) => {
      dispatch({ type: 'SET_SYSTEM_STATUS', payload: data })
    })

    subscribe(EventType.CONFIG_CHANGE, (data) => {
      const event = createEvent({ type: EventType.CONFIG_CHANGE, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_EVENT', payload: event })
      toast.info('Configuration updated', { autoClose: 3000 })
    })

    subscribe(EventType.BIND_RELOAD, (data) => {
      const event = createEvent({ type: EventType.BIND_RELOAD, data, timestamp: new Date().toISOString() }, 'success')
      dispatch({ type: 'ADD_EVENT', payload: event })
      toast.success('DNS server reloaded', { autoClose: 3000 })
    })

    // DNS events
    subscribe(EventType.ZONE_CREATED, (data) => {
      const event = createEvent({ type: EventType.ZONE_CREATED, data, timestamp: new Date().toISOString() }, 'success')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
      toast.success(`DNS zone "${data.name}" created`, { autoClose: 3000 })
    })

    subscribe(EventType.ZONE_UPDATED, (data) => {
      const event = createEvent({ type: EventType.ZONE_UPDATED, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
      toast.info(`DNS zone "${data.name}" updated`, { autoClose: 3000 })
    })

    subscribe(EventType.ZONE_DELETED, (data) => {
      const event = createEvent({ type: EventType.ZONE_DELETED, data, timestamp: new Date().toISOString() }, 'warning')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
      toast.warning(`DNS zone "${data.name}" deleted`, { autoClose: 3000 })
    })

    subscribe(EventType.RECORD_CREATED, (data) => {
      const event = createEvent({ type: EventType.RECORD_CREATED, data, timestamp: new Date().toISOString() }, 'success')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
    })

    subscribe(EventType.RECORD_UPDATED, (data) => {
      const event = createEvent({ type: EventType.RECORD_UPDATED, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
    })

    subscribe(EventType.RECORD_DELETED, (data) => {
      const event = createEvent({ type: EventType.RECORD_DELETED, data, timestamp: new Date().toISOString() }, 'warning')
      dispatch({ type: 'ADD_DNS_EVENT', payload: event })
    })

    // Security events
    subscribe(EventType.SECURITY_ALERT, (data) => {
      const event = createEvent({ type: EventType.SECURITY_ALERT, data, timestamp: new Date().toISOString() }, 'error')
      dispatch({ type: 'ADD_SECURITY_EVENT', payload: event })
      toast.error(`Security Alert: ${data.message}`, { autoClose: 5000 })
    })

    subscribe(EventType.RPZ_UPDATE, (data) => {
      const event = createEvent({ type: EventType.RPZ_UPDATE, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_SECURITY_EVENT', payload: event })
      toast.info('Security rules updated', { autoClose: 3000 })
    })

    subscribe(EventType.THREAT_DETECTED, (data) => {
      const event = createEvent({ type: EventType.THREAT_DETECTED, data, timestamp: new Date().toISOString() }, 'error')
      dispatch({ type: 'ADD_SECURITY_EVENT', payload: event })
      toast.error(`Threat detected: ${data.threat_type}`, { autoClose: 5000 })
    })

    // Health events
    subscribe(EventType.HEALTH_ALERT, (data) => {
      const event = createEvent({ type: EventType.HEALTH_ALERT, data, timestamp: new Date().toISOString() }, 'warning')
      dispatch({ type: 'ADD_HEALTH_EVENT', payload: event })
      toast.warning(`Health Alert: ${data.message}`, { autoClose: 4000 })
    })

    subscribe(EventType.FORWARDER_STATUS_CHANGE, (data) => {
      const event = createEvent({ type: EventType.FORWARDER_STATUS_CHANGE, data, timestamp: new Date().toISOString() }, 
        data.new_status === 'healthy' ? 'success' : 'warning')
      dispatch({ type: 'ADD_HEALTH_EVENT', payload: event })
      
      if (data.new_status !== 'healthy') {
        toast.warning(`Forwarder ${data.forwarder_id} status: ${data.new_status}`, { autoClose: 4000 })
      }
    })

    // User events
    subscribe(EventType.USER_LOGIN, (data) => {
      const event = createEvent({ type: EventType.USER_LOGIN, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_EVENT', payload: event })
    })

    subscribe(EventType.USER_LOGOUT, (data) => {
      const event = createEvent({ type: EventType.USER_LOGOUT, data, timestamp: new Date().toISOString() }, 'info')
      dispatch({ type: 'ADD_EVENT', payload: event })
    })

    // Connection stats
    subscribe('stats', (data) => {
      dispatch({ type: 'SET_CONNECTION_STATS', payload: data })
    })

  }, [subscribe, createEvent])

  const acknowledgeEvent = useCallback((eventId: string) => {
    dispatch({ type: 'ACKNOWLEDGE_EVENT', payload: eventId })
  }, [])

  const clearEvents = useCallback(() => {
    dispatch({ type: 'CLEAR_EVENTS' })
  }, [])

  const getConnectionStats = useCallback(() => {
    getStats()
  }, [getStats])

  const contextValue: RealTimeEventContextType = {
    ...state,
    acknowledgeEvent,
    clearEvents,
    getConnectionStats,
    sendMessage
  }

  return (
    <RealTimeEventContext.Provider value={contextValue}>
      {children}
    </RealTimeEventContext.Provider>
  )
}

export const useRealTimeEvents = () => {
  const context = useContext(RealTimeEventContext)
  if (context === undefined) {
    throw new Error('useRealTimeEvents must be used within a RealTimeEventProvider')
  }
  return context
}

// Specialized hooks for different event types
export const useDNSEvents = () => {
  const { dnsEvents, acknowledgeEvent } = useRealTimeEvents()
  return { dnsEvents, acknowledgeEvent }
}

export const useSecurityEvents = () => {
  const { securityEvents, acknowledgeEvent } = useRealTimeEvents()
  return { securityEvents, acknowledgeEvent }
}

export const useHealthEvents = () => {
  const { healthEvents, acknowledgeEvent } = useRealTimeEvents()
  return { healthEvents, acknowledgeEvent }
}

export const useSystemStatus = () => {
  const { systemStatus, connectionStats, isConnected, getConnectionStats } = useRealTimeEvents()
  return { systemStatus, connectionStats, isConnected, getConnectionStats }
}