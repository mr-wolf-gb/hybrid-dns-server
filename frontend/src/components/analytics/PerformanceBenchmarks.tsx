import React from 'react'
import { 
  ClockIcon, 
  CpuChipIcon, 
  ServerIcon, 
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface PerformanceBenchmark {
  metric: string
  current: number
  target: number
  unit: string
  status: 'good' | 'warning' | 'critical'
  trend: 'up' | 'down' | 'stable'
  description: string
}

interface PerformanceBenchmarksProps {
  data?: {
    benchmarks?: PerformanceBenchmark[]
    avg_response_time?: number
    cache_hit_rate?: number
    queries_per_second?: number
    uptime_percentage?: number
    error_rate?: number
    memory_usage?: number
    cpu_usage?: number
  }
  loading: boolean
}

export const PerformanceBenchmarks: React.FC<PerformanceBenchmarksProps> = ({
  data,
  loading,
}) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Performance Benchmarks
        </h3>
        <LoadingSpinner />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Performance Benchmarks
        </h3>
        <div className="text-center text-gray-500">No performance data available</div>
      </div>
    )
  }

  // Create benchmarks from available data
  const benchmarks: PerformanceBenchmark[] = [
    {
      metric: 'Response Time',
      current: data.avg_response_time || 0,
      target: 50,
      unit: 'ms',
      status: (data.avg_response_time || 0) <= 50 ? 'good' : 
              (data.avg_response_time || 0) <= 100 ? 'warning' : 'critical',
      trend: 'stable',
      description: 'Average DNS query response time'
    },
    {
      metric: 'Cache Hit Rate',
      current: data.cache_hit_rate || 0,
      target: 85,
      unit: '%',
      status: (data.cache_hit_rate || 0) >= 85 ? 'good' : 
              (data.cache_hit_rate || 0) >= 70 ? 'warning' : 'critical',
      trend: 'up',
      description: 'Percentage of queries served from cache'
    },
    {
      metric: 'Queries Per Second',
      current: data.queries_per_second || 0,
      target: 1000,
      unit: 'qps',
      status: (data.queries_per_second || 0) >= 800 ? 'good' : 
              (data.queries_per_second || 0) >= 500 ? 'warning' : 'critical',
      trend: 'stable',
      description: 'DNS queries processed per second'
    },
    {
      metric: 'Uptime',
      current: data.uptime_percentage || 0,
      target: 99.9,
      unit: '%',
      status: (data.uptime_percentage || 0) >= 99.9 ? 'good' : 
              (data.uptime_percentage || 0) >= 99.5 ? 'warning' : 'critical',
      trend: 'stable',
      description: 'System availability percentage'
    },
    {
      metric: 'Error Rate',
      current: data.error_rate || 0,
      target: 1,
      unit: '%',
      status: (data.error_rate || 0) <= 1 ? 'good' : 
              (data.error_rate || 0) <= 3 ? 'warning' : 'critical',
      trend: 'down',
      description: 'Percentage of failed DNS queries'
    },
    {
      metric: 'Memory Usage',
      current: data.memory_usage || 0,
      target: 80,
      unit: '%',
      status: (data.memory_usage || 0) <= 80 ? 'good' : 
              (data.memory_usage || 0) <= 90 ? 'warning' : 'critical',
      trend: 'stable',
      description: 'System memory utilization'
    },
    {
      metric: 'CPU Usage',
      current: data.cpu_usage || 0,
      target: 70,
      unit: '%',
      status: (data.cpu_usage || 0) <= 70 ? 'good' : 
              (data.cpu_usage || 0) <= 85 ? 'warning' : 'critical',
      trend: 'stable',
      description: 'System CPU utilization'
    },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'critical':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
      default:
        return <ChartBarIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400'
      case 'critical':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400'
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '↗️'
      case 'down':
        return '↘️'
      case 'stable':
        return '→'
      default:
        return '→'
    }
  }

  const getProgressPercentage = (current: number, target: number, isInverse = false) => {
    if (isInverse) {
      // For metrics where lower is better (like error rate)
      return Math.max(0, Math.min(100, ((target - current) / target) * 100))
    }
    return Math.max(0, Math.min(100, (current / target) * 100))
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
          <ChartBarIcon className="h-5 w-5 mr-2" />
          Performance Benchmarks
        </h3>
        <div className="flex items-center space-x-4 text-sm">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <span className="text-gray-600 dark:text-gray-400">Good</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
            <span className="text-gray-600 dark:text-gray-400">Warning</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
            <span className="text-gray-600 dark:text-gray-400">Critical</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {benchmarks.map((benchmark) => {
          const isInverse = benchmark.metric === 'Error Rate'
          const progressPercentage = getProgressPercentage(
            benchmark.current, 
            benchmark.target, 
            isInverse
          )

          return (
            <div
              key={benchmark.metric}
              className={`p-4 rounded-lg border-2 ${
                benchmark.status === 'good' ? 'border-green-200 dark:border-green-800' :
                benchmark.status === 'warning' ? 'border-yellow-200 dark:border-yellow-800' :
                'border-red-200 dark:border-red-800'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(benchmark.status)}
                  <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                    {benchmark.metric}
                  </h4>
                </div>
                <span className="text-xs">{getTrendIcon(benchmark.trend)}</span>
              </div>

              <div className="mb-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-gray-900 dark:text-white">
                    {benchmark.current.toFixed(benchmark.unit === '%' ? 1 : 0)}
                  </span>
                  <span className="text-sm text-gray-500">
                    {benchmark.unit}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  Target: {benchmark.target}{benchmark.unit}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-2">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      benchmark.status === 'good' ? 'bg-green-500' :
                      benchmark.status === 'warning' ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${progressPercentage}%` }}
                  ></div>
                </div>
              </div>

              {/* Status Badge */}
              <div className="flex items-center justify-between">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(benchmark.status)}`}>
                  {benchmark.status.toUpperCase()}
                </span>
                <span className="text-xs text-gray-500">
                  {progressPercentage.toFixed(0)}%
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-gray-500 mt-2">
                {benchmark.description}
              </p>
            </div>
          )
        })}
      </div>

      {/* Summary */}
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <h4 className="font-medium text-gray-900 dark:text-white mb-2">
          Performance Summary
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600 dark:text-gray-400">Good: </span>
            <span className="font-medium text-green-600">
              {benchmarks.filter(b => b.status === 'good').length} metrics
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Warning: </span>
            <span className="font-medium text-yellow-600">
              {benchmarks.filter(b => b.status === 'warning').length} metrics
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Critical: </span>
            <span className="font-medium text-red-600">
              {benchmarks.filter(b => b.status === 'critical').length} metrics
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}