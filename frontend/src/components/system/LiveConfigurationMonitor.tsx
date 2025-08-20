import React, { useState, useEffect } from 'react'
import {
  CogIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { Card, Badge, Loading } from '@/components/ui'
import { useSystemWebSocket } from '@/hooks/useWebSocket'
import { formatRelativeTime } from '@/utils'

interface ConfigurationChange {
  id: string
  type: 'zone_created' | 'zone_updated' | 'zone_deleted' | 'record_created' | 'record_updated' | 'record_deleted' | 'bind_reload' | 'config_change'
  entity_type: 'zone' | 'record' | 'forwarder' | 'rpz' | 'system'
  entity_name: string
  action: string
  user_id?: string
  user_name?: string
  details: any
  timestamp: string
  status: 'pending' | 'completed' | 'failed'
}

interface LiveConfigurationMonitorProps {
  userId: string
  maxChanges?: number
}

const LiveConfigurationMonitor: React.FC<LiveConfigurationMonitorProps> = ({
  userId,
  maxChanges = 20
}) => {
  const [configChanges, setConfigChanges] = useState<ConfigurationChange[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  // WebSocket connection for real-time configuration updates
  const { subscribe, isConnected: wsConnected } = useSystemWebSocket(userId, {
    onConnect: () => {
      console.log('Live configuration monitor connected')
      setIsConnected(true)
    },
    onDisconnect: () => {
      setIsConnected(false)
    }
  })

  // Set up WebSocket event handlers
  useEffect(() => {
    // DNS Zone events
    subscribe('zone_created', (data) => {
      addConfigChange({
        type: 'zone_created',
        entity_type: 'zone',
        entity_name: data.name || data.zone_name,
        action: 'Created DNS zone',
        details: data,
        status: 'completed'
      })
    })

    subscribe('zone_updated', (data) => {
      addConfigChange({
        type: 'zone_updated',
        entity_type: 'zone',
        entity_name: data.name || data.zone_name,
        action: 'Updated DNS zone',
        details: data,
        status: 'completed'
      })
    })

    subscribe('zone_deleted', (data) => {
      addConfigChange({
        type: 'zone_deleted',
        entity_type: 'zone',
        entity_name: data.name || data.zone_name,
        action: 'Deleted DNS zone',
        details: data,
        status: 'completed'
      })
    })

    // DNS Record events
    subscribe('record_created', (data) => {
      addConfigChange({
        type: 'record_created',
        entity_type: 'record',
        entity_name: `${data.name || data.record_name} (${data.type})`,
        action: 'Created DNS record',
        details: data,
        status: 'completed'
      })
    })

    subscribe('record_updated', (data) => {
      addConfigChange({
        type: 'record_updated',
        entity_type: 'record',
        entity_name: `${data.name || data.record_name} (${data.type})`,
        action: 'Updated DNS record',
        details: data,
        status: 'completed'
      })
    })

    subscribe('record_deleted', (data) => {
      addConfigChange({
        type: 'record_deleted',
        entity_type: 'record',
        entity_name: `${data.name || data.record_name} (${data.type})`,
        action: 'Deleted DNS record',
        details: data,
        status: 'completed'
      })
    })

    // BIND reload events
    subscribe('bind_reload', (data) => {
      addConfigChange({
        type: 'bind_reload',
        entity_type: 'system',
        entity_name: 'BIND9 DNS Server',
        action: data.success ? 'Configuration reloaded successfully' : 'Configuration reload failed',
        details: data,
        status: data.success ? 'completed' : 'failed'
      })
    })

    // General configuration changes
    subscribe('config_change', (data) => {
      addConfigChange({
        type: 'config_change',
        entity_type: data.entity_type || 'system',
        entity_name: data.entity_name || 'System Configuration',
        action: data.action || 'Configuration changed',
        details: data,
        status: data.status || 'completed'
      })
    })
  }, [subscribe])

  const addConfigChange = (changeData: Partial<ConfigurationChange>) => {
    const change: ConfigurationChange = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      user_id: userId,
      ...changeData
    } as ConfigurationChange

    setConfigChanges(prev => [change, ...prev.slice(0, maxChanges - 1)])
    setLastUpdate(new Date().toISOString())
  }

  const getChangeTypeIcon = (type: string) => {
    switch (type) {
      case 'zone_created':
      case 'zone_updated':
      case 'zone_deleted':
        return <DocumentTextIcon className="h-5 w-5" />
      case 'record_created':
      case 'record_updated':
      case 'record_deleted':
        return <CogIcon className="h-5 w-5" />
      case 'bind_reload':
        return <ArrowPathIcon className="h-5 w-5" />
      default:
        return <CogIcon className="h-5 w-5" />
    }
  }

  const getChangeTypeColor = (type: string) => {
    if (type.includes('created')) return 'text-green-600 dark:text-green-400'
    if (type.includes('updated')) return 'text-blue-600 dark:text-blue-400'
    if (type.includes('deleted')) return 'text-red-600 dark:text-red-400'
    if (type === 'bind_reload') return 'text-purple-600 dark:text-purple-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-4 w-4 text-green-600 dark:text-green-400" />
      case 'failed':
        return <ExclamationTriangleIcon className="h-4 w-4 text-red-600 dark:text-red-400" />
      case 'pending':
        return <ClockIcon className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
      default:
        return <ClockIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
    }
  }

  const getActionDescription = (change: ConfigurationChange) => {
    const details = change.details || {}
    
    switch (change.type) {
      case 'zone_created':
        return `Created zone "${change.entity_name}" with ${details.record_count || 0} records`
      case 'zone_updated':
        return `Updated zone "${change.entity_name}" (Serial: ${details.serial || 'N/A'})`
      case 'zone_deleted':
        return `Deleted zone "${change.entity_name}"`
      case 'record_created':
        return `Added ${change.entity_name} → ${details.value || details.data || 'N/A'}`
      case 'record_updated':
        return `Modified ${change.entity_name} → ${details.value || details.data || 'N/A'}`
      case 'record_deleted':
        return `Removed ${change.entity_name}`
      case 'bind_reload':
        return details.message || change.action
      default:
        return change.action
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Live Configuration Monitor
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

      {/* Configuration Changes */}
      <Card
        title="Recent Configuration Changes"
        description={`Live stream of DNS configuration changes (showing last ${maxChanges})`}
      >
        <div className="space-y-3">
          {configChanges.length === 0 ? (
            <div className="text-center py-8">
              <CogIcon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                No configuration changes yet
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                Changes will appear here in real-time
              </p>
            </div>
          ) : (
            configChanges.map((change) => (
              <div
                key={change.id}
                className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className={`flex-shrink-0 mt-0.5 ${getChangeTypeColor(change.type)}`}>
                  {getChangeTypeIcon(change.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <Badge
                      variant={
                        change.entity_type === 'zone' ? 'primary' :
                        change.entity_type === 'record' ? 'secondary' :
                        change.entity_type === 'system' ? 'warning' : 'default'
                      }
                      size="sm"
                    >
                      {change.entity_type.toUpperCase()}
                    </Badge>
                    
                    {getStatusIcon(change.status)}
                  </div>
                  
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-1">
                    {getActionDescription(change)}
                  </p>
                  
                  {change.user_name && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      by {change.user_name}
                    </p>
                  )}
                </div>
                
                <div className="flex-shrink-0 text-right">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(change.timestamp)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* Statistics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <div className="text-center">
            <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
              {configChanges.filter(c => c.type.includes('zone')).length}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Zone Changes</p>
          </div>
        </Card>
        
        <Card className="p-4">
          <div className="text-center">
            <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
              {configChanges.filter(c => c.type.includes('record')).length}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Record Changes</p>
          </div>
        </Card>
        
        <Card className="p-4">
          <div className="text-center">
            <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
              {configChanges.filter(c => c.type === 'bind_reload').length}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">BIND Reloads</p>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default LiveConfigurationMonitor