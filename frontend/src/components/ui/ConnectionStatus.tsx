import React, { useState } from 'react'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'
import { 
  WifiIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { format } from 'date-fns'

interface ConnectionStatusProps {
  showDetails?: boolean
  className?: string
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  showDetails = false, 
  className = '' 
}) => {
  const [showTooltip, setShowTooltip] = useState(false)
  const { 
    isConnected, 
    connectionStatus, 
    reconnectAttempts, 
    connectionStats,
    systemStatus,
    getConnectionStats 
  } = useRealTimeEvents()

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'text-green-500'
      case 'connecting':
        return 'text-yellow-500'
      case 'error':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <WifiIcon className={clsx('h-5 w-5', getStatusColor())} />
      case 'connecting':
        return <ArrowPathIcon className={clsx('h-5 w-5 animate-spin', getStatusColor())} />
      case 'error':
        return <ExclamationTriangleIcon className={clsx('h-5 w-5', getStatusColor())} />
      default:
        return <WifiIcon className={clsx('h-5 w-5', getStatusColor())} />
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'error':
        return 'Connection Error'
      case 'disconnected':
        return 'Disconnected'
      default:
        return 'Unknown'
    }
  }

  if (!showDetails) {
    return (
      <div 
        className={clsx('relative flex items-center space-x-2', className)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {getStatusIcon()}
        <span className={clsx('text-sm font-medium', getStatusColor())}>
          {getStatusText()}
        </span>
        
        {reconnectAttempts > 0 && (
          <span className="text-xs text-gray-500">
            (Attempt {reconnectAttempts})
          </span>
        )}

        {/* Tooltip */}
        {showTooltip && (
          <div className="absolute bottom-full left-0 mb-2 w-64 rounded-md bg-gray-900 px-3 py-2 text-sm text-white shadow-lg z-50">
            <div className="space-y-1">
              <div>Status: {getStatusText()}</div>
              {connectionStats && (
                <>
                  <div>Active Connections: {connectionStats.total_connections}</div>
                  <div>Messages Sent: {connectionStats.total_messages_sent}</div>
                  <div>Queue Size: {connectionStats.queue_size}</div>
                </>
              )}
              {systemStatus && (
                <>
                  <div>CPU: {systemStatus.cpu_usage?.toFixed(1)}%</div>
                  <div>Memory: {systemStatus.memory_usage?.toFixed(1)}%</div>
                  <div>BIND9: {systemStatus.bind9_running ? 'Running' : 'Stopped'}</div>
                </>
              )}
            </div>
            <div className="absolute top-full left-4 h-0 w-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={clsx('rounded-lg border border-gray-200 bg-white p-4', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-sm font-medium text-gray-900">Real-time Connection</h3>
            <p className={clsx('text-sm', getStatusColor())}>
              {getStatusText()}
              {reconnectAttempts > 0 && ` (Attempt ${reconnectAttempts})`}
            </p>
          </div>
        </div>
        
        <button
          onClick={getConnectionStats}
          className="rounded-md p-1 text-gray-400 hover:text-gray-500"
          title="Refresh connection stats"
        >
          <ArrowPathIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Connection Statistics */}
      {connectionStats && (
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-500">Active Users</dt>
            <dd className="mt-1 text-gray-900">{connectionStats.total_users}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Total Connections</dt>
            <dd className="mt-1 text-gray-900">{connectionStats.total_connections}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Messages Sent</dt>
            <dd className="mt-1 text-gray-900">{connectionStats.total_messages_sent}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Queue Size</dt>
            <dd className="mt-1 text-gray-900">{connectionStats.queue_size}</dd>
          </div>
        </div>
      )}

      {/* Connection Types */}
      {connectionStats?.connection_types && Object.keys(connectionStats.connection_types).length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-500 mb-2">Connection Types</h4>
          <div className="space-y-1">
            {Object.entries(connectionStats.connection_types).map(([type, count]) => (
              <div key={type} className="flex justify-between text-sm">
                <span className="text-gray-600 capitalize">{type.replace('_', ' ')}</span>
                <span className="text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Status */}
      {systemStatus && (
        <div className="mt-4 border-t border-gray-200 pt-4">
          <h4 className="text-sm font-medium text-gray-500 mb-2">System Status</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium text-gray-500">CPU Usage</dt>
              <dd className="mt-1 text-gray-900">
                {systemStatus.cpu_usage?.toFixed(1)}%
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Memory Usage</dt>
              <dd className="mt-1 text-gray-900">
                {systemStatus.memory_usage?.toFixed(1)}%
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Disk Usage</dt>
              <dd className="mt-1 text-gray-900">
                {systemStatus.disk_usage?.toFixed(1)}%
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">BIND9 Status</dt>
              <dd className={clsx(
                'mt-1 font-medium',
                systemStatus.bind9_running ? 'text-green-600' : 'text-red-600'
              )}>
                {systemStatus.bind9_running ? 'Running' : 'Stopped'}
              </dd>
            </div>
          </div>
          
          {systemStatus.uptime && (
            <div className="mt-2 text-xs text-gray-500">
              Last updated: {format(new Date(systemStatus.uptime), 'MMM d, yyyy HH:mm:ss')}
            </div>
          )}
        </div>
      )}

      {/* Broadcasting Status */}
      {connectionStats && (
        <div className="mt-4 flex items-center space-x-2 text-sm">
          <div className={clsx(
            'h-2 w-2 rounded-full',
            connectionStats.broadcasting ? 'bg-green-400' : 'bg-gray-400'
          )} />
          <span className="text-gray-600">
            Broadcasting: {connectionStats.broadcasting ? 'Active' : 'Inactive'}
          </span>
          <span className="text-gray-500">
            ({connectionStats.active_tasks} active tasks)
          </span>
        </div>
      )}
    </div>
  )
}

export default ConnectionStatus