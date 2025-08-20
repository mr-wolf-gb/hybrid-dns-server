import React from 'react'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  SignalIcon,
  SignalSlashIcon,
  WifiIcon
} from '@heroicons/react/24/outline'
import { useHealthMonitoring } from '@/contexts/HealthMonitoringContext'
import { Card, Badge } from '@/components/ui'
import { formatDateTime } from '@/utils'

const RealTimeHealthStatus: React.FC = () => {
  const { healthSummary, isConnected, connectionStatus, lastUpdate } = useHealthMonitoring()

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <SignalIcon className="h-4 w-4 text-green-500" />
      case 'connecting':
        return <ClockIcon className="h-4 w-4 text-yellow-500 animate-spin" />
      case 'disconnected':
        return <SignalSlashIcon className="h-4 w-4 text-gray-400" />
      case 'error':
        return <ExclamationCircleIcon className="h-4 w-4 text-red-500" />
      default:
        return <WifiIcon className="h-4 w-4 text-gray-400" />
    }
  }

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Real-time updates active'
      case 'connecting':
        return 'Connecting...'
      case 'disconnected':
        return 'Disconnected'
      case 'error':
        return 'Connection error'
      default:
        return 'Unknown status'
    }
  }

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 dark:text-green-400'
      case 'unhealthy':
        return 'text-red-600 dark:text-red-400'
      case 'degraded':
        return 'text-yellow-600 dark:text-yellow-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'unhealthy':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'degraded':
        return <ExclamationCircleIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  if (!healthSummary) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Health Status
          </h3>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            {getConnectionStatusIcon()}
            <span>{getConnectionStatusText()}</span>
          </div>
        </div>
        <div className="text-center py-8">
          <ClockIcon className="h-8 w-8 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Loading health data...</p>
        </div>
      </Card>
    )
  }

  const healthPercentage = healthSummary.health_check_enabled > 0 
    ? (healthSummary.healthy_forwarders / healthSummary.health_check_enabled) * 100 
    : 100

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Real-Time Health Status
        </h3>
        <div className="flex items-center space-x-2 text-sm">
          {getConnectionStatusIcon()}
          <span className={isConnected ? 'text-green-600' : 'text-gray-500'}>
            {getConnectionStatusText()}
          </span>
        </div>
      </div>

      {/* Overall Health Score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Overall Health
          </span>
          <span className={`text-sm font-semibold ${getHealthStatusColor(
            healthPercentage >= 95 ? 'healthy' : healthPercentage >= 80 ? 'degraded' : 'unhealthy'
          )}`}>
            {healthPercentage.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              healthPercentage >= 95
                ? 'bg-green-500'
                : healthPercentage >= 80
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${healthPercentage}%` }}
          />
        </div>
      </div>

      {/* Health Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {healthSummary.healthy_forwarders}
          </div>
          <div className="text-xs text-gray-500">Healthy</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
            {healthSummary.degraded_forwarders}
          </div>
          <div className="text-xs text-gray-500">Degraded</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {healthSummary.unhealthy_forwarders}
          </div>
          <div className="text-xs text-gray-500">Unhealthy</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
            {healthSummary.unknown_forwarders}
          </div>
          <div className="text-xs text-gray-500">Unknown</div>
        </div>
      </div>

      {/* Recent Forwarder Status */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Forwarder Status
        </h4>
        <div className="max-h-48 overflow-y-auto space-y-2">
          {healthSummary.forwarder_details.slice(0, 10).map((forwarder) => (
            <div
              key={forwarder.id}
              className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                {getHealthIcon(forwarder.status)}
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {forwarder.name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {forwarder.healthy_servers}/{forwarder.total_servers} servers
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Badge
                  variant={
                    forwarder.status === 'healthy'
                      ? 'success'
                      : forwarder.status === 'unhealthy'
                      ? 'danger'
                      : forwarder.status === 'degraded'
                      ? 'warning'
                      : 'default'
                  }
                  size="sm"
                >
                  {forwarder.status}
                </Badge>
                {!forwarder.is_active && (
                  <Badge variant="secondary" size="sm">
                    Inactive
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 text-center">
            Last updated: {formatDateTime(lastUpdate)}
          </p>
        </div>
      )}
    </Card>
  )
}

export default RealTimeHealthStatus