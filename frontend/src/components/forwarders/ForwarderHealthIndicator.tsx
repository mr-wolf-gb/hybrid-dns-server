import React from 'react'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  SignalIcon,
  SignalSlashIcon,
} from '@heroicons/react/24/outline'
import { Forwarder } from '@/types'
import { Badge } from '@/components/ui'
import { formatDateTime } from '@/utils'

interface ForwarderHealthIndicatorProps {
  forwarder: Forwarder
  showDetails?: boolean
}

const ForwarderHealthIndicator: React.FC<ForwarderHealthIndicatorProps> = ({
  forwarder,
  showDetails = false,
}) => {
  const getHealthIcon = () => {
    switch (forwarder.health_status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'unhealthy':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'unknown':
        return <ClockIcon className="h-5 w-5 text-gray-400" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getHealthBadgeVariant = () => {
    switch (forwarder.health_status) {
      case 'healthy':
        return 'success'
      case 'unhealthy':
        return 'danger'
      case 'unknown':
        return 'default'
      default:
        return 'default'
    }
  }

  const getResponseTimeColor = (responseTime?: number) => {
    if (!responseTime) return 'text-gray-500'
    if (responseTime < 50) return 'text-green-600'
    if (responseTime < 200) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (!showDetails) {
    return (
      <div className="flex items-center space-x-2">
        {getHealthIcon()}
        <Badge variant={getHealthBadgeVariant()}>
          {forwarder.health_status}
        </Badge>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center space-x-2">
        {getHealthIcon()}
        <Badge variant={getHealthBadgeVariant()}>
          {forwarder.health_status}
        </Badge>
      </div>
      
      {forwarder.last_health_check && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Last check: {formatDateTime(forwarder.last_health_check)}
        </div>
      )}
      
      {forwarder.response_time && (
        <div className={`text-xs font-mono ${getResponseTimeColor(forwarder.response_time)}`}>
          {forwarder.response_time}ms
        </div>
      )}
      
      <div className="flex items-center space-x-1">
        {forwarder.is_active ? (
          <SignalIcon className="h-3 w-3 text-green-500" />
        ) : (
          <SignalSlashIcon className="h-3 w-3 text-gray-400" />
        )}
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {forwarder.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
    </div>
  )
}

export default ForwarderHealthIndicator