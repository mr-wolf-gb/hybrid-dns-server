import React from 'react'
// Chart.js will be loaded dynamically
import LazyChart from '@/components/charts/LazyChart'
import { Card } from '@/components/ui'
import { formatNumber, getCategoryColor } from '@/utils'
import { DNSLog } from '@/types'

// Chart.js registration will be handled by LazyChart

interface SecurityStatsProps {
  categoryStats: Record<string, number>
  securityStats?: {
    total_rules: number
    active_rules: number
    inactive_rules: number
    rules_by_action: Record<string, number>
    rules_by_source: Record<string, number>
    rules_by_category: Record<string, number>
  }
  blockedQueries: Array<{
    id: number
    timestamp: string
    client_ip: string
    domain: string
    category: string
    action: string
    rpz_zone: string
  }>
  threatIntelStats?: {
    threat_feeds: {
      total_feeds: number
      active_feeds: number
      feeds_by_type: Record<string, number>
      total_rules_from_feeds: number
    }
    protection_coverage: {
      total_domains_protected: number
      active_threat_feeds: number
      custom_lists: number
      external_feeds: number
    }
    update_health: {
      feeds_up_to_date: number
      feeds_with_errors: number
      feeds_never_updated: number
    }
  }
}

const SecurityStats: React.FC<SecurityStatsProps> = ({
  categoryStats,
  securityStats,
  blockedQueries,
  threatIntelStats,
}) => {
  // Prepare chart data
  const categoryChartData = {
    labels: Object.keys(categoryStats).map(cat => cat.replace('_', ' ')),
    datasets: [
      {
        data: Object.values(categoryStats),
        backgroundColor: [
          '#ef4444', // red for malware/phishing
          '#3b82f6', // blue for social media
          '#8b5cf6', // purple for adult/gambling
          '#f59e0b', // orange for custom
          '#10b981', // green for other
          '#6b7280', // gray for misc
        ],
        borderWidth: 0,
      },
    ],
  }

  // Process blocked queries for time-based chart
  const hourlyBlocks = blockedQueries.reduce((acc, query) => {
    const hour = new Date(query.timestamp).getHours()
    acc[hour] = (acc[hour] || 0) + 1
    return acc
  }, {} as Record<number, number>)

  const blocksOverTimeData = {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      {
        label: 'Blocked Queries',
        data: Array.from({ length: 24 }, (_, i) => hourlyBlocks[i] || 0),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  }

  // Process top blocked domains from recent queries
  const domainCounts = blockedQueries.reduce((acc, query) => {
    acc[query.domain] = (acc[query.domain] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const topDomains = Object.entries(domainCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)

  const topBlockedDomainsData = {
    labels: topDomains.map(([domain]) => domain.length > 20 ? domain.substring(0, 20) + '...' : domain),
    datasets: [
      {
        label: 'Blocked Count',
        data: topDomains.map(([, count]) => count),
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderColor: '#ef4444',
        borderWidth: 1,
      },
    ],
  }

  // Action distribution chart
  const actionChartData = {
    labels: Object.keys(securityStats?.rules_by_action || {}),
    datasets: [
      {
        data: Object.values(securityStats?.rules_by_action || {}),
        backgroundColor: [
          '#ef4444', // red for block
          '#f59e0b', // orange for redirect
          '#10b981', // green for passthru
        ],
        borderWidth: 0,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  }

  const barChartOptions = {
    ...chartOptions,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
      {/* Category Distribution */}
      <Card
        title="Rule Categories"
        description="Distribution of rules by category"
        className="col-span-1"
      >
        <div className="h-64">
          {Object.keys(categoryStats).length > 0 ? (
            <LazyChart>
              {({ Doughnut }) => (
                <Doughnut data={categoryChartData} options={chartOptions} />
              )}
            </LazyChart>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              No category data available
            </div>
          )}
        </div>
      </Card>

      {/* Blocks Over Time */}
      <Card
        title="Blocked Queries (24h)"
        description="Blocked queries over the last 24 hours"
        className="col-span-1 lg:col-span-2"
      >
        <div className="h-64">
          {blockedQueries.length > 0 ? (
            <LazyChart>
              {({ Line }) => (
                <Line data={blocksOverTimeData} options={chartOptions} />
              )}
            </LazyChart>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              No blocking data available
            </div>
          )}
        </div>
      </Card>

      {/* Top Blocked Domains */}
      <Card
        title="Top Blocked Domains"
        description="Most frequently blocked domains"
        className="col-span-1 lg:col-span-2"
      >
        <div className="h-64">
          {topDomains.length > 0 ? (
            <LazyChart>
              {({ Bar }) => (
                <Bar data={topBlockedDomainsData} options={barChartOptions} />
              )}
            </LazyChart>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              No blocked domains data available
            </div>
          )}
        </div>
      </Card>

      {/* Rule Actions Distribution */}
      <Card
        title="Rule Actions"
        description="Distribution of rule actions"
        className="col-span-1"
      >
        <div className="h-64">
          {securityStats?.rules_by_action && Object.keys(securityStats.rules_by_action).length > 0 ? (
            <LazyChart>
              {({ Doughnut }) => (
                <Doughnut data={actionChartData} options={chartOptions} />
              )}
            </LazyChart>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              No action data available
            </div>
          )}
        </div>
      </Card>

      {/* Threat Intelligence Summary */}
      <Card
        title="Threat Intelligence"
        description="Threat feed and protection coverage"
        className="col-span-1 lg:col-span-3"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {formatNumber(threatIntelStats?.threat_feeds?.total_feeds || 0)}
            </div>
            <div className="text-sm text-blue-700 dark:text-blue-300">
              Total Feeds
            </div>
          </div>

          <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatNumber(threatIntelStats?.threat_feeds?.active_feeds || 0)}
            </div>
            <div className="text-sm text-green-700 dark:text-green-300">
              Active Feeds
            </div>
          </div>

          <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {formatNumber(threatIntelStats?.protection_coverage?.total_domains_protected || 0)}
            </div>
            <div className="text-sm text-purple-700 dark:text-purple-300">
              Protected Domains
            </div>
          </div>

          <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
            <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
              {formatNumber(threatIntelStats?.update_health?.feeds_up_to_date || 0)}
            </div>
            <div className="text-sm text-orange-700 dark:text-orange-300">
              Up to Date
            </div>
          </div>
        </div>

        {/* Recent Blocked Queries */}
        {blockedQueries.length > 0 && (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Recent Blocked Queries
            </h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {blockedQueries.slice(0, 10).map((query, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded text-sm">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-gray-900 dark:text-gray-100">
                      {query.domain}
                    </span>
                    {query.category && (
                      <span className={`px-2 py-1 rounded-full text-xs ${getCategoryColor(query.category)}`}>
                        {query.category.replace('_', ' ')}
                      </span>
                    )}
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {query.client_ip}
                    </span>
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">
                    {(() => {
                      try {
                        const date = new Date(query.timestamp);
                        return isNaN(date.getTime()) ? 'Invalid time' : date.toLocaleTimeString();
                      } catch {
                        return 'Invalid time';
                      }
                    })()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default SecurityStats