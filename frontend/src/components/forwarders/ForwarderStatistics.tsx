import React from 'react'
import {
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { Forwarder } from '@/types'
import { Card } from '@/components/ui'
import { formatDateTime } from '@/utils'

interface ForwarderStatisticsProps {
  forwarders: Forwarder[]
}

interface ForwarderStats {
  total: number
  active: number
  healthy: number
  unhealthy: number
  unknown: number
  byType: {
    ad: number
    intranet: number
    public: number
  }
  avgResponseTime: number
  lastHealthCheck: string | null
}

const ForwarderStatistics: React.FC<ForwarderStatisticsProps> = ({ forwarders }) => {
  const calculateStats = (): ForwarderStats => {
    const stats: ForwarderStats = {
      total: forwarders.length,
      active: 0,
      healthy: 0,
      unhealthy: 0,
      unknown: 0,
      byType: { ad: 0, intranet: 0, public: 0 },
      avgResponseTime: 0,
      lastHealthCheck: null,
    }

    let totalResponseTime = 0
    let responseTimeCount = 0
    let latestCheck: Date | null = null

    forwarders.forEach(forwarder => {
      if (forwarder.is_active) stats.active++
      
      switch (forwarder.health_status) {
        case 'healthy':
          stats.healthy++
          break
        case 'unhealthy':
          stats.unhealthy++
          break
        default:
          stats.unknown++
      }

      if (forwarder.type && forwarder.type in stats.byType) {
        stats.byType[forwarder.type as keyof typeof stats.byType]++
      }

      if (forwarder.response_time) {
        totalResponseTime += forwarder.response_time
        responseTimeCount++
      }

      if (forwarder.last_health_check) {
        const checkDate = new Date(forwarder.last_health_check)
        if (!latestCheck || checkDate > latestCheck) {
          latestCheck = checkDate
          stats.lastHealthCheck = forwarder.last_health_check
        }
      }
    })

    if (responseTimeCount > 0) {
      stats.avgResponseTime = Math.round(totalResponseTime / responseTimeCount)
    }

    return stats
  }

  const stats = calculateStats()

  const getHealthPercentage = () => {
    if (stats.total === 0) return 0
    return Math.round((stats.healthy / stats.total) * 100)
  }

  const getActivePercentage = () => {
    if (stats.total === 0) return 0
    return Math.round((stats.active / stats.total) * 100)
  }

  const getResponseTimeColor = (responseTime: number) => {
    if (responseTime < 50) return 'text-green-600 dark:text-green-400'
    if (responseTime < 200) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Overview Statistics */}
      <Card className="p-6">
        <div className="flex items-center mb-4">
          <ChartBarIcon className="h-5 w-5 text-blue-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Overview Statistics
          </h3>
        </div>
        
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Total Forwarders</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {stats.total}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Active</span>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-semibold text-green-600 dark:text-green-400">
                {stats.active}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({getActivePercentage()}%)
              </span>
            </div>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Healthy</span>
            <div className="flex items-center space-x-2">
              <CheckCircleIcon className="h-4 w-4 text-green-500" />
              <span className="text-lg font-semibold text-green-600 dark:text-green-400">
                {stats.healthy}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({getHealthPercentage()}%)
              </span>
            </div>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Unhealthy</span>
            <div className="flex items-center space-x-2">
              <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
              <span className="text-lg font-semibold text-red-600 dark:text-red-400">
                {stats.unhealthy}
              </span>
            </div>
          </div>
          
          {stats.unknown > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Unknown Status</span>
              <span className="text-lg font-semibold text-gray-500 dark:text-gray-400">
                {stats.unknown}
              </span>
            </div>
          )}
        </div>
      </Card>

      {/* Performance Statistics */}
      <Card className="p-6">
        <div className="flex items-center mb-4">
          <ClockIcon className="h-5 w-5 text-purple-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Performance Statistics
          </h3>
        </div>
        
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Average Response Time</span>
            <span className={`text-lg font-semibold font-mono ${getResponseTimeColor(stats.avgResponseTime)}`}>
              {stats.avgResponseTime > 0 ? `${stats.avgResponseTime}ms` : 'N/A'}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Last Health Check</span>
            <span className="text-sm text-gray-900 dark:text-gray-100">
              {stats.lastHealthCheck ? formatDateTime(stats.lastHealthCheck) : 'Never'}
            </span>
          </div>
          
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">Forwarders by Type</div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-blue-600 dark:text-blue-400">Active Directory</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {stats.byType.ad}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-purple-600 dark:text-purple-400">Intranet</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {stats.byType.intranet}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-green-600 dark:text-green-400">Public DNS</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {stats.byType.public}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Health Status Distribution */}
      <Card className="p-6 lg:col-span-2">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Health Status Distribution
        </h3>
        
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
              <span>Health Status</span>
              <span>{getHealthPercentage()}% Healthy</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
              <div className="flex h-3 rounded-full overflow-hidden">
                {stats.healthy > 0 && (
                  <div
                    className="bg-green-500"
                    style={{ width: `${(stats.healthy / stats.total) * 100}%` }}
                  />
                )}
                {stats.unhealthy > 0 && (
                  <div
                    className="bg-red-500"
                    style={{ width: `${(stats.unhealthy / stats.total) * 100}%` }}
                  />
                )}
                {stats.unknown > 0 && (
                  <div
                    className="bg-gray-400"
                    style={{ width: `${(stats.unknown / stats.total) * 100}%` }}
                  />
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span className="text-gray-600 dark:text-gray-400">Healthy ({stats.healthy})</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <span className="text-gray-600 dark:text-gray-400">Unhealthy ({stats.unhealthy})</span>
            </div>
            {stats.unknown > 0 && (
              <div className="flex items-center space-x-1">
                <div className="w-3 h-3 bg-gray-400 rounded-full" />
                <span className="text-gray-600 dark:text-gray-400">Unknown ({stats.unknown})</span>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

export default ForwarderStatistics