import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react'
import { useWebSocketContext } from './WebSocketContext'

interface HealthAlert {
  id: string
  type: 'health_status' | 'performance'
  level: 'warning' | 'critical'
  forwarder_id?: number
  forwarder_name?: string
  message: string
  details: any
  created_at: string
  acknowledged: boolean
}

interface ForwarderHealthStatus {
  id: number
  name: string
  type: string
  is_active: boolean
  health_check_enabled: boolean
  status: string
  healthy_servers: number
  total_servers: number
  last_checked: string | null
}

interface HealthSummary {
  total_forwarders: number
  active_forwarders: number
  health_check_enabled: number
  healthy_forwarders: number
  unhealthy_forwarders: number
  degraded_forwarders: number
  unknown_forwarders: number
  last_updated: string
  forwarder_details: ForwarderHealthStatus[]
}

interface PerformanceMetrics {
  period_hours: number
  overall_metrics: {
    total_checks: number
    successful_checks: number
    success_rate: number
    failure_rate: number
    avg_response_time: number | null
    min_response_time: number | null
    max_response_time: number | null
    median_response_time?: number | null
    p95_response_time?: number | null
    p99_response_time?: number | null
  }
  forwarder_metrics: Array<{
    forwarder_id: number
    total_checks: number
    successful_checks: number
    success_rate: number
    avg_response_time: number | null
    performance_grade: string
  }>
  performance_grade: string
  generated_at: string
}

interface HealthMonitoringState {
  healthSummary: HealthSummary | null
  performanceMetrics: PerformanceMetrics | null
  alerts: HealthAlert[]
  isConnected: boolean
  connectionStatus: string
  lastUpdate: string | null
}

type HealthMonitoringAction =
  | { type: 'SET_HEALTH_SUMMARY'; payload: HealthSummary }
  | { type: 'SET_PERFORMANCE_METRICS'; payload: PerformanceMetrics }
  | { type: 'SET_ALERTS'; payload: HealthAlert[] }
  | { type: 'ADD_ALERT'; payload: HealthAlert }
  | { type: 'ACKNOWLEDGE_ALERT'; payload: string }
  | { type: 'SET_CONNECTION_STATUS'; payload: { isConnected: boolean; status: string } }
  | { type: 'UPDATE_FORWARDER_STATUS'; payload: { forwarder_id: number; old_status: string; new_status: string } }

const initialState: HealthMonitoringState = {
  healthSummary: {
    total_forwarders: 0,
    active_forwarders: 0,
    health_check_enabled: 0,
    healthy_forwarders: 0,
    unhealthy_forwarders: 0,
    degraded_forwarders: 0,
    unknown_forwarders: 0,
    last_updated: new Date().toISOString(),
    forwarder_details: []
  },
  performanceMetrics: {
    period_hours: 24,
    overall_metrics: {
      total_checks: 0,
      successful_checks: 0,
      success_rate: 0,
      failure_rate: 0,
      avg_response_time: null,
      min_response_time: null,
      max_response_time: null
    },
    forwarder_metrics: [],
    performance_grade: 'unknown',
    generated_at: new Date().toISOString()
  },
  alerts: [],
  isConnected: false,
  connectionStatus: 'disconnected',
  lastUpdate: null
}

function healthMonitoringReducer(state: HealthMonitoringState, action: HealthMonitoringAction): HealthMonitoringState {
  switch (action.type) {
    case 'SET_HEALTH_SUMMARY':
      return {
        ...state,
        healthSummary: action.payload,
        lastUpdate: new Date().toISOString()
      }

    case 'SET_PERFORMANCE_METRICS':
      return {
        ...state,
        performanceMetrics: action.payload,
        lastUpdate: new Date().toISOString()
      }

    case 'SET_ALERTS':
      return {
        ...state,
        alerts: action.payload
      }

    case 'ADD_ALERT':
      return {
        ...state,
        alerts: [action.payload, ...state.alerts]
      }

    case 'ACKNOWLEDGE_ALERT':
      return {
        ...state,
        alerts: state.alerts.map(alert =>
          alert.id === action.payload
            ? { ...alert, acknowledged: true }
            : alert
        )
      }

    case 'SET_CONNECTION_STATUS':
      return {
        ...state,
        isConnected: action.payload.isConnected,
        connectionStatus: action.payload.status
      }

    case 'UPDATE_FORWARDER_STATUS':
      if (!state.healthSummary) return state

      return {
        ...state,
        healthSummary: {
          ...state.healthSummary,
          forwarder_details: state.healthSummary.forwarder_details.map(forwarder =>
            forwarder.id === action.payload.forwarder_id
              ? { ...forwarder, status: action.payload.new_status }
              : forwarder
          )
        }
      }

    default:
      return state
  }
}

interface HealthMonitoringContextType extends HealthMonitoringState {
  acknowledgeAlert: (alertId: string) => void
  refreshHealthData: () => void
}

const HealthMonitoringContext = createContext<HealthMonitoringContextType | undefined>(undefined)

interface HealthMonitoringProviderProps {
  children: ReactNode
  userId: string
}

export const HealthMonitoringProvider: React.FC<HealthMonitoringProviderProps> = ({ children, userId }) => {
  const [state, dispatch] = useReducer(healthMonitoringReducer, initialState)

  // Use existing WebSocket connection from WebSocketContext
  const { healthConnection, registerEventHandler, unregisterEventHandler } = useWebSocketContext()
  const [healthState] = healthConnection
  const isConnected = healthState.isConnected
  const connectionStatus = healthState.isConnected ? 'connected' : healthState.isConnecting ? 'connecting' : 'disconnected'

  // Subscribe to health events using the global event system
  const subscribe = (eventType: string, handler: (data: any) => void) => {
    registerEventHandler(`health-monitoring-${eventType}`, [eventType], (message) => {
      handler(message.data)
    })
  }

  // Set up event handlers
  useEffect(() => {
    const handlerIds = [
      'health-monitoring-health_update',
      'health-monitoring-health_alert',
      'health-monitoring-forwarder_status_change'
    ]

    registerEventHandler('health-monitoring-health_update', ['health_update'], (message) => {
      if (message.data && typeof message.data === 'object') {
        // Ensure forwarder_details is always an array
        const healthData = {
          ...message.data,
          forwarder_details: Array.isArray(message.data.forwarder_details) 
            ? message.data.forwarder_details 
            : []
        }
        dispatch({ type: 'SET_HEALTH_SUMMARY', payload: healthData })
      }
    })

    registerEventHandler('health-monitoring-health_alert', ['health_alert'], (message) => {
      if (message.data && typeof message.data === 'object') {
        dispatch({ type: 'ADD_ALERT', payload: message.data })
      }
    })

    registerEventHandler('health-monitoring-forwarder_status_change', ['forwarder_status_change'], (message) => {
      if (message.data && typeof message.data === 'object' && message.data.forwarder_id) {
        dispatch({ type: 'UPDATE_FORWARDER_STATUS', payload: message.data })
      }
    })

    // Cleanup on unmount
    return () => {
      handlerIds.forEach(id => unregisterEventHandler(id))
    }
  }, [registerEventHandler, unregisterEventHandler])

  // Update connection status in state
  useEffect(() => {
    dispatch({
      type: 'SET_CONNECTION_STATUS',
      payload: { isConnected, status: connectionStatus }
    })
  }, [isConnected, connectionStatus])

  // Load initial data when component mounts
  useEffect(() => {
    refreshHealthData()
  }, [])

  const acknowledgeAlert = (alertId: string) => {
    dispatch({ type: 'ACKNOWLEDGE_ALERT', payload: alertId })
  }

  const refreshHealthData = async () => {
    try {
      // Load health summary
      const healthResponse = await fetch('/api/health/summary')
      if (healthResponse.ok) {
        const healthData = await healthResponse.json()
        // Ensure forwarder_details is always an array
        if (healthData && typeof healthData === 'object') {
          healthData.forwarder_details = Array.isArray(healthData.forwarder_details) 
            ? healthData.forwarder_details 
            : []
          dispatch({ type: 'SET_HEALTH_SUMMARY', payload: healthData })
        }
      } else {
        // Set empty health summary on error
        dispatch({ type: 'SET_HEALTH_SUMMARY', payload: {
          total_forwarders: 0,
          active_forwarders: 0,
          health_check_enabled: 0,
          healthy_forwarders: 0,
          unhealthy_forwarders: 0,
          degraded_forwarders: 0,
          unknown_forwarders: 0,
          last_updated: new Date().toISOString(),
          forwarder_details: []
        }})
      }

      // Load performance metrics
      const performanceResponse = await fetch('/api/health/performance?hours=24')
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json()
        // Ensure forwarder_metrics is always an array and overall_metrics exists
        if (performanceData && typeof performanceData === 'object') {
          performanceData.forwarder_metrics = Array.isArray(performanceData.forwarder_metrics) 
            ? performanceData.forwarder_metrics 
            : []
          // Ensure overall_metrics exists
          if (!performanceData.overall_metrics) {
            performanceData.overall_metrics = {
              total_checks: 0,
              successful_checks: 0,
              success_rate: 0,
              failure_rate: 0,
              avg_response_time: null,
              min_response_time: null,
              max_response_time: null
            }
          }
          dispatch({ type: 'SET_PERFORMANCE_METRICS', payload: performanceData })
        }
      } else {
        // Set empty performance metrics on error
        dispatch({ type: 'SET_PERFORMANCE_METRICS', payload: {
          period_hours: 24,
          overall_metrics: {
            total_checks: 0,
            successful_checks: 0,
            success_rate: 0,
            failure_rate: 0,
            avg_response_time: null,
            min_response_time: null,
            max_response_time: null
          },
          forwarder_metrics: [],
          performance_grade: 'unknown',
          generated_at: new Date().toISOString()
        }})
      }

      // Load alerts
      const alertsResponse = await fetch('/api/health/alerts')
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json()
        // Ensure alerts is always an array
        const alerts = Array.isArray(alertsData.alerts) ? alertsData.alerts : 
                      Array.isArray(alertsData) ? alertsData : []
        dispatch({ type: 'SET_ALERTS', payload: alerts })
      } else {
        // Set empty alerts on error
        dispatch({ type: 'SET_ALERTS', payload: [] })
      }
    } catch (error) {
      console.error('Error loading health data:', error)
      // Set safe defaults on error
      dispatch({ type: 'SET_HEALTH_SUMMARY', payload: {
        total_forwarders: 0,
        active_forwarders: 0,
        health_check_enabled: 0,
        healthy_forwarders: 0,
        unhealthy_forwarders: 0,
        degraded_forwarders: 0,
        unknown_forwarders: 0,
        last_updated: new Date().toISOString(),
        forwarder_details: []
      }})
      dispatch({ type: 'SET_ALERTS', payload: [] })
    }
  }

  const contextValue: HealthMonitoringContextType = {
    ...state,
    acknowledgeAlert,
    refreshHealthData
  }

  return (
    <HealthMonitoringContext.Provider value={contextValue}>
      {children}
    </HealthMonitoringContext.Provider>
  )
}

export const useHealthMonitoring = () => {
  const context = useContext(HealthMonitoringContext)
  if (context === undefined) {
    throw new Error('useHealthMonitoring must be used within a HealthMonitoringProvider')
  }
  return context
}