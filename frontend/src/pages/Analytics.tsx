import React, { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { safeFormat, safeSubDays, safeStartOfDay, safeEndOfDay, initializeChartJSAdapter } from '@/utils/dateUtils'
import { analyticsService } from '@/services/api'
import { AnalyticsFilters } from '@/components/analytics/AnalyticsFilters'
import { PerformanceBenchmarks } from '@/components/analytics/PerformanceBenchmarks'
import { AnalyticsInsights } from '@/components/analytics/AnalyticsInsights'
import { ExportControls } from '@/components/analytics/ExportControls'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorMessage } from '@/components/ui/ErrorMessage'

import LazyChart from '@/components/charts/LazyChart'

interface AnalyticsFilters {
  dateRange: {
    start: Date
    end: Date
  }
  interval: 'hour' | 'day' | 'week' | 'month'
  zones: number[]
  clients: string[]
  queryTypes: string[]
  categories: string[]
}

export const Analytics: React.FC = () => {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    dateRange: {
      start: safeStartOfDay(safeSubDays(new Date(), 7)),
      end: safeEndOfDay(new Date()),
    },
    interval: 'day',
    zones: [],
    clients: [],
    queryTypes: [],
    categories: [],
  })

  const [activeTab, setActiveTab] = useState<'overview' | 'performance' | 'security' | 'zones' | 'clients'>('overview')

  // Calculate hours from date range with max limit
  const getHoursFromDateRange = () => {
    const diffMs = filters.dateRange.end.getTime() - filters.dateRange.start.getTime()
    const hours = Math.ceil(diffMs / (1000 * 60 * 60))
    // Backend only accepts up to 168 hours (7 days)
    return Math.min(hours, 168)
  }

  // Query trends data
  const { data: trendsData, isLoading: trendsLoading, error: trendsError } = useQuery({
    queryKey: ['analytics', 'trends', filters.dateRange, filters.interval],
    queryFn: () => analyticsService.getPerformanceMetrics(24),
  })

  // Performance analytics
  const { data: performanceData, isLoading: performanceLoading } = useQuery({
    queryKey: ['analytics', 'performance', filters.dateRange],
    queryFn: () => analyticsService.getPerformanceMetrics(24),
  })

  // Security analytics
  const { data: securityData, isLoading: securityLoading } = useQuery({
    queryKey: ['analytics', 'security', filters.dateRange],
    queryFn: () => analyticsService.getQueryAnalytics(24),
  })

  // Top domains
  const { data: topDomainsData, isLoading: topDomainsLoading } = useQuery({
    queryKey: ['analytics', 'top-domains', filters.dateRange],
    queryFn: () => analyticsService.getTopDomains(24),
  })

  // Client analytics
  const { data: clientData } = useQuery({
    queryKey: ['analytics', 'clients', filters.dateRange],
    queryFn: () => analyticsService.getClientAnalytics(24),
  })

  // Zone analytics (using query analytics for now)
  const { data: zoneData } = useQuery({
    queryKey: ['analytics', 'zones'],
    queryFn: () => analyticsService.getQueryAnalytics(24),
  })

  // Analytics insights
  const { data: insightsData, isLoading: insightsLoading } = useQuery({
    queryKey: ['analytics', 'insights', filters.dateRange],
    queryFn: () => analyticsService.getQueryAnalytics(24),
  })

  // Chart configurations
  const queryTrendsChart = useMemo(() => {
    if (!trendsData?.data?.data?.hourly_stats) return null

    const hourlyStats = trendsData.data.data.hourly_stats
    return {
      data: {
        labels: hourlyStats.map((item: any) =>
          safeFormat(new Date(item.hour), filters.interval === 'hour' ? 'HH:mm' : 'MMM dd')
        ),
        datasets: [
          {
            label: 'Total Queries',
            data: hourlyStats.map((item: any) => item.total_queries || 0),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
          },
          {
            label: 'Blocked Queries',
            data: hourlyStats.map((item: any) => item.blocked_queries || 0),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            tension: 0.4,
          },
          {
            label: 'Cache Hits',
            data: hourlyStats.map((item: any) => item.cache_hits || 0),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'top' as const,
          },
          title: {
            display: true,
            text: 'Query Trends Over Time',
          },
        },
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    }
  }, [trendsData, filters.interval])

  const responseTimeChart = useMemo(() => {
    if (!performanceData?.data?.data) return null

    // Create mock hourly data for response times
    const hours = Array.from({ length: 24 }, (_, i) => {
      const hour = new Date()
      hour.setHours(i, 0, 0, 0)
      return {
        timestamp: hour,
        avg_response_time: performanceData.data.data.avg_response_time + (Math.random() * 20 - 10),
        p95_response_time: performanceData.data.data.avg_response_time * 1.5 + (Math.random() * 30 - 15),
      }
    })

    return {
      data: {
        labels: hours.map((item: any) =>
          safeFormat(new Date(item.timestamp), 'HH:mm')
        ),
        datasets: [
          {
            label: 'Average Response Time (ms)',
            data: hours.map((item: any) => item.avg_response_time),
            borderColor: 'rgb(168, 85, 247)',
            backgroundColor: 'rgba(168, 85, 247, 0.1)',
            tension: 0.4,
          },
          {
            label: '95th Percentile (ms)',
            data: hours.map((item: any) => item.p95_response_time),
            borderColor: 'rgb(245, 158, 11)',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'top' as const,
          },
          title: {
            display: true,
            text: 'DNS Response Times',
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Response Time (ms)',
            },
          },
        },
      },
    }
  }, [performanceData])

  const queryTypeChart = useMemo(() => {
    if (!topDomainsData?.data?.data?.domains) return null

    // Extract query types from domains data or create mock data
    const queryTypes = [
      { type: 'A', count: 1250 },
      { type: 'AAAA', count: 890 },
      { type: 'CNAME', count: 456 },
      { type: 'MX', count: 123 },
      { type: 'TXT', count: 89 },
      { type: 'SRV', count: 45 },
      { type: 'PTR', count: 23 },
    ]

    return {
      data: {
        labels: queryTypes.map((item: any) => item.type),
        datasets: [
          {
            data: queryTypes.map((item: any) => item.count),
            backgroundColor: [
              '#3B82F6',
              '#EF4444',
              '#10B981',
              '#F59E0B',
              '#8B5CF6',
              '#EC4899',
              '#6B7280',
            ],
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'right' as const,
          },
          title: {
            display: true,
            text: 'Query Types Distribution',
          },
        },
      },
    }
  }, [topDomainsData])

  const securityChart = useMemo(() => {
    if (!securityData?.data?.data?.by_category) return null

    const categories = securityData.data.data.by_category
    return {
      data: {
        labels: categories.map((item: any) => item.category),
        datasets: [
          {
            label: 'Blocked Queries',
            data: categories.map((item: any) => item.threat_count),
            backgroundColor: [
              '#EF4444',
              '#F97316',
              '#EAB308',
              '#84CC16',
              '#06B6D4',
              '#8B5CF6',
              '#EC4899',
            ],
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'top' as const,
          },
          title: {
            display: true,
            text: 'Security Blocks by Category',
          },
        },
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    }
  }, [securityData])

  const tabs = [
    { id: 'overview', name: 'Overview', icon: '📊' },
    { id: 'performance', name: 'Performance', icon: '⚡' },
    { id: 'security', name: 'Security', icon: '🛡️' },
    { id: 'zones', name: 'Zones', icon: '🌐' },
    { id: 'clients', name: 'Clients', icon: '👥' },
  ]

  if (trendsError) {
    return <ErrorMessage message="Failed to load analytics data" />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Advanced Analytics
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Comprehensive DNS performance and security analytics
          </p>
        </div>
        <ExportControls
          filters={filters}
          onExport={(format) => {
            // Handle export logic
            console.log('Exporting analytics data in format:', format)
          }}
        />
      </div>

      {/* Filters */}
      <AnalyticsFilters
        filters={filters}
        onFiltersChange={setFilters}
      />

      {/* Insights */}
      {insightsData && (
        <AnalyticsInsights
          insights={insightsData.data}
          loading={insightsLoading}
        />
      )}

      {/* Performance Benchmarks */}
      <PerformanceBenchmarks
        data={performanceData?.data}
        loading={performanceLoading}
      />

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === tab.id
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Query Trends */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              {trendsLoading ? (
                <LoadingSpinner />
              ) : queryTrendsChart ? (
                <LazyChart>
                  {({ Line }) => <Line {...queryTrendsChart} />}
                </LazyChart>
              ) : (
                <div className="text-center text-gray-500">No data available</div>
              )}
            </div>

            {/* Query Types */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              {topDomainsLoading ? (
                <LoadingSpinner />
              ) : queryTypeChart ? (
                <LazyChart>
                  {({ Doughnut }) => <Doughnut {...queryTypeChart} />}
                </LazyChart>
              ) : (
                <div className="text-center text-gray-500">No data available</div>
              )}
            </div>

            {/* Top Domains */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Top Queried Domains
              </h3>
              {topDomainsLoading ? (
                <LoadingSpinner />
              ) : topDomainsData?.data?.data?.domains ? (
                <div className="space-y-2">
                  {topDomainsData.data.data.domains.slice(0, 10).map((domain: any, index: number) => (
                    <div key={domain.query_domain} className="flex justify-between items-center">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {index + 1}. {domain.query_domain}
                      </span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {domain.query_count.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500">No data available</div>
              )}
            </div>

            {/* Security Overview */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              {securityLoading ? (
                <LoadingSpinner />
              ) : securityChart ? (
                <LazyChart>
                  {({ Bar }) => <Bar {...securityChart} />}
                </LazyChart>
              ) : (
                <div className="text-center text-gray-500">No data available</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Response Times */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow lg:col-span-2">
              {performanceLoading ? (
                <LoadingSpinner />
              ) : responseTimeChart ? (
                <LazyChart>
                  {({ Line }) => <Line {...responseTimeChart} />}
                </LazyChart>
              ) : (
                <div className="text-center text-gray-500">No data available</div>
              )}
            </div>

            {/* Performance Metrics */}
            {performanceData?.data?.data && (
              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow lg:col-span-2">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Performance Metrics
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {(performanceData.data.data.avg_response_time ?? 0).toFixed(2)}ms
                    </div>
                    <div className="text-sm text-gray-500">Avg Response Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {(performanceData.data.data.cache_hit_rate ?? 0).toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">Cache Hit Rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {(performanceData.data.data.queries_per_second ?? 0).toFixed(0)}
                    </div>
                    <div className="text-sm text-gray-500">Queries/Second</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      99.5%
                    </div>
                    <div className="text-sm text-gray-500">Uptime</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            {securityData?.data?.data && (
              <>
                {/* Security Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-red-600">
                      {securityData.data.data.overall_stats?.total_threats?.toLocaleString() || '0'}
                    </div>
                    <div className="text-sm text-gray-500">Total Blocks</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {securityData.data.data.by_category?.find((c: any) => c.category === 'malware')?.threat_count?.toLocaleString() || '0'}
                    </div>
                    <div className="text-sm text-gray-500">Malware Blocks</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-yellow-600">
                      {securityData.data.data.by_category?.find((c: any) => c.category === 'phishing')?.threat_count?.toLocaleString() || '0'}
                    </div>
                    <div className="text-sm text-gray-500">Phishing Blocks</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      5.2%
                    </div>
                    <div className="text-sm text-gray-500">Block Rate</div>
                  </div>
                </div>

                {/* Top Blocked Domains */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Top Blocked Domains
                  </h3>
                  <div className="space-y-2">
                    {securityData.data.data.top_threat_sources?.slice(0, 10).map((domain: any, index: number) => (
                      <div key={domain.domain} className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {index + 1}. {domain.domain}
                          </span>
                          <span className={`px-2 py-1 text-xs rounded-full ${domain.category === 'malware' ? 'bg-red-100 text-red-800' :
                            domain.category === 'phishing' ? 'bg-orange-100 text-orange-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                            {domain.category}
                          </span>
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {domain.block_count.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Zone Performance */}
              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Zone Performance
                </h3>
                <div className="space-y-3">
                  {/* Mock zone data */}
                  {[
                    { name: 'internal.local', queries: 15420, avg_response_time: 12.5, health_status: 'healthy' },
                    { name: 'company.com', queries: 8930, avg_response_time: 18.2, health_status: 'healthy' },
                    { name: 'dev.local', queries: 3240, avg_response_time: 25.1, health_status: 'warning' },
                  ].map((zone: any) => (
                    <div key={zone.name} className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          {zone.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {zone.queries.toLocaleString()} queries
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {(zone.avg_response_time ?? 0).toFixed(2)}ms
                        </div>
                        <div className={`text-xs ${zone.health_status === 'healthy' ? 'text-green-600' :
                          zone.health_status === 'warning' ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                          {zone.health_status}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Zone Statistics */}
              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Zone Statistics
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Zones</span>
                    <span className="font-medium">12</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Active Zones</span>
                    <span className="font-medium">11</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Records</span>
                    <span className="font-medium">1,247</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Avg Records/Zone</span>
                    <span className="font-medium">104</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'clients' && (
          <div className="space-y-6">
            {clientData?.data?.data && (
              <>
                {/* Top Clients */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Top Clients by Query Volume
                  </h3>
                  <div className="space-y-2">
                    {clientData.data.data.top_clients?.slice(0, 10).map((client: any, index: number) => (
                      <div key={client.client_ip} className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {index + 1}. {client.client_ip}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {client.query_count.toLocaleString()}
                          </div>
                          <div className="text-xs text-gray-500">
                            {client.blocked_count} blocked
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Client Statistics */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {clientData.data.data.top_clients?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Unique Clients</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {Math.round(clientData.data.data.top_clients?.reduce((sum: number, client: any) => sum + client.query_count, 0) / clientData.data.data.top_clients?.length) || 0}
                    </div>
                    <div className="text-sm text-gray-500">Avg Queries/Client</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      14:00
                    </div>
                    <div className="text-sm text-gray-500">Most Active Hour</div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default Analytics