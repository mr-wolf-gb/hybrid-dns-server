import React from 'react'
import { 
  LightBulbIcon, 
  TrendingUpIcon, 
  TrendingDownIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface Insight {
  id: string
  type: 'performance' | 'security' | 'capacity' | 'optimization' | 'alert'
  severity: 'info' | 'warning' | 'critical' | 'success'
  title: string
  description: string
  recommendation?: string
  metric?: {
    value: number
    change: number
    unit: string
  }
  trend?: 'up' | 'down' | 'stable'
  actionable: boolean
}

interface AnalyticsInsightsProps {
  insights?: Insight[]
  loading: boolean
}

export const AnalyticsInsights: React.FC<AnalyticsInsightsProps> = ({
  insights,
  loading,
}) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Analytics Insights
        </h3>
        <LoadingSpinner />
      </div>
    )
  }

  // Mock insights if none provided
  const defaultInsights: Insight[] = [
    {
      id: '1',
      type: 'performance',
      severity: 'warning',
      title: 'Response Time Increase',
      description: 'DNS response times have increased by 15% over the last 24 hours',
      recommendation: 'Consider reviewing forwarder health and cache configuration',
      metric: { value: 45.2, change: 15, unit: 'ms' },
      trend: 'up',
      actionable: true,
    },
    {
      id: '2',
      type: 'security',
      severity: 'success',
      title: 'Threat Blocking Effective',
      description: 'Successfully blocked 2,847 malicious domains in the last 24 hours',
      metric: { value: 2847, change: 12, unit: 'blocks' },
      trend: 'up',
      actionable: false,
    },
    {
      id: '3',
      type: 'capacity',
      severity: 'info',
      title: 'Query Volume Growth',
      description: 'DNS query volume has grown by 8% compared to last week',
      recommendation: 'Monitor resource usage and consider scaling if trend continues',
      metric: { value: 125000, change: 8, unit: 'queries/day' },
      trend: 'up',
      actionable: true,
    },
    {
      id: '4',
      type: 'optimization',
      severity: 'warning',
      title: 'Cache Hit Rate Below Target',
      description: 'Cache hit rate is 78%, below the recommended 85% threshold',
      recommendation: 'Review cache TTL settings and consider increasing cache size',
      metric: { value: 78, change: -3, unit: '%' },
      trend: 'down',
      actionable: true,
    },
    {
      id: '5',
      type: 'alert',
      severity: 'critical',
      title: 'Forwarder Health Issue',
      description: 'Primary AD forwarder showing intermittent connectivity issues',
      recommendation: 'Check network connectivity and consider failover configuration',
      actionable: true,
    },
  ]

  const displayInsights = insights || defaultInsights

  const getInsightIcon = (type: string, severity: string) => {
    switch (type) {
      case 'performance':
        return <TrendingUpIcon className="h-5 w-5" />
      case 'security':
        return <CheckCircleIcon className="h-5 w-5" />
      case 'capacity':
        return <InformationCircleIcon className="h-5 w-5" />
      case 'optimization':
        return <LightBulbIcon className="h-5 w-5" />
      case 'alert':
        return <ExclamationTriangleIcon className="h-5 w-5" />
      default:
        return <InformationCircleIcon className="h-5 w-5" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'success':
        return 'text-green-600 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400'
      case 'info':
        return 'text-blue-600 bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-400'
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200 dark:bg-gray-900/20 dark:border-gray-800 dark:text-gray-400'
    }
  }

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon className="h-4 w-4 text-green-500" />
      case 'down':
        return <TrendingDownIcon className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'performance':
        return 'Performance'
      case 'security':
        return 'Security'
      case 'capacity':
        return 'Capacity'
      case 'optimization':
        return 'Optimization'
      case 'alert':
        return 'Alert'
      default:
        return 'Insight'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
          <LightBulbIcon className="h-5 w-5 mr-2" />
          Analytics Insights
        </h3>
        <div className="text-sm text-gray-500">
          {displayInsights.filter(i => i.actionable).length} actionable insights
        </div>
      </div>

      {displayInsights.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <LightBulbIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No insights available for the selected time period</p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayInsights.map((insight) => (
            <div
              key={insight.id}
              className={`p-4 rounded-lg border-2 ${getSeverityColor(insight.severity)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className="flex-shrink-0">
                    {getInsightIcon(insight.type, insight.severity)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {insight.title}
                      </h4>
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-white/50 dark:bg-black/20">
                        {getTypeLabel(insight.type)}
                      </span>
                      {insight.actionable && (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                          Actionable
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                      {insight.description}
                    </p>
                    {insight.recommendation && (
                      <div className="bg-white/50 dark:bg-black/20 p-3 rounded-md">
                        <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                          Recommendation:
                        </p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {insight.recommendation}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                
                {insight.metric && (
                  <div className="flex-shrink-0 text-right ml-4">
                    <div className="flex items-center space-x-1">
                      <span className="text-lg font-bold text-gray-900 dark:text-white">
                        {insight.metric.value.toLocaleString()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {insight.metric.unit}
                      </span>
                      {getTrendIcon(insight.trend)}
                    </div>
                    {insight.metric.change !== 0 && (
                      <div className={`text-sm ${
                        insight.metric.change > 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {insight.metric.change > 0 ? '+' : ''}{insight.metric.change}%
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <h4 className="font-medium text-gray-900 dark:text-white mb-2">
          Insights Summary
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600 dark:text-gray-400">Critical: </span>
            <span className="font-medium text-red-600">
              {displayInsights.filter(i => i.severity === 'critical').length}
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Warning: </span>
            <span className="font-medium text-yellow-600">
              {displayInsights.filter(i => i.severity === 'warning').length}
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Info: </span>
            <span className="font-medium text-blue-600">
              {displayInsights.filter(i => i.severity === 'info').length}
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Success: </span>
            <span className="font-medium text-green-600">
              {displayInsights.filter(i => i.severity === 'success').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}