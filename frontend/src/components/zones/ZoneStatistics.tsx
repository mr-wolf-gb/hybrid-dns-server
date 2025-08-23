import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChartBarIcon,
  ClockIcon,
  DocumentTextIcon,
  HashtagIcon,
  CalendarIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone, ZoneStatistics as ZoneStatsType } from '@/types'
import { Badge } from '@/components/ui'
import { formatDistanceToNowSafe } from '@/utils'

interface ZoneStatisticsProps {
  zone: Zone
  className?: string
}

const ZoneStatistics: React.FC<ZoneStatisticsProps> = ({ zone, className = '' }) => {
  const { data: statistics, isLoading, error } = useQuery({
    queryKey: ['zone-statistics', zone.id],
    queryFn: () => zonesService.getZoneStatistics(zone.id),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const stats = statistics?.data

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getHealthStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge variant="success">Healthy</Badge>
      case 'warning':
        return <Badge variant="warning">Warning</Badge>
      case 'error':
        return <Badge variant="danger">Error</Badge>
      default:
        return <Badge variant="default">Unknown</Badge>
    }
  }

  if (isLoading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="flex items-center space-x-2 mb-4">
            <div className="h-5 w-5 bg-gray-300 dark:bg-gray-600 rounded"></div>
            <div className="h-6 w-32 bg-gray-300 dark:bg-gray-600 rounded"></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-20 bg-gray-300 dark:bg-gray-600 rounded"></div>
                <div className="h-6 w-16 bg-gray-300 dark:bg-gray-600 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
          <XCircleIcon className="h-5 w-5" />
          <span className="text-sm">Failed to load zone statistics</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <ChartBarIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Zone Statistics
          </h3>
        </div>
        {stats && getHealthStatusBadge(stats.health_status)}
      </div>

      {stats ? (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <DocumentTextIcon className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Records
                </span>
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats.record_count}
              </div>
            </div>

            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <HashtagIcon className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Serial
                </span>
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats.serial}
              </div>
            </div>

            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <ClockIcon className="h-4 w-4 text-purple-500" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Modified
                </span>
              </div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDistanceToNowSafe(stats.last_modified)}
              </div>
            </div>

            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <CalendarIcon className="h-4 w-4 text-orange-500" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Health Check
                </span>
              </div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDistanceToNowSafe(stats.last_check)}
              </div>
            </div>
          </div>

          {/* Health Status Details */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <div className="flex items-center space-x-2 mb-4">
              {getHealthStatusIcon(stats.health_status)}
              <h4 className="text-md font-medium text-gray-900 dark:text-gray-100">
                Health Status
              </h4>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">
                  Current Status
                </div>
                <div className="flex items-center space-x-2">
                  {getHealthStatusBadge(stats.health_status)}
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Last checked {formatDistanceToNowSafe(stats.last_check)}
                  </span>
                </div>
              </div>

              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">
                  Zone Configuration
                </div>
                <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                  <div>Type: <span className="font-medium">{zone.zone_type}</span></div>
                  <div>Status: <span className="font-medium">{zone.is_active ? 'Active' : 'Inactive'}</span></div>
                  <div>TTL: <span className="font-medium">{zone.minimum}s</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* Zone Details */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h4 className="text-md font-medium text-gray-900 dark:text-gray-100 mb-4">
              Zone Configuration
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Refresh:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">{zone.refresh}s</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Retry:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">{zone.retry}s</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Expire:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">{zone.expire}s</span>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Email:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">{zone.email}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Created:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">
                    {formatDistanceToNowSafe(zone.created_at)}
                  </span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Updated:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">
                    {formatDistanceToNowSafe(zone.updated_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No statistics available</p>
        </div>
      )}
    </div>
  )
}

export default ZoneStatistics