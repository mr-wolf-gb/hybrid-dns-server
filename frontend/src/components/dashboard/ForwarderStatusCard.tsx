import React from 'react'
import { Badge } from '@/components/ui'

interface ForwarderHealth {
  name: string
  status: string
  response_time: number
}

interface ForwarderStatusCardProps {
  forwarders: ForwarderHealth[]
}

const ForwarderStatusCard: React.FC<ForwarderStatusCardProps> = ({ forwarders }) => {
  if (!forwarders || forwarders.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500 dark:text-gray-400 text-sm">
        No forwarders configured
      </div>
    )
  }

  const getStatusVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'success'
      case 'unhealthy':
        return 'danger'
      case 'warning':
        return 'warning'
      default:
        return 'default'
    }
  }

  const formatResponseTime = (time: number): string => {
    if (time < 1000) {
      return `${time}ms`
    }
    return `${(time / 1000).toFixed(1)}s`
  }

  return (
    <div className="space-y-3">
      {forwarders.map((forwarder, index) => (
        <div 
          key={index} 
          className="flex items-center justify-between py-3 px-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {forwarder.name}
              </span>
              <Badge variant={getStatusVariant(forwarder.status)} size="sm">
                {forwarder.status}
              </Badge>
            </div>
            <div className="mt-1">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Response time: {formatResponseTime(forwarder.response_time)}
              </span>
            </div>
          </div>
          
          <div className="flex-shrink-0 ml-3">
            <div className={`w-3 h-3 rounded-full ${
              forwarder.status === 'healthy' 
                ? 'bg-green-400' 
                : forwarder.status === 'unhealthy'
                ? 'bg-red-400'
                : 'bg-yellow-400'
            }`} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default ForwarderStatusCard