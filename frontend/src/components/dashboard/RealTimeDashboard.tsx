import React, { useEffect, useState } from 'react'
import { useRealTimeEvents, useDNSEvents, useSecurityEvents, useHealthEvents } from '@/contexts/RealTimeEventContext'
import { useWebSocketContext } from '@/contexts/WebSocketContext'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { RealTimeNotifications } from '@/components/ui/RealTimeNotifications'
import { 
  ChartBarIcon,
  ShieldCheckIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { format } from 'date-fns'
import clsx from 'clsx'

interface RealTimeDashboardProps {
  userId: string
}

export const RealTimeDashboard: React.FC<RealTimeDashboardProps> = ({ userId }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'dns' | 'security' | 'health'>('overview')
  
  // Real-time event contexts
  const { systemStatus, connectionStats, isConnected } = useRealTimeEvents()
  const { dnsEvents } = useDNSEvents()
  const { securityEvents } = useSecurityEvents()
  const { healthEvents } = useHealthEvents()

  // Use existing WebSocket connection from context (no additional connections needed)
  const { isConnected: wsConnected } = useWebSocketContext()

  const getEventSeverityCount = (events: any[], severity: string) => {
    return events.filter(event => event.severity === severity).length
  }

  const getRecentEvents = (events: any[], limit = 5) => {
    return events.slice(0, limit)
  }

  return (
    <div className="space-y-6">
      {/* Header with Connection Status and Notifications */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Real-Time Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor your DNS server in real-time
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <ConnectionStatus />
          <RealTimeNotifications />
        </div>
      </div>

      {/* Connection Status Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ServerIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Connection Status
                  </dt>
                  <dd className={clsx(
                    'text-lg font-medium',
                    isConnected ? 'text-green-600' : 'text-red-600'
                  )}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ChartBarIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Connections
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {connectionStats?.total_connections || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ShieldCheckIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    BIND9 Status
                  </dt>
                  <dd className={clsx(
                    'text-lg font-medium',
                    systemStatus?.bind9_running ? 'text-green-600' : 'text-red-600'
                  )}>
                    {systemStatus?.bind9_running ? 'Running' : 'Stopped'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ExclamationTriangleIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Security Alerts
                  </dt>
                  <dd className="text-lg font-medium text-red-600">
                    {getEventSeverityCount(securityEvents, 'error')}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              System Performance
            </h3>
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">CPU Usage</dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {systemStatus.cpu_usage?.toFixed(1)}%
                </dd>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full" 
                    style={{ width: `${systemStatus.cpu_usage || 0}%` }}
                  />
                </div>
              </div>
              
              <div>
                <dt className="text-sm font-medium text-gray-500">Memory Usage</dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {systemStatus.memory_usage?.toFixed(1)}%
                </dd>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full" 
                    style={{ width: `${systemStatus.memory_usage || 0}%` }}
                  />
                </div>
              </div>
              
              <div>
                <dt className="text-sm font-medium text-gray-500">Disk Usage</dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {systemStatus.disk_usage?.toFixed(1)}%
                </dd>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-yellow-600 h-2 rounded-full" 
                    style={{ width: `${systemStatus.disk_usage || 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Event Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            {[
              { key: 'overview', label: 'Overview', count: dnsEvents.length + securityEvents.length + healthEvents.length },
              { key: 'dns', label: 'DNS Events', count: dnsEvents.length },
              { key: 'security', label: 'Security Events', count: securityEvents.length },
              { key: 'health', label: 'Health Events', count: healthEvents.length }
            ].map(({ key, label, count }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={clsx(
                  'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm',
                  activeTab === key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                )}
              >
                {label}
                {count > 0 && (
                  <span className={clsx(
                    'ml-2 py-0.5 px-2 rounded-full text-xs',
                    activeTab === key
                      ? 'bg-blue-100 text-blue-600'
                      : 'bg-gray-100 text-gray-900'
                  )}>
                    {count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Recent DNS Events */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Recent DNS Events</h4>
                  <div className="space-y-2">
                    {getRecentEvents(dnsEvents, 3).map((event) => (
                      <div key={event.id} className="flex items-center space-x-2 text-sm">
                        <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
                        <span className="text-gray-600 truncate">
                          {event.type.replace('_', ' ')}
                        </span>
                        <span className="text-gray-400 text-xs">
                          {format(new Date(event.timestamp), 'HH:mm')}
                        </span>
                      </div>
                    ))}
                    {dnsEvents.length === 0 && (
                      <p className="text-sm text-gray-500">No recent DNS events</p>
                    )}
                  </div>
                </div>

                {/* Recent Security Events */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Recent Security Events</h4>
                  <div className="space-y-2">
                    {getRecentEvents(securityEvents, 3).map((event) => (
                      <div key={event.id} className="flex items-center space-x-2 text-sm">
                        <ExclamationTriangleIcon className="h-4 w-4 text-red-500 flex-shrink-0" />
                        <span className="text-gray-600 truncate">
                          {event.type.replace('_', ' ')}
                        </span>
                        <span className="text-gray-400 text-xs">
                          {format(new Date(event.timestamp), 'HH:mm')}
                        </span>
                      </div>
                    ))}
                    {securityEvents.length === 0 && (
                      <p className="text-sm text-gray-500">No recent security events</p>
                    )}
                  </div>
                </div>

                {/* Recent Health Events */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Recent Health Events</h4>
                  <div className="space-y-2">
                    {getRecentEvents(healthEvents, 3).map((event) => (
                      <div key={event.id} className="flex items-center space-x-2 text-sm">
                        <ClockIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="text-gray-600 truncate">
                          {event.type.replace('_', ' ')}
                        </span>
                        <span className="text-gray-400 text-xs">
                          {format(new Date(event.timestamp), 'HH:mm')}
                        </span>
                      </div>
                    ))}
                    {healthEvents.length === 0 && (
                      <p className="text-sm text-gray-500">No recent health events</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dns' && (
            <EventList events={dnsEvents} type="DNS" />
          )}

          {activeTab === 'security' && (
            <EventList events={securityEvents} type="Security" />
          )}

          {activeTab === 'health' && (
            <EventList events={healthEvents} type="Health" />
          )}
        </div>
      </div>

      {/* Detailed Connection Status */}
      <ConnectionStatus showDetails={true} />
    </div>
  )
}

interface EventListProps {
  events: any[]
  type: string
}

const EventList: React.FC<EventListProps> = ({ events, type }) => {
  if (events.length === 0) {
    return (
      <div className="text-center py-12">
        <ClockIcon className="mx-auto h-12 w-12 text-gray-300" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No {type.toLowerCase()} events</h3>
        <p className="mt-1 text-sm text-gray-500">
          {type} events will appear here when they occur.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className={clsx(
                'flex-shrink-0 w-2 h-2 rounded-full mt-2',
                event.severity === 'error' ? 'bg-red-500' :
                event.severity === 'warning' ? 'bg-yellow-500' :
                event.severity === 'success' ? 'bg-green-500' : 'bg-blue-500'
              )} />
              <div>
                <h4 className="text-sm font-medium text-gray-900">
                  {event.type.split('_').map((word: string) => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                  ).join(' ')}
                </h4>
                <p className="mt-1 text-sm text-gray-600">
                  {JSON.stringify(event.data, null, 2)}
                </p>
              </div>
            </div>
            <time className="text-xs text-gray-500">
              {format(new Date(event.timestamp), 'MMM d, HH:mm:ss')}
            </time>
          </div>
        </div>
      ))}
    </div>
  )
}

export default RealTimeDashboard