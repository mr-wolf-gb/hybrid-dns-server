import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
    ChartBarIcon,
    DocumentArrowDownIcon,
    CalendarIcon,
    FunnelIcon,
} from '@heroicons/react/24/outline'
import LazyChart from '@/components/charts/LazyChart'
import { rpzService } from '@/services/api'
import { Card, Button, Select, Badge } from '@/components/ui'
import { formatNumber, formatDateTime } from '@/utils'
// import { BlockedQueryReport, ThreatDetectionReport } from '@/types'

interface SecurityAnalyticsProps {
    isOpen: boolean
    onClose: () => void
}

const SecurityAnalytics: React.FC<SecurityAnalyticsProps> = ({
    isOpen,
    onClose,
}) => {
    const [timeRange, setTimeRange] = useState(24)
    const [reportDays, setReportDays] = useState(30)
    const [categoryFilter, setCategoryFilter] = useState('all')

    // Fetch blocked queries
    const { data: blockedQueries, isLoading: queriesLoading } = useQuery({
        queryKey: ['blocked-queries-analytics', timeRange, categoryFilter],
        queryFn: () => rpzService.getBlockedQueries({
            hours: timeRange,
            category: categoryFilter !== 'all' ? categoryFilter : undefined,
            limit: 1000
        }),
        enabled: isOpen,
        refetchInterval: 60000,
    })

    // Fetch threat detection report
    const { data: threatReport, isLoading: reportLoading } = useQuery({
        queryKey: ['threat-detection-analytics', reportDays],
        queryFn: () => rpzService.getThreatDetectionReport({
            days: reportDays,
            include_details: true,
        }),
        enabled: isOpen,
        refetchInterval: 300000,
    })

    // Fetch category statistics
    const { data: categoryStats } = useQuery({
        queryKey: ['category-statistics-analytics', timeRange],
        queryFn: () => rpzService.getCategoryStatistics({
            time_period: timeRange,
            include_inactive: false,
        }),
        enabled: isOpen,
        refetchInterval: 300000,
    })

    if (!isOpen) return null

    const queries = blockedQueries?.data
    const report = threatReport?.data
    const categories = categoryStats?.data

    // Prepare chart data
    const hourlyBlocksData = {
        labels: queries?.hourly_breakdown?.map(item => item.hour) || [],
        datasets: [
            {
                label: 'Blocked Queries',
                data: queries?.hourly_breakdown?.map(item => item.blocked_count) || [],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true,
            },
        ],
    }

    const categoryDistributionData = {
        labels: Object.keys(report?.threat_categories || {}),
        datasets: [
            {
                data: Object.values(report?.threat_categories || {}).map((cat: any) => cat.blocked_count),
                backgroundColor: [
                    '#ef4444', // red
                    '#f59e0b', // orange
                    '#8b5cf6', // purple
                    '#10b981', // green
                    '#3b82f6', // blue
                    '#6b7280', // gray
                ],
                borderWidth: 0,
            },
        ],
    }

    const threatTimelineData = {
        labels: report?.threat_timeline?.map(item => item.date) || [],
        datasets: [
            {
                label: 'Daily Threats',
                data: report?.threat_timeline?.map(item => item.blocked_count) || [],
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                tension: 0.4,
                fill: true,
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
        <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />

                <div className="inline-block w-full max-w-7xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white dark:bg-gray-800 shadow-xl rounded-lg">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                Security Analytics
                            </h2>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                Detailed analysis of blocked queries and threat patterns
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <Select
                                value={timeRange.toString()}
                                onChange={(e) => setTimeRange(parseInt(e.target.value))}
                                options={[
                                    { value: '1', label: 'Last hour' },
                                    { value: '24', label: 'Last 24 hours' },
                                    { value: '168', label: 'Last week' },
                                    { value: '720', label: 'Last month' },
                                ]}
                            />
                            <Select
                                value={categoryFilter}
                                onChange={(e) => setCategoryFilter(e.target.value)}
                                options={[
                                    { value: 'all', label: 'All categories' },
                                    { value: 'malware', label: 'Malware' },
                                    { value: 'phishing', label: 'Phishing' },
                                    { value: 'adult', label: 'Adult content' },
                                    { value: 'social-media', label: 'Social media' },
                                    { value: 'gambling', label: 'Gambling' },
                                ]}
                            />
                            <Button variant="outline" onClick={onClose}>
                                Close
                            </Button>
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 gap-4 mb-6 sm:grid-cols-2 lg:grid-cols-4">
                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <ChartBarIcon className="w-8 h-8 text-red-600 dark:text-red-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {formatNumber(queries?.summary?.total_blocked || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Total Blocked
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <DocumentArrowDownIcon className="w-8 h-8 text-orange-600 dark:text-orange-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {formatNumber(queries?.summary?.unique_domains || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Unique Domains
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <FunnelIcon className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {formatNumber(queries?.summary?.unique_clients || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Unique Clients
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <CalendarIcon className="w-8 h-8 text-green-600 dark:text-green-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {Math.round(report?.executive_summary?.average_daily_blocks || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Daily Average
                                    </p>
                                </div>
                            </div>
                        </Card>
                    </div>

                    {/* Charts */}
                    <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-2">
                        {/* Hourly Blocks */}
                        <Card
                            title="Blocked Queries Over Time"
                            description={`Hourly breakdown for the last ${timeRange} hours`}
                        >
                            <div className="h-64">
                                {queries?.hourly_breakdown?.length ? (
                                    <LazyChart>
                                        {({ Line }) => (
                                            <Line data={hourlyBlocksData} options={chartOptions} />
                                        )}
                                    </LazyChart>
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        No data available for selected time range
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* Category Distribution */}
                        <Card
                            title="Threats by Category"
                            description="Distribution of blocked threats by category"
                        >
                            <div className="h-64">
                                {report?.threat_categories && Object.keys(report.threat_categories).length > 0 ? (
                                    <LazyChart>
                                        {({ Doughnut }) => (
                                            <Doughnut data={categoryDistributionData} options={chartOptions} />
                                        )}
                                    </LazyChart>
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        No category data available
                                    </div>
                                )}
                            </div>
                        </Card>
                    </div>

                    {/* Threat Timeline */}
                    <Card
                        title="Threat Detection Timeline"
                        description={`Daily threat detection over ${reportDays} days`}
                        className="mb-6"
                    >
                        <div className="h-64">
                            {report?.threat_timeline?.length ? (
                                <LazyChart>
                                    {({ Line }) => (
                                        <Line data={threatTimelineData} options={chartOptions} />
                                    )}
                                </LazyChart>
                            ) : (
                                <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                    No timeline data available
                                </div>
                            )}
                        </div>
                    </Card>

                    {/* Recent Blocked Queries Table */}
                    <Card
                        title="Recent Blocked Queries"
                        description="Most recent blocked queries with details"
                    >
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-800">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Time
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Domain
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Client IP
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Category
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Action
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                                    {queries?.query_results?.slice(0, 20).map((query, index) => (
                                        <tr key={index}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                {formatDateTime(query.timestamp)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-gray-100">
                                                {query.domain}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                {query.client_ip}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Badge variant="outline">
                                                    {query.category}
                                                </Badge>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Badge variant={query.action === 'block' ? 'destructive' : 'default'}>
                                                    {query.action}
                                                </Badge>
                                            </td>
                                        </tr>
                                    )) || (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                                                    {queriesLoading ? 'Loading...' : 'No blocked queries found'}
                                                </td>
                                            </tr>
                                        )}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    )
}

export default SecurityAnalytics