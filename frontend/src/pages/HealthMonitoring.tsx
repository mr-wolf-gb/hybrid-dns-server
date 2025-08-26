import React, { useState } from 'react'
import { HeartIcon, ChartBarIcon, ExclamationTriangleIcon, ClockIcon } from '@heroicons/react/24/outline'
import { HealthMonitoringProvider, useHealthMonitoring } from '@/contexts/HealthMonitoringContext'
import RealTimeHealthStatus from '@/components/health/RealTimeHealthStatus'
import HealthHistoryChart from '@/components/health/HealthHistoryChart'
import HealthAlerts from '@/components/health/HealthAlerts'
import PerformanceMetrics from '@/components/health/PerformanceMetrics'
import { Card, Button, Badge, Select } from '@/components/ui'

const HealthMonitoringContent: React.FC = () => {
  const { healthSummary, alerts, isConnected, refreshHealthData } = useHealthMonitoring()
  const [selectedForwarder, setSelectedForwarder] = useState<number | undefined>(undefined)

  const unacknowledgedAlerts = alerts.filter(alert => !alert.acknowledged)
  const criticalAlerts = unacknowledgedAlerts.filter(alert => alert.level === 'critical')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <HeartIcon className="h-8 w-8 mr-3 text-red-500" />
            Health Monitoring
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Real-time health monitoring, alerts, and performance metrics for DNS forwarders
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
          {criticalAlerts.length > 0 && (
            <Badge variant="danger" size="lg">
              {criticalAlerts.length} Critical Alert{criticalAlerts.length !== 1 ? 's' : ''}
            </Badge>
          )}
          <Button onClick={refreshHealthData} variant="outline">
            Refresh Data
          </Button>
        </div>
      </div>

      {/* Critical Alerts Banner */}
      {criticalAlerts.length > 0 && (
        <Card className="border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 p-4">
          <div className="flex items-center space-x-3">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Critical Health Issues Detected
              </h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                {criticalAlerts.length} critical alert{criticalAlerts.length !== 1 ? 's' : ''} require{criticalAlerts.length === 1 ? 's' : ''} immediate attention.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Real-time Status */}
        <div className="lg:col-span-1">
          <RealTimeHealthStatus />
        </div>

        {/* Right Column - Alerts */}
        <div className="lg:col-span-2">
          <HealthAlerts />
        </div>
      </div>

      {/* Performance Metrics */}
      <PerformanceMetrics />

      {/* Health History Charts */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
            <ChartBarIcon className="h-6 w-6 mr-2 text-blue-500" />
            Health History
          </h2>
          <div className="flex items-center space-x-3">
            <label className="text-sm text-gray-600 dark:text-gray-400">
              Filter by forwarder:
            </label>
            <Select
              value={selectedForwarder?.toString() || ''}
              onValueChange={(value) => setSelectedForwarder(value ? parseInt(value) : undefined)}
            >
              <option value="">All Forwarders</option>
              {Array.isArray(healthSummary?.forwarder_details) && healthSummary.forwarder_details.map((forwarder) => (
                <option key={forwarder.id} value={forwarder.id.toString()}>
                  {forwarder.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <HealthHistoryChart
            forwarderId={selectedForwarder}
            forwarderName={
              selectedForwarder && Array.isArray(healthSummary?.forwarder_details)
                ? healthSummary.forwarder_details.find(f => f.id === selectedForwarder)?.name
                : undefined
            }
          />
          <HealthHistoryChart
            forwarderId={selectedForwarder}
            forwarderName={
              selectedForwarder && Array.isArray(healthSummary?.forwarder_details)
                ? healthSummary.forwarder_details.find(f => f.id === selectedForwarder)?.name
                : undefined
            }
          />
        </div>
      </div>

      {/* System Status */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <ClockIcon className="h-5 w-5 mr-2 text-gray-500" />
          System Status
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {healthSummary?.total_forwarders || 0}
            </div>
            <div className="text-sm text-gray-500">Total Forwarders</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {healthSummary?.active_forwarders || 0}
            </div>
            <div className="text-sm text-gray-500">Active</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {healthSummary?.health_check_enabled || 0}
            </div>
            <div className="text-sm text-gray-500">Monitored</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {unacknowledgedAlerts.length}
            </div>
            <div className="text-sm text-gray-500">Active Alerts</div>
          </div>
        </div>
      </Card>
    </div>
  )
}

const HealthMonitoring: React.FC = () => {
  // In a real app, you'd get the user ID from authentication context
  const userId = 'current-user' // This should come from your auth system

  return (
    <HealthMonitoringProvider userId={userId}>
      <HealthMonitoringContent />
    </HealthMonitoringProvider>
  )
}

export default HealthMonitoring