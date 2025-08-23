import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  HeartIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ServerIcon
} from '@heroicons/react/24/outline'
import { Card, Badge, Loading } from '@/components/ui'
import { useHealthWebSocket } from '@/hooks/useWebSocket'
import { formatRelativeTime, formatNumber } from '@/utils'

interface HealthAlert {
  id: string
  type: string
  level: 'warning' | 'critical'
  forwarder_id?: number
  message: string
  details: any
  created_at: string
  acknowledged: boolean
}

interface ForwarderHealth {
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
  forwarder_details: ForwarderHealth[]
}

interface RealTimeHealthMonitorProps {
  userId: string
  autoRefresh?: boolean
}

const RealTimeHealthMonitor: React.FC<RealTimeHealthMonitorProps> = ({
  userId,
  autoRefresh = true
}) => {
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null)
  const [recentAlerts, setRecentAlerts] = useState<HealthAlert[]>([])
  const [lastUpdate, setLastUpdate] = useState<string>('')

  // WebSocket connection for real-time health updates
  const { subscribe, isConnected } = useHealthWebSocket(userId, {
    onConnect: () => {
      console.log('Real-time health monitor connected')
    }
  })

  // Fetch live health status
  const { data: healthData, refetch } = useQuery({
    queryKey: ['realtime-health'],
    queryFn: async () => {
      const response = await fetch('/api/realtime/health/live')
      if (!response.ok) throw new Error('Failed to fetch health status')
      return response.json()
    },
    refetchInterval: autoRefresh ? 10000 : false, // Refresh every 10 seconds
    enabled: autoRefresh
  })

  // Set up WebSocket event handlers
  useEffect(() => {
    subscribe('health_update', (data) => {
      setHealthSummary(data)
      setLastUpdate(new Date().toISOString())
    })

    subscribe('health_alert', (data) => {
      setRecentAlerts(prev => [data, ...prev.slice(0, 9)]) // Keep last 10 alerts
    })

    subscribe('forwarder_status_change', (data) => {
      setHealthSummary(prev => {
        if (!prev) return prev

        return {
          ...prev,
          forwarder_details: (prev.forwarder_details || []).map(forwarder =>
            forwarder.id === data.forwarder_id
              ? { ...forwarder, status: data.new_status }
              : forwarder
          )
        }
      })
    })
  }, [subscribe])

  // Update data when query results change
  useEffect(() => {
    if (healthData) {
      setHealthSummary(healthData.health_summary)
      setRecentAlerts(healthData.recent_alerts || [])
      setLastUpdate(healthData.timestamp)
    }
  }, [healthData])

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return 'text-green-600 dark:text-green-400'
      case 'degraded': return 'text-yellow-600 dark:text-yellow-400'
      case 'unhealthy': return 'text-red-600 dark:text-red-400'
      default: return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return <CheckCircleIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
      case 'degraded': return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
      case 'unhealthy': return <XCircleIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
      default: return <ClockIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
      case 'warning': return 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20'
      default: return 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
    }
  }

  if (!healthSummary) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading health status..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Real-time Health Monitor
          </h2>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {lastUpdate && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Last update: {formatRelativeTime(lastUpdate)}
          </span>
        )}
      </div>

      {/* Health Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center">
            <HeartIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Healthy
              </p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {healthSummary.healthy_forwarders}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Degraded
              </p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {healthSummary.degraded_forwarders}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <XCircleIcon className="h-8 w-8 text-red-600 dark:text-red-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Unhealthy
              </p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {healthSummary.unhealthy_forwarders}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <ServerIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Active
              </p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {healthSummary.active_forwarders}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Forwarder Details */}
      <Card
        title="Forwarder Status"
        description="Real-time status of all DNS forwarders"
      >
        <div className="space-y-3">
          {(healthSummary.forwarder_details || []).map((forwarder) => (
            <div
              key={forwarder.id}
              className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center space-x-3">
                {getStatusIcon(forwarder.status)}
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {forwarder.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {forwarder.type} • {forwarder.healthy_servers}/{forwarder.total_servers} servers
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <Badge
                  variant={
                    forwarder.status === 'healthy' ? 'success' :
                      forwarder.status === 'degraded' ? 'warning' : 'danger'
                  }
                  size="sm"
                >
                  {forwarder.status.toUpperCase()}
                </Badge>

                {forwarder.last_checked && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(forwarder.last_checked)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent Alerts */}
      {recentAlerts.length > 0 && (
        <Card
          title="Recent Health Alerts"
          description="Latest health alerts and notifications"
        >
          <div className="space-y-3">
            {recentAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-3 rounded-lg border ${getAlertLevelColor(alert.level)} ${alert.acknowledged ? 'opacity-60' : ''
                  }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <Badge
                        variant={alert.level === 'critical' ? 'danger' : 'warning'}
                        size="sm"
                      >
                        {alert.level.toUpperCase()}
                      </Badge>
                      {alert.acknowledged && (
                        <Badge variant="success" size="sm">
                          ACKNOWLEDGED
                        </Badge>
                      )}
                    </div>

                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-1">
                      {alert.message}
                    </p>

                    {alert.forwarder_id && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Forwarder ID: {alert.forwarder_id}
                      </p>
                    )}
                  </div>

                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(alert.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default RealTimeHealthMonitor