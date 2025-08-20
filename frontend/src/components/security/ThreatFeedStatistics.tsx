import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChartBarIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { Card, Badge, Modal } from '@/components/ui'
import { formatDateTime, formatRelativeTime } from '@/utils'

interface ThreatFeedStatisticsProps {
  isOpen: boolean
  onClose: () => void
}

interface StatisticsData {
  total_feeds: number
  active_feeds: number
  inactive_feeds: number
  total_rules: number
  rules_by_category: Record<string, number>
  feeds_by_status: Record<string, number>
  update_statistics: {
    successful_updates_24h: number
    failed_updates_24h: number
    pending_updates: number
    never_updated: number
  }
  health_metrics: {
    overall_health_score: number
    feeds_needing_attention: Array<{
      feed_id: number
      feed_name: string
      issues: string[]
    }>
    recommendations: string[]
  }
  feed_details: Array<{
    id: number
    name: string
    feed_type: string
    is_active: boolean
    rules_count: number
    last_updated: string | null
    last_update_status: string | null
    next_update: string | null
    update_frequency: number
    health_issues: string[]
  }>
}

const ThreatFeedStatistics: React.FC<ThreatFeedStatisticsProps> = ({ isOpen, onClose }) => {
  const { data: statistics, isLoading } = useQuery({
    queryKey: ['threat-feed-statistics'],
    queryFn: () => rpzService.getThreatFeedStatistics(),
    enabled: isOpen,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const getHealthColor = (score: number) => {
    if (score >= 90) return 'text-green-600 dark:text-green-400'
    if (score >= 75) return 'text-yellow-600 dark:text-yellow-400'
    if (score >= 50) return 'text-orange-600 dark:text-orange-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getHealthBadge = (score: number) => {
    if (score >= 90) return 'success'
    if (score >= 75) return 'warning'
    if (score >= 50) return 'warning'
    return 'danger'
  }

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-4 w-4 text-green-600" />
      case 'failed':
        return <XCircleIcon className="h-4 w-4 text-red-600" />
      case 'pending':
        return <ClockIcon className="h-4 w-4 text-yellow-600 animate-pulse" />
      default:
        return <ExclamationTriangleIcon className="h-4 w-4 text-gray-400" />
    }
  }

  const stats = statistics?.data as StatisticsData

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Threat Feed Statistics"
      size="xl"
    >
      <div className="space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : stats ? (
          <>
            {/* Overview Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card className="p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ChartBarIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="ml-4">
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {stats.total_feeds}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Total Feeds
                    </div>
                  </div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ShieldCheckIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="ml-4">
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {stats.active_feeds}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Active Feeds
                    </div>
                  </div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ExclamationTriangleIcon className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="ml-4">
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {stats.total_rules.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Total Rules
                    </div>
                  </div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`text-2xl font-bold ${getHealthColor(stats.health_metrics.overall_health_score)}`}>
                      {stats.health_metrics.overall_health_score}%
                    </div>
                  </div>
                  <div className="ml-4">
                    <Badge variant={getHealthBadge(stats.health_metrics.overall_health_score)}>
                      Health Score
                    </Badge>
                  </div>
                </div>
              </Card>
            </div>

            {/* Rules by Category */}
            <Card className="p-6">
              <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                Rules by Category
              </h4>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                {Object.entries(stats.rules_by_category).map(([category, count]) => (
                  <div key={category} className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      {count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                      {category.replace('_', ' ')}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Update Statistics */}
            <Card className="p-6">
              <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                Update Statistics (24h)
              </h4>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="text-xl font-bold text-green-600 dark:text-green-400">
                    {stats.update_statistics.successful_updates_24h}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Successful
                  </div>
                </div>
                <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <div className="text-xl font-bold text-red-600 dark:text-red-400">
                    {stats.update_statistics.failed_updates_24h}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Failed
                  </div>
                </div>
                <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <div className="text-xl font-bold text-yellow-600 dark:text-yellow-400">
                    {stats.update_statistics.pending_updates}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Pending
                  </div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-xl font-bold text-gray-600 dark:text-gray-400">
                    {stats.update_statistics.never_updated}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Never Updated
                  </div>
                </div>
              </div>
            </Card>

            {/* Feed Details */}
            <Card className="p-6">
              <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                Feed Details
              </h4>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Feed
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Rules
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Last Update
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Next Update
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                    {stats.feed_details.map((feed) => (
                      <tr key={feed.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {feed.name}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                              {feed.feed_type.replace('_', ' ')}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(feed.last_update_status)}
                            <Badge variant={feed.is_active ? 'success' : 'default'}>
                              {feed.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          {feed.rules_count.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {feed.last_updated ? formatRelativeTime(feed.last_updated) : 'Never'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {feed.next_update ? formatRelativeTime(feed.next_update) : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Health Issues */}
            {stats.health_metrics.feeds_needing_attention.length > 0 && (
              <Card className="p-6">
                <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                  Feeds Needing Attention
                </h4>
                <div className="space-y-3">
                  {stats.health_metrics.feeds_needing_attention.map((feed) => (
                    <div key={feed.feed_id} className="flex items-center justify-between p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {feed.feed_name}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {feed.issues.join(', ')}
                        </div>
                      </div>
                      <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Recommendations */}
            {stats.health_metrics.recommendations.length > 0 && (
              <Card className="p-6">
                <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                  Recommendations
                </h4>
                <ul className="space-y-2">
                  {stats.health_metrics.recommendations.map((recommendation, index) => (
                    <li key={index} className="flex items-start space-x-3">
                      <CheckCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {recommendation}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">
              No statistics available
            </p>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default ThreatFeedStatistics