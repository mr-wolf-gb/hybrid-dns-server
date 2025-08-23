import React, { useState, useEffect } from 'react'
import {
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline'
import { useHealthMonitoring } from '@/contexts/HealthMonitoringContext'
import { Card, Button, Badge, Select } from '@/components/ui'

interface PerformanceMetrics {
  period_hours: number
  overall_metrics: {
    total_checks: number
    successful_checks: number
    success_rate: number
    failure_rate: number
    avg_response_time: number | null
    min_response_time: number | null
    max_response_time: number | null
    median_response_time?: number | null
    p95_response_time?: number | null
    p99_response_time?: number | null
  }
  forwarder_metrics: Array<{
    forwarder_id: number
    total_checks: number
    successful_checks: number
    success_rate: number
    avg_response_time: number | null
    performance_grade: string
  }>
  performance_grade: string
  generated_at: string
}

const PerformanceMetrics: React.FC = () => {
  const { performanceMetrics: contextMetrics } = useHealthMonitoring()
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(contextMetrics)
  const [loading, setLoading] = useState(false)
  const [timeRange, setTimeRange] = useState('24')

  const loadPerformanceMetrics = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/health/performance?hours=${timeRange}`)
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Error loading performance metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (timeRange !== '24' || !contextMetrics) {
      loadPerformanceMetrics()
    } else {
      setMetrics(contextMetrics)
    }
  }, [timeRange, contextMetrics])

  const getPerformanceGradeColor = (grade: string) => {
    switch (grade) {
      case 'excellent':
        return 'text-green-600 dark:text-green-400'
      case 'good':
        return 'text-blue-600 dark:text-blue-400'
      case 'fair':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'poor':
        return 'text-orange-600 dark:text-orange-400'
      case 'critical':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getPerformanceGradeBadge = (grade: string) => {
    switch (grade) {
      case 'excellent':
        return 'success'
      case 'good':
        return 'primary'
      case 'fair':
        return 'warning'
      case 'poor':
        return 'danger'
      case 'critical':
        return 'danger'
      default:
        return 'default'
    }
  }

  const formatResponseTime = (time: number | null) => {
    if (time === null) return 'N/A'
    return `${time.toFixed(1)}ms`
  }

  const formatNumber = (num: number) => {
    return num.toLocaleString()
  }

  if (loading && !metrics) {
    return (
      <Card className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  if (!metrics) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500">No performance data available</p>
          <Button onClick={loadPerformanceMetrics} variant="outline" size="sm" className="mt-3">
            Load Data
          </Button>
        </div>
      </Card>
    )
  }

  const { overall_metrics } = metrics

  return (
    <div className="space-y-6">
      {/* Overall Performance Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Performance Metrics
            </h3>
            <p className="text-sm text-gray-500">
              Last {metrics.period_hours} hours
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Badge
              variant={getPerformanceGradeBadge(metrics.performance_grade) as any}
              size="lg"
            >
              {metrics.performance_grade.toUpperCase()}
            </Badge>
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
            <Button onClick={loadPerformanceMetrics} variant="outline" size="sm" disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </Button>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
          <div className="text-center">
            <div className="flex items-center justify-center mb-2">
              <CheckCircleIcon className="h-8 w-8 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {(overall_metrics.success_rate ?? 0).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">Success Rate</div>
            <div className="text-xs text-gray-400 mt-1">
              {formatNumber(overall_metrics.successful_checks)} / {formatNumber(overall_metrics.total_checks)}
            </div>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center mb-2">
              <ClockIcon className="h-8 w-8 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatResponseTime(overall_metrics.avg_response_time)}
            </div>
            <div className="text-sm text-gray-500">Avg Response</div>
            <div className="text-xs text-gray-400 mt-1">
              Min: {formatResponseTime(overall_metrics.min_response_time)}
            </div>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center mb-2">
              <ExclamationCircleIcon className="h-8 w-8 text-red-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {(overall_metrics.failure_rate ?? 0).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">Failure Rate</div>
            <div className="text-xs text-gray-400 mt-1">
              {formatNumber(overall_metrics.total_checks - overall_metrics.successful_checks)} failures
            </div>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center mb-2">
              <ChartBarIcon className="h-8 w-8 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(overall_metrics.total_checks)}
            </div>
            <div className="text-sm text-gray-500">Total Checks</div>
            <div className="text-xs text-gray-400 mt-1">
              {((overall_metrics.total_checks ?? 0) / (metrics.period_hours ?? 1)).toFixed(1)}/hour
            </div>
          </div>
        </div>

        {/* Response Time Percentiles */}
        {overall_metrics.median_response_time && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Response Time Distribution
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatResponseTime(overall_metrics.median_response_time)}
                </div>
                <div className="text-xs text-gray-500">Median (P50)</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatResponseTime(overall_metrics.p95_response_time)}
                </div>
                <div className="text-xs text-gray-500">95th Percentile</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatResponseTime(overall_metrics.p99_response_time)}
                </div>
                <div className="text-xs text-gray-500">99th Percentile</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatResponseTime(overall_metrics.max_response_time)}
                </div>
                <div className="text-xs text-gray-500">Maximum</div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Per-Forwarder Performance */}
      {metrics.forwarder_metrics.length > 0 && (
        <Card className="p-6">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Forwarder Performance
          </h4>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {metrics.forwarder_metrics
              .sort((a, b) => b.success_rate - a.success_rate)
              .map((forwarder) => (
                <div
                  key={forwarder.forwarder_id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        Forwarder #{forwarder.forwarder_id}
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatNumber(forwarder.total_checks)} checks
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {forwarder.success_rate.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatResponseTime(forwarder.avg_response_time)}
                      </div>
                    </div>
                    <Badge
                      variant={getPerformanceGradeBadge(forwarder.performance_grade) as any}
                      size="sm"
                    >
                      {forwarder.performance_grade}
                    </Badge>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default PerformanceMetrics