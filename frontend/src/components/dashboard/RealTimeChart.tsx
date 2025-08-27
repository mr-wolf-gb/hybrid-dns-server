import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useWebSocketContext } from '@/contexts/WebSocketContext'
import LazyChart from '@/components/charts/LazyChart'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface QueryStreamData {
  timestamp: string
  total_queries: number
  blocked_queries: number
  allowed_queries: number
  unique_clients: number
  avg_response_time: number
}

interface RealTimeChartProps {
  userId: string
  minutes?: number
  autoRefresh?: boolean
}

const RealTimeChart: React.FC<RealTimeChartProps> = ({
  userId,
  minutes = 10,
  autoRefresh = true
}) => {
  const [streamData, setStreamData] = useState<QueryStreamData[]>([])
  const [isLive, setIsLive] = useState(autoRefresh)
  const chartRef = useRef<any>(null)

  // Use existing WebSocket connection from context
  const { isConnected, registerEventHandler, unregisterEventHandler } = useWebSocketContext()

  // Fetch query stream data
  const { data: queryStream, refetch } = useQuery({
    queryKey: ['query-stream', minutes],
    queryFn: async () => {
      const response = await fetch(`/api/realtime/queries/stream?minutes=${minutes}`)
      if (!response.ok) throw new Error('Failed to fetch query stream')
      return response.json()
    },
    refetchInterval: isLive ? 30000 : false, // Refresh every 30 seconds when live
    enabled: isLive
  })

  // Set up WebSocket event handlers for real-time updates
  useEffect(() => {
    if (!isConnected) return

    const handlerId = 'realtime-chart'
    
    registerEventHandler(handlerId, ['system_status'], (message) => {
      if (message.data?.type === 'query_update') {
        // Add new data point to the chart
        const now = new Date()
        const currentMinute = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes())

        setStreamData(prev => {
          const updated = [...prev]
          const existingIndex = updated.findIndex(item =>
            new Date(item.timestamp).getTime() === currentMinute.getTime()
          )

          if (existingIndex >= 0) {
            // Update existing data point
            updated[existingIndex] = {
              ...updated[existingIndex],
              total_queries: updated[existingIndex].total_queries + 1,
              blocked_queries: data.data.blocked ? updated[existingIndex].blocked_queries + 1 : updated[existingIndex].blocked_queries,
              allowed_queries: data.data.blocked ? updated[existingIndex].allowed_queries : updated[existingIndex].allowed_queries + 1
            }
          } else {
            // Add new data point
            const newPoint: QueryStreamData = {
              timestamp: currentMinute.toISOString(),
              total_queries: 1,
              blocked_queries: data.data.blocked ? 1 : 0,
              allowed_queries: data.data.blocked ? 0 : 1,
              unique_clients: 1,
              avg_response_time: 0
            }
            updated.push(newPoint)

            // Keep only the last N minutes
            const cutoff = new Date(now.getTime() - minutes * 60 * 1000)
            return updated.filter(item => new Date(item.timestamp) >= cutoff)
          }

          return updated
        })
      }
    })

    return () => {
      unregisterEventHandler(handlerId)
    }
  }, [isConnected, registerEventHandler, unregisterEventHandler, minutes])

  // Update data when query results change
  useEffect(() => {
    if (queryStream?.stream) {
      setStreamData(queryStream.stream)
    }
  }, [queryStream])

  const chartData = {
    labels: streamData.map(item => {
      const date = new Date(item.timestamp)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }),
    datasets: [
      {
        label: 'Total Queries',
        data: streamData.map(item => item.total_queries),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Blocked Queries',
        data: streamData.map(item => item.blocked_queries),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Allowed Queries',
        data: streamData.map(item => item.allowed_queries),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
      }
    ]
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: `DNS Query Activity (Last ${minutes} minutes)`,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          afterLabel: (context: any) => {
            const dataPoint = streamData[context.dataIndex]
            if (dataPoint) {
              const avg = dataPoint.avg_response_time ?? 0
              const avgNum = typeof avg === 'number' ? avg : 0
              return [
                `Unique Clients: ${Number(dataPoint.unique_clients ?? 0)}`,
                `Avg Response: ${avgNum.toFixed(1)}ms`
              ]
            }
            return []
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Queries per Minute'
        },
        beginAtZero: true
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    },
    animation: {
      duration: isLive ? 750 : 0 // Smooth animation for live updates
    }
  }

  const toggleLive = () => {
    setIsLive(!isLive)
    if (!isLive) {
      refetch()
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Real-time Query Activity
          </h3>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={minutes}
            onChange={(e) => {
              // This would trigger a refetch with new minutes parameter
              window.location.search = `?minutes=${e.target.value}`
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value={5}>5 minutes</option>
            <option value={10}>10 minutes</option>
            <option value={15}>15 minutes</option>
            <option value={30}>30 minutes</option>
            <option value={60}>1 hour</option>
          </select>

          <button
            onClick={toggleLive}
            className={`px-3 py-1 text-sm rounded-md border ${isLive
                ? 'border-red-300 text-red-700 bg-red-50 hover:bg-red-100 dark:border-red-600 dark:text-red-400 dark:bg-red-900/20 dark:hover:bg-red-900/30'
                : 'border-green-300 text-green-700 bg-green-50 hover:bg-green-100 dark:border-green-600 dark:text-green-400 dark:bg-green-900/20 dark:hover:bg-green-900/30'
              }`}
          >
            {isLive ? 'Pause' : 'Resume'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-80 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <LazyChart>
          {({ Line }) => (
            <Line ref={chartRef} data={chartData} options={chartOptions} />
          )}
        </LazyChart>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <div className="text-center">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {streamData.reduce((sum, item) => sum + item.total_queries, 0)}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Queries</p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <div className="text-center">
            <p className="text-lg font-semibold text-red-600 dark:text-red-400">
              {streamData.reduce((sum, item) => sum + item.blocked_queries, 0)}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Blocked</p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <div className="text-center">
            <p className="text-lg font-semibold text-green-600 dark:text-green-400">
              {streamData.reduce((sum, item) => sum + item.allowed_queries, 0)}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Allowed</p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <div className="text-center">
            <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
              {streamData.length > 0 ? Math.max(...streamData.map(item => item.unique_clients)) : 0}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Peak Clients</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default RealTimeChart