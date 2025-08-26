import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChartBarIcon,
  ShieldCheckIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  PauseIcon
} from '@heroicons/react/24/outline'
import { Card, Badge, Loading } from '@/components/ui'
import { useWebSocketContext } from '@/contexts/WebSocketContext'
import { formatNumber, formatRelativeTime } from '@/utils'
import RealTimeChart from './RealTimeChart'

interface QueryEvent {
  timestamp: string
  client_ip: string
  domain: string
  type: string
  blocked: boolean
  response_time: number
}

interface LiveStats {
  queries: {
    total_today: number
    blocked_today: number
    block_rate: number
    last_hour: number
    unique_clients_hour: number
    unique_domains_hour: number
  }
  system: {
    cpu_usage: number
    memory_usage: number
    disk_usage: number
    uptime_seconds: number
  }
  performance: {
    avg_response_time: number
    cache_hit_rate: number
  }
}

interface RealTimeQueryMonitorProps {
  userId: string
  autoRefresh?: boolean
  maxEvents?: number
}

const RealTimeQueryMonitor: React.FC<RealTimeQueryMonitorProps> = ({
  userId,
  autoRefresh = true,
  maxEvents = 50
}) => {
  const [isLive, setIsLive] = useState(autoRefresh)
  const [recentQueries, setRecentQueries] = useState<QueryEvent[]>([])
  const [liveStats, setLiveStats] = useState<LiveStats | null>(null)
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const scrollRef = useRef<HTMLDivElement>(null)

  // Use existing WebSocket connection from context
  const { isConnected, registerEventHandler, unregisterEventHandler } = useWebSocketContext()

  // Fetch live stats periodically
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['realtime-stats'],
    queryFn: async () => {
      const response = await fetch('/api/realtime/stats/live')
      if (!response.ok) throw new Error('Failed to fetch live stats')
      return response.json()
    },
    refetchInterval: isLive ? 5000 : false, // Refresh every 5 seconds when live
    enabled: isLive
  })

  // Fetch recent queries
  const { data: queriesData, refetch: refetchQueries } = useQuery({
    queryKey: ['recent-queries'],
    queryFn: async () => {
      const response = await fetch('/api/realtime/queries/recent?limit=20')
      if (!response.ok) throw new Error('Failed to fetch recent queries')
      return response.json()
    },
    refetchInterval: isLive ? 3000 : false, // Refresh every 3 seconds when live
    enabled: isLive
  })

  // Set up WebSocket event handlers
  useEffect(() => {
    if (!isConnected) return

    const handlerId = 'realtime-query-monitor'
    
    registerEventHandler(handlerId, ['system_status'], (message) => {
      if (message.data?.type === 'query_update') {
        // Add new query to the list
        const newQuery: QueryEvent = {
          timestamp: message.data.timestamp,
          client_ip: message.data.client_ip,
          domain: message.data.query_domain,
          type: message.data.query_type,
          blocked: message.data.blocked,
          response_time: 0
        }

        setRecentQueries(prev => [newQuery, ...prev.slice(0, maxEvents - 1)])
        setLastUpdate(new Date().toISOString())

        // Auto-scroll to top when new queries arrive
        if (scrollRef.current) {
          scrollRef.current.scrollTop = 0
        }
      } else if (message.data?.type === 'system_metrics') {
        // Update system metrics in live stats
        setLiveStats(prev => prev ? {
          ...prev,
          system: {
            ...prev.system,
            cpu_usage: message.data.cpu_usage,
            memory_usage: message.data.memory_usage,
            disk_usage: message.data.disk_usage
          }
        } : null)
      }
    })

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [isConnected, registerEventHandler, unregisterEventHandler, maxEvents])

  // Update stats when data changes
  useEffect(() => {
    if (statsData) {
      setLiveStats(statsData)
      setLastUpdate(statsData.timestamp)
    }
  }, [statsData])

  // Update queries when data changes
  useEffect(() => {
    if (queriesData?.queries) {
      setRecentQueries(queriesData.queries)
    }
  }, [queriesData])

  const toggleLive = () => {
    setIsLive(!isLive)
    if (!isLive) {
      refetchStats()
      refetchQueries()
    }
  }

  const getQueryTypeColor = (type: string) => {
    switch (type) {
      case 'A': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'AAAA': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      case 'CNAME': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'MX': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      case 'TXT': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Real-time Query Monitor
          </h2>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {lastUpdate && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Last update: {formatRelativeTime(lastUpdate)}
            </span>
          )}
          <button
            onClick={toggleLive}
            className={`inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md ${isLive
              ? 'text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800'
              : 'text-green-700 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-800'
              }`}
          >
            {isLive ? (
              <>
                <PauseIcon className="w-4 h-4 mr-1" />
                Pause
              </>
            ) : (
              <>
                <PlayIcon className="w-4 h-4 mr-1" />
                Resume
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Statistics */}
      {liveStats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="p-4">
            <div className="flex items-center">
              <ChartBarIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Queries Today
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  {formatNumber(liveStats.queries.total_today)}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center">
              <ShieldCheckIcon className="h-8 w-8 text-red-600 dark:text-red-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Blocked Today
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  {formatNumber(liveStats.queries.blocked_today)}
                  <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                    ({(liveStats.queries.block_rate ?? 0).toFixed(1)}%)
                  </span>
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center">
              <ClockIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Avg Response
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  {(liveStats.performance.avg_response_time ?? 0).toFixed(1)}ms
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  CPU Usage
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  {(liveStats.system.cpu_usage ?? 0).toFixed(1)}%
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Real-time Chart */}
      <RealTimeChart userId={userId} minutes={10} autoRefresh={isLive} />

      {/* Recent Queries */}
      <Card
        title="Recent DNS Queries"
        description={`Live stream of DNS queries (showing last ${maxEvents})`}
      >
        <div
          ref={scrollRef}
          className="max-h-96 overflow-y-auto space-y-2"
        >
          {recentQueries.length === 0 ? (
            <div className="text-center py-8">
              <Loading text="Waiting for queries..." />
            </div>
          ) : (
            recentQueries.map((query, index) => (
              <div
                key={`${query.timestamp}-${index}`}
                className={`flex items-center justify-between p-3 rounded-lg border ${query.blocked
                  ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
                  : 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
                  }`}
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    <Badge
                      variant={query.blocked ? 'danger' : 'success'}
                      size="sm"
                    >
                      {query.blocked ? 'BLOCKED' : 'ALLOWED'}
                    </Badge>
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {query.domain}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      from {query.client_ip}
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Badge
                      className={getQueryTypeColor(query.type)}
                      size="sm"
                    >
                      {query.type}
                    </Badge>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatRelativeTime(query.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  )
}

export default RealTimeQueryMonitor