import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
    ShieldCheckIcon,
    ShieldExclamationIcon,
    ExclamationTriangleIcon,
    ChartBarIcon,
    ClockIcon,
    ArrowTrendingUpIcon,
    ArrowTrendingDownIcon,
    InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { Line, Doughnut, Bar } from 'react-chartjs-2'
import { rpzService } from '@/services/api'
import { Card, Button, Badge, Select } from '@/components/ui'
import { formatNumber, formatDateTime, formatRelativeTime } from '@/utils'
import { ThreatIntelligenceStats, ThreatDetectionReport } from '@/types'

interface ThreatIntelligenceDashboardProps {
    isOpen: boolean
    onClose: () => void
}

const ThreatIntelligenceDashboard: React.FC<ThreatIntelligenceDashboardProps> = ({
    isOpen,
    onClose,
}) => {
    const [selectedTimeRange, setSelectedTimeRange] = useState(30)
    const [selectedReportType, setSelectedReportType] = useState('comprehensive')

    // Fetch threat intelligence statistics
    const { data: threatIntelStats, isLoading: statsLoading } = useQuery({
        queryKey: ['threat-intelligence-stats'],
        queryFn: () => rpzService.getThreatIntelligenceStatistics(),
        enabled: isOpen,
        refetchInterval: 60000, // Refresh every minute
    })

    // Fetch threat detection report
    const { data: threatReport, isLoading: reportLoading } = useQuery({
        queryKey: ['threat-detection-report', selectedTimeRange],
        queryFn: () => rpzService.getThreatDetectionReport({
            days: selectedTimeRange,
            include_details: true,
        }),
        enabled: isOpen,
        refetchInterval: 300000, // Refresh every 5 minutes
    })

    // Fetch threat coverage report
    const { data: coverageReport } = useQuery({
        queryKey: ['threat-coverage-report'],
        queryFn: () => rpzService.getThreatCoverageReport(),
        enabled: isOpen,
        refetchInterval: 300000,
    })

    // Fetch feed performance metrics
    const { data: performanceMetrics } = useQuery({
        queryKey: ['feed-performance-metrics', selectedTimeRange],
        queryFn: () => rpzService.getFeedPerformanceMetrics(selectedTimeRange),
        enabled: isOpen,
        refetchInterval: 300000,
    })

    if (!isOpen) return null

    const stats = threatIntelStats?.data
    const report = threatReport?.data
    const coverage = coverageReport?.data
    const performance = performanceMetrics?.data

    // Prepare chart data
    const feedTypeChartData = {
        labels: Object.keys(stats?.threat_feeds?.feeds_by_type || {}),
        datasets: [
            {
                data: Object.values(stats?.threat_feeds?.feeds_by_type || {}),
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
                label: 'Threats Blocked',
                data: report?.threat_timeline?.map(item => item.blocked_count) || [],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true,
            },
        ],
    }

    const categoryThreatData = {
        labels: Object.keys(report?.threat_categories || {}),
        datasets: [
            {
                label: 'Blocked Count',
                data: Object.values(report?.threat_categories || {}).map((cat: any) => cat.blocked_count),
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
        <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />

                <div className="inline-block w-full max-w-7xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white dark:bg-gray-800 shadow-xl rounded-lg">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                Threat Intelligence Dashboard
                            </h2>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                Comprehensive threat analysis and protection metrics
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <Select
                                value={selectedTimeRange.toString()}
                                onChange={(e) => setSelectedTimeRange(parseInt(e.target.value))}
                                options={[
                                    { value: '7', label: 'Last 7 days' },
                                    { value: '30', label: 'Last 30 days' },
                                    { value: '90', label: 'Last 90 days' },
                                ]}
                            />
                            <Button variant="outline" onClick={onClose}>
                                Close
                            </Button>
                        </div>
                    </div>

                    {/* Key Metrics */}
                    <div className="grid grid-cols-1 gap-4 mb-6 sm:grid-cols-2 lg:grid-cols-4">
                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <ShieldCheckIcon className="w-8 h-8 text-green-600 dark:text-green-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {formatNumber(stats?.protection_coverage?.total_domains_protected || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Protected Domains
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <ShieldExclamationIcon className="w-8 h-8 text-red-600 dark:text-red-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {formatNumber(report?.executive_summary?.total_threats_blocked || 0)}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Threats Blocked
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <ChartBarIcon className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {stats?.threat_feeds?.active_feeds || 0}
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Active Feeds
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <ClockIcon className="w-8 h-8 text-orange-600 dark:text-orange-400" />
                                </div>
                                <div className="ml-4">
                                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                                        {Math.round(report?.executive_summary?.threat_detection_rate || 0)}%
                                    </div>
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                                        Detection Rate
                                    </p>
                                </div>
                            </div>
                        </Card>
                    </div>

                    {/* Charts Row */}
                    <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-3">
                        {/* Feed Types Distribution */}
                        <Card
                            title="Feed Types"
                            description="Distribution of threat feed types"
                            className="col-span-1"
                        >
                            <div className="h-64">
                                {stats?.threat_feeds?.feeds_by_type && Object.keys(stats.threat_feeds.feeds_by_type).length > 0 ? (
                                    <Doughnut data={feedTypeChartData} options={chartOptions} />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        No feed data available
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* Threat Timeline */}
                        <Card
                            title="Threat Timeline"
                            description={`Threats blocked over ${selectedTimeRange} days`}
                            className="col-span-1 lg:col-span-2"
                        >
                            <div className="h-64">
                                {report?.threat_timeline?.length ? (
                                    <Line data={threatTimelineData} options={chartOptions} />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        No timeline data available
                                    </div>
                                )}
                            </div>
                        </Card>
                    </div>

                    {/* Category Analysis */}
                    <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-2">
                        <Card
                            title="Threats by Category"
                            description="Blocked threats grouped by category"
                        >
                            <div className="h-64">
                                {report?.threat_categories && Object.keys(report.threat_categories).length > 0 ? (
                                    <Bar data={categoryThreatData} options={barChartOptions} />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        No category data available
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* Feed Effectiveness */}
                        <Card
                            title="Feed Effectiveness"
                            description="Performance of individual threat feeds"
                        >
                            <div className="space-y-3 max-h-64 overflow-y-auto">
                                {report?.feed_effectiveness?.length ? (
                                    report.feed_effectiveness.map((feed, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                            <div>
                                                <div className="font-medium text-gray-900 dark:text-gray-100">
                                                    {feed.feed_name}
                                                </div>
                                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                                    {formatNumber(feed.rules_count)} rules
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {formatNumber(feed.blocks_generated)} blocks
                                                </div>
                                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                                    {Math.round(feed.effectiveness_score)}% effective
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                                        No effectiveness data available
                                    </div>
                                )}
                            </div>
                        </Card>
                    </div>

                    {/* Top Threat Sources */}
                    <Card
                        title="Top Threat Sources"
                        description="Most active threat domains"
                        className="mb-6"
                    >
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-800">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Domain
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Category
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Blocks
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            First Seen
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Last Seen
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                                    {report?.top_threat_sources?.slice(0, 10).map((threat, index) => (
                                        <tr key={index}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-gray-100">
                                                {threat.domain}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Badge variant="outline">
                                                    {threat.category}
                                                </Badge>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                {formatNumber(threat.block_count)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                {formatDateTime(threat.first_seen)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                {formatDateTime(threat.last_seen)}
                                            </td>
                                        </tr>
                                    )) || (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                                                    No threat source data available
                                                </td>
                                            </tr>
                                        )}
                                </tbody>
                            </table>
                        </div>
                    </Card>

                    {/* Health Status */}
                    <Card
                        title="System Health"
                        description="Overall threat protection health"
                    >
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                                    {stats?.update_health?.feeds_up_to_date || 0}
                                </div>
                                <div className="text-sm text-green-700 dark:text-green-300">
                                    Feeds Up to Date
                                </div>
                            </div>

                            <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                                    {stats?.update_health?.feeds_with_errors || 0}
                                </div>
                                <div className="text-sm text-red-700 dark:text-red-300">
                                    Feeds with Errors
                                </div>
                            </div>

                            <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                                    {stats?.update_health?.feeds_due_for_update || 0}
                                </div>
                                <div className="text-sm text-yellow-700 dark:text-yellow-300">
                                    Due for Update
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    )
}

export default ThreatIntelligenceDashboard