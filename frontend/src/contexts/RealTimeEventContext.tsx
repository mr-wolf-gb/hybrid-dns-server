import React, { createContext, useContext, useReducer, useEffect, ReactNode, useCallback } from 'react'
import { useWebSocketContext, WebSocketMessage } from './WebSocketContext'
import { useAuth } from './AuthContext'
import { toast } from 'react-toastify'

// Event types enum for consistency
export enum EventType {
  // Health monitoring events
  HEALTH_UPDATE = 'health_update',
  HEALTH_ALERT = 'health_alert',
  FORWARDER_STATUS_CHANGE = 'forwarder_status_change',

  // DNS zone events
  ZONE_CREATED = 'zone_created',
  ZONE_UPDATED = 'zone_updated',
  ZONE_DELETED = 'zone_deleted',
  RECORD_CREATED = 'record_created',
  RECORD_UPDATED = 'record_updated',
  RECORD_DELETED = 'record_deleted',

  // Security events
  SECURITY_ALERT = 'security_alert',
  RPZ_UPDATE = 'rpz_update',
  THREAT_DETECTED = 'threat_detected',

  // System events
  SYSTEM_STATUS = 'system_status',
  BIND_RELOAD = 'bind_reload',
  CONFIG_CHANGE = 'config_change',

  // User events
  USER_LOGIN = 'user_login',
  USER_LOGOUT = 'user_logout',
  SESSION_EXPIRED = 'session_expired',

  // Connection events
  CONNECTION_ESTABLISHED = 'connection_established',
  SUBSCRIPTION_UPDATED = 'subscription_updated'
}

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
}

export const RealTimeEventProvider: React.FC<RealTimeEventProviderProps> = ({ children }) => {
  const { user } = useAuth()
  const [state, dispatch] = useReducer(realTimeEventReducer, initialState)
  
  // Use the existing WebSocket context instead of creating a new connection
  const { 
    isConnected, 
    isConnecting, 
    error,
    registerEventHandler, 
    unregisterEventHandler,
    sendMessage,
    getConnectionStats
  } = useWebSocketContext()

  // Update connection status in state
  useEffect(() => {
    dispatch({
      type: 'SET_CONNECTION_STATUS',
      payload: { 
        isConnected, 
        status: isConnected ? 'connected' : isConnecting ? 'connecting' : 'disconnected', 
        attempts: 0 
      }
    })
  }, [isConnected, isConnecting])

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

  // Set up event handlers using the WebSocket context
  useEffect(() => {
    if (!user) return;

    const handlerId = 'realtime-event-context';

    // Register a single event handler for all event types
    registerEventHandler(handlerId, ['*'], (message: WebSocketMessage) => {
      const eventType = message.type;
      const data = message.data;

      // Handle different event types
      switch (eventType) {
        case EventType.SYSTEM_STATUS:
          dispatch({ type: 'SET_SYSTEM_STATUS', payload: data });
          break;

        case EventType.CONFIG_CHANGE:
          const configEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_EVENT', payload: configEvent });
          toast.info('Configuration updated', { autoClose: 3000 });
          break;

        case EventType.BIND_RELOAD:
          const reloadEvent = createEvent(message, 'success');
          dispatch({ type: 'ADD_EVENT', payload: reloadEvent });
          toast.success('DNS server reloaded', { autoClose: 3000 });
          break;

        // DNS events
        case EventType.ZONE_CREATED:
          const zoneCreatedEvent = createEvent(message, 'success');
          dispatch({ type: 'ADD_DNS_EVENT', payload: zoneCreatedEvent });
          toast.success(`DNS zone "${data?.name}" created`, { autoClose: 3000 });
          break;

        case EventType.ZONE_UPDATED:
          const zoneUpdatedEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_DNS_EVENT', payload: zoneUpdatedEvent });
          toast.info(`DNS zone "${data?.name}" updated`, { autoClose: 3000 });
          break;

        case EventType.ZONE_DELETED:
          const zoneDeletedEvent = createEvent(message, 'warning');
          dispatch({ type: 'ADD_DNS_EVENT', payload: zoneDeletedEvent });
          toast.warning(`DNS zone "${data?.name}" deleted`, { autoClose: 3000 });
          break;

        case EventType.RECORD_CREATED:
          const recordCreatedEvent = createEvent(message, 'success');
          dispatch({ type: 'ADD_DNS_EVENT', payload: recordCreatedEvent });
          break;

        case EventType.RECORD_UPDATED:
          const recordUpdatedEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_DNS_EVENT', payload: recordUpdatedEvent });
          break;

        case EventType.RECORD_DELETED:
          const recordDeletedEvent = createEvent(message, 'warning');
          dispatch({ type: 'ADD_DNS_EVENT', payload: recordDeletedEvent });
          break;

        // Security events
        case EventType.SECURITY_ALERT:
          const securityEvent = createEvent(message, 'error');
          dispatch({ type: 'ADD_SECURITY_EVENT', payload: securityEvent });
          toast.error(`Security Alert: ${data?.message}`, { autoClose: 5000 });
          break;

        case EventType.RPZ_UPDATE:
          const rpzEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_SECURITY_EVENT', payload: rpzEvent });
          toast.info('Security rules updated', { autoClose: 3000 });
          break;

        case EventType.THREAT_DETECTED:
          const threatEvent = createEvent(message, 'error');
          dispatch({ type: 'ADD_SECURITY_EVENT', payload: threatEvent });
          toast.error(`Threat detected: ${data?.threat_type}`, { autoClose: 5000 });
          break;

        // Health events
        case EventType.HEALTH_ALERT:
          const healthEvent = createEvent(message, 'warning');
          dispatch({ type: 'ADD_HEALTH_EVENT', payload: healthEvent });
          toast.warning(`Health Alert: ${data?.message}`, { autoClose: 4000 });
          break;

        case EventType.FORWARDER_STATUS_CHANGE:
          const forwarderEvent = createEvent(message, data?.new_status === 'healthy' ? 'success' : 'warning');
          dispatch({ type: 'ADD_HEALTH_EVENT', payload: forwarderEvent });
          
          if (data?.new_status !== 'healthy') {
            toast.warning(`Forwarder ${data?.forwarder_id} status: ${data?.new_status}`, { autoClose: 4000 });
          }
          break;

        // User events
        case EventType.USER_LOGIN:
          const loginEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_EVENT', payload: loginEvent });
          break;

        case EventType.USER_LOGOUT:
          const logoutEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_EVENT', payload: logoutEvent });
          break;

        // Connection stats
        case 'stats':
          dispatch({ type: 'SET_CONNECTION_STATS', payload: data });
          break;

        default:
          // Handle unknown events as general events
          const unknownEvent = createEvent(message, 'info');
          dispatch({ type: 'ADD_EVENT', payload: unknownEvent });
          break;
      }
    });

    // Cleanup on unmount or user change
    return () => {
      unregisterEventHandler(handlerId);
    };
  }, [user, registerEventHandler, unregisterEventHandler, createEvent])

  const acknowledgeEvent = useCallback((eventId: string) => {
    dispatch({ type: 'ACKNOWLEDGE_EVENT', payload: eventId })
  }, [])

  const clearEvents = useCallback(() => {
    dispatch({ type: 'CLEAR_EVENTS' })
  }, [])

  const getConnectionStatsCallback = useCallback(() => {
    const stats = getConnectionStats();
    if (stats) {
      dispatch({ type: 'SET_CONNECTION_STATS', payload: stats });
    }
  }, [getConnectionStats])

  const contextValue: RealTimeEventContextType = {
    ...state,
    acknowledgeEvent,
    clearEvents,
    getConnectionStats: getConnectionStatsCallback,
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