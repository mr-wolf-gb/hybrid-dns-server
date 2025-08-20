import React, { useState } from 'react'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  XMarkIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { useHealthMonitoring } from '@/contexts/HealthMonitoringContext'
import { Card, Button, Badge } from '@/components/ui'
import { formatDateTime } from '@/utils'

const HealthAlerts: React.FC = () => {
  const { alerts, acknowledgeAlert } = useHealthMonitoring()
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning'>('all')

  const filteredAlerts = alerts.filter(alert => {
    if (filter === 'all') return true
    return alert.level === filter
  })

  const unacknowledgedAlerts = alerts.filter(alert => !alert.acknowledged)
  const criticalAlerts = alerts.filter(alert => alert.level === 'critical' && !alert.acknowledged)
  const warningAlerts = alerts.filter(alert => alert.level === 'warning' && !alert.acknowledged)

  const getAlertIcon = (level: string, acknowledged: boolean) => {
    if (acknowledged) {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />
    }

    switch (level) {
      case 'critical':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getAlertBorderColor = (level: string, acknowledged: boolean) => {
    if (acknowledged) return 'border-green-200 dark:border-green-800'
    
    switch (level) {
      case 'critical':
        return 'border-red-200 dark:border-red-800'
      case 'warning':
        return 'border-yellow-200 dark:border-yellow-800'
      default:
        return 'border-gray-200 dark:border-gray-700'
    }
  }

  const getAlertBackgroundColor = (level: string, acknowledged: boolean) => {
    if (acknowledged) return 'bg-green-50 dark:bg-green-900/10'
    
    switch (level) {
      case 'critical':
        return 'bg-red-50 dark:bg-red-900/10'
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/10'
      default:
        return 'bg-gray-50 dark:bg-gray-800'
    }
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Health Alerts
          </h3>
          <p className="text-sm text-gray-500">
            {unacknowledgedAlerts.length} unacknowledged alerts
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="danger" size="sm">
            {criticalAlerts.length} Critical
          </Badge>
          <Badge variant="warning" size="sm">
            {warningAlerts.length} Warning
          </Badge>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex items-center space-x-2 mb-4">
        <Button
          variant={filter === 'all' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({alerts.length})
        </Button>
        <Button
          variant={filter === 'critical' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setFilter('critical')}
        >
          Critical ({alerts.filter(a => a.level === 'critical').length})
        </Button>
        <Button
          variant={filter === 'warning' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setFilter('warning')}
        >
          Warning ({alerts.filter(a => a.level === 'warning').length})
        </Button>
      </div>

      {/* Alerts List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircleIcon className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <p className="text-gray-500">
              {filter === 'all' 
                ? 'No alerts at this time' 
                : `No ${filter} alerts`}
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-4 ${getAlertBorderColor(alert.level, alert.acknowledged)} ${getAlertBackgroundColor(alert.level, alert.acknowledged)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  {getAlertIcon(alert.level, alert.acknowledged)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <Badge
                        variant={alert.level === 'critical' ? 'danger' : 'warning'}
                        size="sm"
                      >
                        {alert.level.toUpperCase()}
                      </Badge>
                      <Badge variant="secondary" size="sm">
                        {alert.type.replace('_', ' ')}
                      </Badge>
                      {alert.acknowledged && (
                        <Badge variant="success" size="sm">
                          Acknowledged
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-500 mb-2">
                      {formatDateTime(alert.created_at)}
                    </p>
                    
                    {/* Alert Details */}
                    {alert.details && (
                      <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                        {alert.forwarder_name && (
                          <div>Forwarder: {alert.forwarder_name}</div>
                        )}
                        {alert.details.status && (
                          <div>Status: {alert.details.status}</div>
                        )}
                        {alert.details.healthy_servers !== undefined && alert.details.total_servers !== undefined && (
                          <div>
                            Servers: {alert.details.healthy_servers}/{alert.details.total_servers} healthy
                          </div>
                        )}
                        {alert.details.consecutive_failures && (
                          <div>Consecutive failures: {alert.details.consecutive_failures}</div>
                        )}
                        {alert.details.value !== undefined && alert.details.threshold !== undefined && (
                          <div>
                            Value: {alert.details.value} (threshold: {alert.details.threshold})
                          </div>
                        )}
                        {alert.details.uptime_24h !== undefined && (
                          <div>24h uptime: {alert.details.uptime_24h.toFixed(1)}%</div>
                        )}
                        {alert.details.avg_response_time && (
                          <div>Avg response time: {alert.details.avg_response_time.toFixed(1)}ms</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Action Buttons */}
                <div className="flex items-center space-x-2 ml-4">
                  {!alert.acknowledged && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => acknowledgeAlert(alert.id)}
                      className="text-xs"
                    >
                      Acknowledge
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Summary Stats */}
      {alerts.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-red-600 dark:text-red-400">
                {criticalAlerts.length}
              </div>
              <div className="text-xs text-gray-500">Critical</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">
                {warningAlerts.length}
              </div>
              <div className="text-xs text-gray-500">Warning</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-green-600 dark:text-green-400">
                {alerts.filter(a => a.acknowledged).length}
              </div>
              <div className="text-xs text-gray-500">Acknowledged</div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

export default HealthAlerts