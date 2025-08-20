import React, { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'
import { Card, Button, Select } from '@/components/ui'
import { formatDateTime } from '@/utils'

interface HealthHistoryData {
  timestamp: string
  total_checks: number
  healthy_checks: number
  success_rate: number
  avg_response_time: number | null
  min_response_time: number | null
  max_response_time: number | null
}

interface HealthHistoryChartProps {
  forwarderId?: number
  forwarderName?: string
}

const HealthHistoryChart: React.FC<HealthHistoryChartProps> = ({
  forwarderId,
  forwarderName
}) => {
  const [historyData, setHistoryData] = useState<HealthHistoryData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState('24')
  const [chartType, setChartType] = useState<'success_rate' | 'response_time'>('success_rate')

  const loadHistoryData = async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        hours: timeRange
      })
      
      if (forwarderId) {
        params.append('forwarder_id', forwarderId.toString())
      }

      const response = await fetch(`/api/health/history?${params}`)
      
      if (!response.ok) {
        throw new Error('Failed to load health history')
      }

      const data = await response.json()
      setHistoryData(data.chart_data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHistoryData()
  }, [timeRange, forwarderId])

  const formatTooltipValue = (value: any, name: string) => {
    switch (name) {
      case 'success_rate':
        return [`${value.toFixed(1)}%`, 'Success Rate']
      case 'avg_response_time':
      case 'min_response_time':
      case 'max_response_time':
        return [`${value.toFixed(1)}ms`, name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())]
      default:
        return [value, name]
    }
  }

  const formatXAxisTick = (tickItem: string) => {
    const date = new Date(tickItem)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={loadHistoryData} variant="outline" size="sm">
            Retry
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Health History {forwarderName && `- ${forwarderName}`}
          </h3>
          <p className="text-sm text-gray-500">
            {historyData.length} data points over the last {timeRange} hours
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select
            value={chartType}
            onValueChange={(value) => setChartType(value as 'success_rate' | 'response_time')}
          >
            <option value="success_rate">Success Rate</option>
            <option value="response_time">Response Time</option>
          </Select>
          <Select
            value={timeRange}
            onValueChange={setTimeRange}
          >
            <option value="1">1 Hour</option>
            <option value="6">6 Hours</option>
            <option value="24">24 Hours</option>
            <option value="72">3 Days</option>
            <option value="168">1 Week</option>
          </Select>
          <Button onClick={loadHistoryData} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {historyData.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No health data available for the selected time range</p>
        </div>
      ) : (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'success_rate' ? (
              <AreaChart data={historyData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatXAxisTick}
                  className="text-xs"
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                  className="text-xs"
                />
                <Tooltip
                  formatter={formatTooltipValue}
                  labelFormatter={(label) => formatDateTime(label)}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="success_rate"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            ) : (
              <LineChart data={historyData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatXAxisTick}
                  className="text-xs"
                />
                <YAxis
                  tickFormatter={(value) => `${value}ms`}
                  className="text-xs"
                />
                <Tooltip
                  formatter={formatTooltipValue}
                  labelFormatter={(label) => formatDateTime(label)}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avg_response_time"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="min_response_time"
                  stroke="#10b981"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="max_response_time"
                  stroke="#ef4444"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      )}

      {chartType === 'response_time' && (
        <div className="mt-4 flex items-center justify-center space-x-6 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-blue-500"></div>
            <span>Average</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-green-500 border-dashed border-t"></div>
            <span>Minimum</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-0.5 bg-red-500 border-dashed border-t"></div>
            <span>Maximum</span>
          </div>
        </div>
      )}
    </Card>
  )
}

export default HealthHistoryChart