import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone, ZoneHealth } from '@/types'
import { Badge } from '@/components/ui'
import { formatDistanceToNowSafe } from '@/utils'

interface ZoneHealthIndicatorProps {
  zone: Zone
  size?: 'sm' | 'md' | 'lg'
  showDetails?: boolean
  className?: string
}

const ZoneHealthIndicator: React.FC<ZoneHealthIndicatorProps> = ({
  zone,
  size = 'md',
  showDetails = false,
  className = ''
}) => {
  const { data: health, isLoading, error, refetch } = useQuery({
    queryKey: ['zone-health', zone.id],
    queryFn: () => zonesService.getZoneHealth(zone.id),
    refetchInterval: 60000, // Refresh every minute
    retry: 2,
  })

  const healthData = health?.data

  const getHealthIcon = (status: string, iconSize: string) => {
    const sizeClass = {
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6'
    }[iconSize]

    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className={`${sizeClass} text-green-500`} />
      case 'warning':
        return <ExclamationTriangleIcon className={`${sizeClass} text-yellow-500`} />
      case 'error':
        return <XCircleIcon className={`${sizeClass} text-red-500`} />
      default:
        return <ExclamationTriangleIcon className={`${sizeClass} text-gray-400`} />
    }
  }

  const getHealthBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge variant="success" size={size}>Healthy</Badge>
      case 'warning':
        return <Badge variant="warning" size={size}>Warning</Badge>
      case 'error':
        return <Badge variant="danger" size={size}>Error</Badge>
      default:
        return <Badge variant="default" size={size}>Unknown</Badge>
    }
  }

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 dark:text-green-400'
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'error':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <ArrowPathIcon className={`${size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-6 w-6' : 'h-5 w-5'} text-gray-400 animate-spin`} />
        {showDetails && (
          <span className={`${size === 'sm' ? 'text-xs' : 'text-sm'} text-gray-500 dark:text-gray-400`}>
            Checking health...
          </span>
        )}
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <XCircleIcon className={`${size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-6 w-6' : 'h-5 w-5'} text-red-500`} />
        {showDetails && (
          <span className={`${size === 'sm' ? 'text-xs' : 'text-sm'} text-red-600 dark:text-red-400`}>
            Health check failed
          </span>
        )}
      </div>
    )
  }

  if (!healthData) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <ExclamationTriangleIcon className={`${size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-6 w-6' : 'h-5 w-5'} text-gray-400`} />
        {showDetails && (
          <span className={`${size === 'sm' ? 'text-xs' : 'text-sm'} text-gray-500 dark:text-gray-400`}>
            No health data
          </span>
        )}
      </div>
    )
  }

  if (!showDetails) {
    // Simple indicator mode
    return (
      <div className={`flex items-center space-x-1 ${className}`}>
        {getHealthIcon(healthData.status, size)}
        {size !== 'sm' && getHealthBadge(healthData.status)}
      </div>
    )
  }

  // Detailed mode
  return (
    <div className={`${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {getHealthIcon(healthData.status, size)}
          <span className={`font-medium ${getHealthColor(healthData.status)}`}>
            Zone Health
          </span>
        </div>
        {getHealthBadge(healthData.status)}
      </div>

      <div className="space-y-2">
        {/* Last Check */}
        <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
          <ClockIcon className="h-4 w-4" />
          <span>
            Last checked {formatDistanceToNowSafe(healthData.last_check)}
          </span>
        </div>

        {/* Response Time */}
        {healthData.response_time && (
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Response time: <span className="font-medium">{healthData.response_time}ms</span>
          </div>
        )}

        {/* Issues */}
        {healthData.issues && healthData.issues.length > 0 && (
          <div className="mt-3">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Issues ({healthData.issues.length}):
            </div>
            <div className="space-y-1">
              {healthData.issues.map((issue, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-2 text-sm"
                >
                  <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                  <span className="text-gray-600 dark:text-gray-400">{issue}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Refresh Button */}
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center space-x-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 disabled:opacity-50"
        >
          <ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>
    </div>
  )
}

export default ZoneHealthIndicator