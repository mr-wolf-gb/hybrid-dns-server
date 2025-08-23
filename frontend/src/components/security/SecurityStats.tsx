import React from 'react'
import { Line, Doughnut, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement,
} from 'chart.js'
import { Card } from '@/components/ui'
import { formatNumber, getCategoryColor } from '@/utils'
import { DNSLog } from '@/types'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement
)

interface SecurityStatsProps {
  categoryStats: Record<string, number>
  securityStats?: {
    blocked_today: number
    blocked_this_week: number
    blocked_this_month: number
    top_blocked_domains: Array<{ domain: string; count: number; category: string }>
    blocks_by_hour: Array<{ hour: string; count: number }>
    threat_feed_stats: Array<{ feed: string; rules: number; last_update: string }>
  }
  blockedQueries: DNSLog[]
}

const SecurityStats: React.FC<SecurityStatsProps> = ({
  categoryStats,
  securityStats,
  blockedQueries,
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

  const blocksOverTimeData = {
    labels: securityStats?.blocks_by_hour?.map(item => item.hour) || [],
    datasets: [
      {
        label: 'Blocked Queries',
        data: securityStats?.blocks_by_hour?.map(item => item.count) || [],
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  }

  const topBlockedDomainsData = {
    labels: securityStats?.top_blocked_domains?.slice(0, 10).map(item => item.domain) || [],
    datasets: [
      {
        label: 'Blocked Count',
        data: securityStats?.top_blocked_domains?.slice(0, 10).map(item => item.count) || [],
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderColor: '#ef4444',
        borderWidth: 1,
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
            <Doughnut data={categoryChartData} options={chartOptions} />
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
          {securityStats?.blocks_by_hour?.length ? (
            <Line data={blocksOverTimeData} options={chartOptions} />
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
          {securityStats?.top_blocked_domains?.length ? (
            <Bar data={topBlockedDomainsData} options={barChartOptions} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              No blocked domains data available
            </div>
          )}
        </div>
      </Card>

      {/* Threat Feed Status */}
      <Card
        title="Threat Feed Status"
        description="Status of configured threat feeds"
        className="col-span-1"
      >
        <div className="space-y-4">
          {securityStats?.threat_feed_stats?.length ? (
            securityStats.threat_feed_stats.map((feed, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {feed.feed}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {formatNumber(feed.rules)} rules
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Updated
                  </div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {(() => {
                      try {
                        const date = new Date(feed.last_update);
                        return isNaN(date.getTime()) ? 'Invalid date' : date.toLocaleDateString();
                      } catch {
                        return 'Invalid date';
                      }
                    })()}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              No threat feeds configured
            </div>
          )}
        </div>
      </Card>

      {/* Security Summary */}
      <Card
        title="Security Summary"
        description="Key security metrics"
        className="col-span-1 lg:col-span-3"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <div className="text-3xl font-bold text-red-600 dark:text-red-400">
              {formatNumber(securityStats?.blocked_today || 0)}
            </div>
            <div className="text-sm text-red-700 dark:text-red-300">
              Blocked Today
            </div>
          </div>

          <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
            <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
              {formatNumber(securityStats?.blocked_this_week || 0)}
            </div>
            <div className="text-sm text-orange-700 dark:text-orange-300">
              Blocked This Week
            </div>
          </div>

          <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {formatNumber(securityStats?.blocked_this_month || 0)}
            </div>
            <div className="text-sm text-purple-700 dark:text-purple-300">
              Blocked This Month
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
                      {query.query_domain}
                    </span>
                    {query.blocked_category && (
                      <span className={`px-2 py-1 rounded-full text-xs ${getCategoryColor(query.blocked_category)}`}>
                        {query.blocked_category.replace('_', ' ')}
                      </span>
                    )}
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