import React, { useState } from 'react'
import {
  ChartBarIcon,
  ShieldCheckIcon,
  HeartIcon,
  CogIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { Card, Badge } from '@/components/ui'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'
import RealTimeQueryMonitor from '@/components/dashboard/RealTimeQueryMonitor'
import RealTimeHealthMonitor from '@/components/health/RealTimeHealthMonitor'
import LiveConfigurationMonitor from '@/components/system/LiveConfigurationMonitor'
import RealTimeChart from '@/components/dashboard/RealTimeChart'
import WebSocketTest from '@/components/debug/WebSocketTest'

const RealTimeDashboard: React.FC = () => {
  const [activeView, setActiveView] = useState<'overview' | 'queries' | 'health' | 'config' | 'test'>('overview')
  const [isGlobalLive, setIsGlobalLive] = useState(true)

  const {
    isConnected,
    connectionStatus,
    events,
    unreadCount,
    systemStatus,
    connectionStats
  } = useRealTimeEvents()

  const userId = 'current-user' // This would come from auth context in production

  const views = [
    {
      id: 'overview',
      name: 'Overview',
      icon: ChartBarIcon,
      description: 'Real-time system overview'
    },
    {
      id: 'queries',
      name: 'Query Monitor',
      icon: ShieldCheckIcon,
      description: 'Live DNS query monitoring'
    },
    {
      id: 'health',
      name: 'Health Monitor',
      icon: HeartIcon,
      description: 'Real-time health status'
    },
    {
      id: 'config',
      name: 'Configuration',
      icon: CogIcon,
      description: 'Live configuration changes'
    },
    {
      id: 'test',
      name: 'WebSocket Test',
      icon: ArrowPathIcon,
      description: 'Test WebSocket connection'
    }
  ]

  const getConnectionStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-600 dark:text-green-400'
      case 'connecting': return 'text-yellow-600 dark:text-yellow-400'
      case 'disconnected': return 'text-red-600 dark:text-red-400'
      default: return 'text-gray-600 dark:text-gray-400'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Real-time Dashboard
            </h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Live monitoring of DNS queries, health status, and configuration changes
            </p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className={`text-sm font-medium ${getConnectionStatusColor(connectionStatus)}`}>
                {connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)}
              </span>
            </div>

            {/* Global Live Toggle */}
            <button
              onClick={() => setIsGlobalLive(!isGlobalLive)}
              className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md ${isGlobalLive
                  ? 'text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800'
                  : 'text-green-700 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-800'
                }`}
            >
              {isGlobalLive ? (
                <>
                  <PauseIcon className="w-4 h-4 mr-2" />
                  Pause All
                </>
              ) : (
                <>
                  <PlayIcon className="w-4 h-4 mr-2" />
                  Resume All
                </>
              )}
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="mt-6">
          <nav className="flex space-x-8" aria-label="Tabs">
            {views.map((view) => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id as any)}
                className={`${activeView === view.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <view.icon className="h-4 w-4" />
                <span>{view.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* System Status Bar */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Connection Status
              </p>
              <p className={`text-lg font-semibold ${getConnectionStatusColor(connectionStatus)}`}>
                {connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)}
              </p>
            </div>
            <div className={`w-8 h-8 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active Connections
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {connectionStats?.total_connections || 0}
              </p>
            </div>
            <ArrowPathIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Unread Events
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {unreadCount}
              </p>
            </div>
            {unreadCount > 0 && (
              <Badge variant="danger" size="sm">
                {unreadCount}
              </Badge>
            )}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                System Status
              </p>
              <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                {systemStatus ? 'Online' : 'Checking...'}
              </p>
            </div>
            <HeartIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
        </Card>
      </div>

      {/* Recent Events Summary */}
      {events.length > 0 && (
        <Card
          title="Recent Events"
          description="Latest system events and notifications"
        >
          <div className="space-y-2">
            {events.slice(0, 5).map((event) => (
              <div
                key={event.id}
                className={`flex items-center justify-between p-2 rounded border ${event.acknowledged ? 'opacity-60' : ''
                  } ${event.severity === 'error' ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20' :
                    event.severity === 'warning' ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20' :
                      event.severity === 'success' ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20' :
                        'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
                  }`}
              >
                <div className="flex items-center space-x-3">
                  <Badge
                    variant={
                      event.severity === 'error' ? 'danger' :
                        event.severity === 'warning' ? 'warning' :
                          event.severity === 'success' ? 'success' : 'default'
                    }
                    size="sm"
                  >
                    {event.type.replace('_', ' ').toUpperCase()}
                  </Badge>
                  <span className="text-sm text-gray-900 dark:text-gray-100">
                    {typeof event.data === 'object' && event.data.message
                      ? event.data.message
                      : `${event.type} event occurred`}
                  </span>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {(() => {
                    try {
                      const date = new Date(event.timestamp);
                      return isNaN(date.getTime()) ? 'Invalid time' : date.toLocaleTimeString();
                    } catch {
                      return 'Invalid time';
                    }
                  })()}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Main Content */}
      <div className="min-h-screen">
        {activeView === 'overview' && (
          <div className="space-y-6">
            <RealTimeChart userId={userId} minutes={15} autoRefresh={isGlobalLive} />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card
                title="Quick Health Status"
                description="Current system health overview"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">DNS Server</span>
                    <Badge variant="success" size="sm">Healthy</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">WebSocket Connection</span>
                    <Badge variant={isConnected ? 'success' : 'danger'} size="sm">
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Real-time Updates</span>
                    <Badge variant={isGlobalLive ? 'success' : 'warning'} size="sm">
                      {isGlobalLive ? 'Active' : 'Paused'}
                    </Badge>
                  </div>
                </div>
              </Card>

              <Card
                title="Connection Statistics"
                description="WebSocket connection details"
              >
                {connectionStats ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Total Users</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {connectionStats.total_users}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Active Connections</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {connectionStats.total_connections}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Messages Sent</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {connectionStats.total_messages_sent}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Broadcasting</span>
                      <Badge variant={connectionStats.broadcasting ? 'success' : 'danger'} size="sm">
                        {connectionStats.broadcasting ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">Loading connection stats...</p>
                )}
              </Card>
            </div>
          </div>
        )}

        {activeView === 'queries' && (
          <RealTimeQueryMonitor userId={userId} autoRefresh={isGlobalLive} />
        )}

        {activeView === 'health' && (
          <RealTimeHealthMonitor userId={userId} autoRefresh={isGlobalLive} />
        )}

        {activeView === 'config' && (
          <LiveConfigurationMonitor userId={userId} />
        )}

        {activeView === 'test' && (
          <WebSocketTest />
        )}
      </div>
    </div>
  )
}

export default RealTimeDashboard