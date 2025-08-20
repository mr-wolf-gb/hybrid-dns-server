import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react'
import { useHealthWebSocket } from '@/hooks/useWebSocket'

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
  healthSummary: null,
  performanceMetrics: null,
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

  // WebSocket connection for real-time health updates
  const { isConnected, connectionStatus, subscribe } = useHealthWebSocket(userId, {
    onConnect: () => {
      console.log('Health monitoring WebSocket connected')
    },
    onDisconnect: () => {
      console.log('Health monitoring WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Health monitoring WebSocket error:', error)
    }
  })

  // Set up event handlers
  useEffect(() => {
    subscribe('health_update', (data) => {
      dispatch({ type: 'SET_HEALTH_SUMMARY', payload: data })
    })

    subscribe('health_alert', (data) => {
      dispatch({ type: 'ADD_ALERT', payload: data })
    })

    subscribe('forwarder_status_change', (data) => {
      dispatch({ type: 'UPDATE_FORWARDER_STATUS', payload: data })
    })
  }, [subscribe])

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
        dispatch({ type: 'SET_HEALTH_SUMMARY', payload: healthData })
      }

      // Load performance metrics
      const performanceResponse = await fetch('/api/health/performance?hours=24')
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json()
        dispatch({ type: 'SET_PERFORMANCE_METRICS', payload: performanceData })
      }

      // Load alerts
      const alertsResponse = await fetch('/api/health/alerts')
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json()
        dispatch({ type: 'SET_ALERTS', payload: alertsData.alerts || [] })
      }
    } catch (error) {
      console.error('Error loading health data:', error)
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