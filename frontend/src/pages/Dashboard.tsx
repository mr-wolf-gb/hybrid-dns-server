import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChartBarIcon,
  ShieldCheckIcon,
  ServerIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { dashboardService } from '@/services/api'
import { Card, Loading, Badge } from '@/components/ui'
import { formatNumber, formatPercentage, formatRelativeTime, getStatusColor } from '@/utils'
import DashboardChart from '@/components/dashboard/DashboardChart'
import RecentQueriesTable from '@/components/dashboard/RecentQueriesTable'
import ForwarderStatusCard from '@/components/dashboard/ForwarderStatusCard'
import RealTimeQueryMonitor from '@/components/dashboard/RealTimeQueryMonitor'
import RealTimeHealthMonitor from '@/components/health/RealTimeHealthMonitor'
import LiveConfigurationMonitor from '@/components/system/LiveConfigurationMonitor'

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<'overview' | 'realtime' | 'health' | 'config'>('overview')
  const userId = 'current-user' // This would come from auth context in production
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardService.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: recentQueries, isLoading: queriesLoading } = useQuery({
    queryKey: ['recent-queries'],
    queryFn: () => dashboardService.getRecentQueries(10),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading dashboard..." />
      </div>
    )
  }

  const dashboardData = stats?.data

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          DNS Server Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Monitor DNS queries, security filtering, and server health
        </p>
        
        {/* Tab Navigation */}
        <div className="mt-4">
          <nav className="flex space-x-8" aria-label="Tabs">
            {[
              { id: 'overview', name: 'Overview', icon: ChartBarIcon },
              { id: 'realtime', name: 'Real-time Queries', icon: ClockIcon },
              { id: 'health', name: 'Health Monitor', icon: ShieldCheckIcon },
              { id: 'config', name: 'Configuration', icon: ServerIcon }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Queries Today */}
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ChartBarIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Queries Today
                </dt>
                <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {formatNumber(dashboardData?.total_queries_today || 0)}
                </dd>
              </dl>
            </div>
          </div>
        </Card>

        {/* Blocked Queries Today */}
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ShieldCheckIcon className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Blocked Today
                </dt>
                <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {formatNumber(dashboardData?.blocked_queries_today || 0)}
                  <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                    ({formatPercentage(
                      dashboardData?.blocked_queries_today || 0,
                      dashboardData?.total_queries_today || 0
                    )})
                  </span>
                </dd>
              </dl>
            </div>
          </div>
        </Card>

        {/* Cache Hit Rate */}
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ClockIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Cache Hit Rate
                </dt>
                <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {(dashboardData?.cache_hit_rate || 0).toFixed(1)}%
                </dd>
              </dl>
            </div>
          </div>
        </Card>

        {/* Active Zones */}
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ServerIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Active Zones
                </dt>
                <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {dashboardData?.active_zones || 0}
                </dd>
              </dl>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts and tables grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Query volume chart */}
        <Card
          title="Query Volume (24h)"
          description="DNS queries over the last 24 hours"
        >
          {dashboardData?.queries_per_hour && (
            <DashboardChart data={dashboardData.queries_per_hour} />
          )}
        </Card>

        {/* Forwarder status */}
        <Card
          title="Forwarder Health"
          description="Status of DNS forwarders"
        >
          {dashboardData?.forwarder_health && (
            <ForwarderStatusCard forwarders={dashboardData.forwarder_health} />
          )}
        </Card>
      </div>

      {/* Top domains and recent queries */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Top domains */}
        <Card
          title="Top Domains"
          description="Most queried domains today"
        >
          <div className="space-y-3">
            {dashboardData?.top_domains?.slice(0, 8).map((domain, index) => (
              <div key={index} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {domain.domain}
                </span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {formatNumber(domain.count)}
                </span>
              </div>
            )) || (
              <p className="text-sm text-gray-500 dark:text-gray-400">No data available</p>
            )}
          </div>
        </Card>

        {/* Blocked domains */}
        <Card
          title="Blocked Domains"
          description="Recently blocked domains"
        >
          <div className="space-y-3">
            {dashboardData?.blocked_domains?.slice(0, 8).map((domain, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate block">
                    {domain.domain}
                  </span>
                  <Badge variant="danger" size="sm" className="mt-1">
                    {domain.category}
                  </Badge>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                  {formatNumber(domain.count)}
                </span>
              </div>
            )) || (
              <p className="text-sm text-gray-500 dark:text-gray-400">No blocked domains</p>
            )}
          </div>
        </Card>

        {/* Recent queries */}
        <Card
          title="Recent Queries"
          description="Latest DNS queries"
        >
          {queriesLoading ? (
            <Loading text="Loading queries..." />
          ) : (
            <RecentQueriesTable queries={recentQueries?.data || []} />
          )}
        </Card>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <>
          {/* Stats overview */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {/* Total Queries Today */}
            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ChartBarIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Queries Today
                    </dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                      {formatNumber(dashboardData?.total_queries_today || 0)}
                    </dd>
                  </dl>
                </div>
              </div>
            </Card>

            {/* Blocked Queries Today */}
            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ShieldCheckIcon className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Blocked Today
                    </dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                      {formatNumber(dashboardData?.blocked_queries_today || 0)}
                      <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                        ({formatPercentage(
                          dashboardData?.blocked_queries_today || 0,
                          dashboardData?.total_queries_today || 0
                        )})
                      </span>
                    </dd>
                  </dl>
                </div>
              </div>
            </Card>

            {/* Cache Hit Rate */}
            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ClockIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Cache Hit Rate
                    </dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                      {(dashboardData?.cache_hit_rate || 0).toFixed(1)}%
                    </dd>
                  </dl>
                </div>
              </div>
            </Card>

            {/* Active Zones */}
            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ServerIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="ml-4 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Active Zones
                    </dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-gray-100">
                      {dashboardData?.active_zones || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </Card>
          </div>

          {/* Charts and tables grid */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Query volume chart */}
            <Card
              title="Query Volume (24h)"
              description="DNS queries over the last 24 hours"
            >
              {dashboardData?.queries_per_hour && (
                <DashboardChart data={dashboardData.queries_per_hour} />
              )}
            </Card>

            {/* Forwarder status */}
            <Card
              title="Forwarder Health"
              description="Status of DNS forwarders"
            >
              {dashboardData?.forwarder_health && (
                <ForwarderStatusCard forwarders={dashboardData.forwarder_health} />
              )}
            </Card>
          </div>

          {/* Top domains and recent queries */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Top domains */}
            <Card
              title="Top Domains"
              description="Most queried domains today"
            >
              <div className="space-y-3">
                {dashboardData?.top_domains?.slice(0, 8).map((domain, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {domain.domain}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {formatNumber(domain.count)}
                    </span>
                  </div>
                )) || (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No data available</p>
                )}
              </div>
            </Card>

            {/* Blocked domains */}
            <Card
              title="Blocked Domains"
              description="Recently blocked domains"
            >
              <div className="space-y-3">
                {dashboardData?.blocked_domains?.slice(0, 8).map((domain, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate block">
                        {domain.domain}
                      </span>
                      <Badge variant="danger" size="sm" className="mt-1">
                        {domain.category}
                      </Badge>
                    </div>
                    <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                      {formatNumber(domain.count)}
                    </span>
                  </div>
                )) || (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No blocked domains</p>
                )}
              </div>
            </Card>

            {/* Recent queries */}
            <Card
              title="Recent Queries"
              description="Latest DNS queries"
            >
              {queriesLoading ? (
                <Loading text="Loading queries..." />
              ) : (
                <RecentQueriesTable queries={recentQueries?.data || []} />
              )}
            </Card>
          </div>

          {/* System alerts */}
          {dashboardData?.healthy_forwarders !== dashboardData?.total_forwarders && (
            <Card className="border-yellow-200 dark:border-yellow-800">
              <div className="flex items-start space-x-3">
                <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Forwarder Health Alert
                  </h3>
                  <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                    {(dashboardData?.total_forwarders || 0) - (dashboardData?.healthy_forwarders || 0)} out of{' '}
                    {dashboardData?.total_forwarders || 0} forwarders are experiencing issues.
                  </p>
                </div>
              </div>
            </Card>
          )}
        </>
      )}

      {activeTab === 'realtime' && (
        <RealTimeQueryMonitor userId={userId} />
      )}

      {activeTab === 'health' && (
        <RealTimeHealthMonitor userId={userId} />
      )}

      {activeTab === 'config' && (
        <LiveConfigurationMonitor userId={userId} />
      )}
    </div>
  )
}

export default Dashboard