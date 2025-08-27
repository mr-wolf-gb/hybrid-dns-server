import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  ClockIcon, 
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  ServerIcon,
  GlobeAltIcon
} from '@heroicons/react/24/outline';
// Chart.js will be loaded dynamically
import LazyChart from '@/components/charts/LazyChart'
import { toast } from 'react-toastify';

import { reportsApi } from '../../services/api';

// Chart.js registration will be handled by LazyChart

interface AnalyticsData {
  trends: any;
  topDomains: any[];
  clients: any;
  performance: any;
  errors: any;
  security: any;
  zones: any;
  insights: any[];
}

const AnalyticsDashboard: React.FC = () => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    loadAnalyticsData();
  }, [dateRange]);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      
      const [
        trendsResponse,
        topDomainsResponse,
        clientsResponse,
        performanceResponse,
        errorsResponse,
        securityResponse,
        zonesResponse,
        insightsResponse
      ] = await Promise.all([
        reportsApi.getQueryTrends(dateRange.start_date, dateRange.end_date),
        reportsApi.getTopDomains(dateRange.start_date, dateRange.end_date),
        reportsApi.getClientAnalytics(dateRange.start_date, dateRange.end_date),
        reportsApi.getPerformanceAnalytics(dateRange.start_date, dateRange.end_date),
        reportsApi.getErrorAnalytics(dateRange.start_date, dateRange.end_date),
        reportsApi.getSecurityAnalytics(dateRange.start_date, dateRange.end_date),
        reportsApi.getZoneAnalytics(),
        reportsApi.getAnalyticsInsights(dateRange.start_date, dateRange.end_date)
      ]);

      setAnalyticsData({
        trends: trendsResponse.data,
        topDomains: topDomainsResponse.data.top_domains,
        clients: clientsResponse.data,
        performance: performanceResponse.data,
        errors: errorsResponse.data,
        security: securityResponse.data,
        zones: zonesResponse.data,
        insights: insightsResponse.data.insights
      });
    } catch (error) {
      console.error('Failed to load analytics data:', error);
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'performance': return ClockIcon;
      case 'errors': return ExclamationTriangleIcon;
      case 'security': return ShieldCheckIcon;
      case 'volume': return ChartBarIcon;
      default: return ChartBarIcon;
    }
  };

  const getInsightColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'info': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!analyticsData) {
    return (
      <div className="text-center text-gray-500 py-8">
        Failed to load analytics data
      </div>
    );
  }

  // Prepare chart data
  const trendsChartData = {
    labels: analyticsData.trends.data.map((d: any) => d.timestamp),
    datasets: [
      {
        label: 'DNS Queries',
        data: analyticsData.trends.data.map((d: any) => d.count),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1,
      },
    ],
  };

  const topDomainsChartData = {
    labels: analyticsData.topDomains.slice(0, 10).map((d: any) => d.domain),
    datasets: [
      {
        label: 'Query Count',
        data: analyticsData.topDomains.slice(0, 10).map((d: any) => d.query_count),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
      },
    ],
  };

  const errorTypesChartData = {
    labels: Object.keys(analyticsData.errors.response_codes),
    datasets: [
      {
        data: Object.values(analyticsData.errors.response_codes),
        backgroundColor: [
          '#10B981', // NOERROR - green
          '#EF4444', // NXDOMAIN - red
          '#F59E0B', // SERVFAIL - yellow
          '#8B5CF6', // REFUSED - purple
          '#6B7280', // Other - gray
        ],
      },
    ],
  };

  return (
    <div className="space-y-6">
      {/* Date Range Selector */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex items-center space-x-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={dateRange.start_date}
              onChange={(e) => setDateRange(prev => ({ ...prev, start_date: e.target.value }))}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={dateRange.end_date}
              onChange={(e) => setDateRange(prev => ({ ...prev, end_date: e.target.value }))}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ChartBarIcon className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Queries</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(analyticsData.trends.total_queries)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-green-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Avg Response Time</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData.performance.avg_response_time}ms
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-red-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Error Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData.errors.error_rate}%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ShieldCheckIcon className="h-8 w-8 text-purple-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Blocked Queries</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(analyticsData.security.total_blocked)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Insights */}
      {analyticsData.insights.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Analytics Insights</h3>
          </div>
          <div className="p-6 space-y-4">
            {analyticsData.insights.map((insight, index) => {
              const IconComponent = getInsightIcon(insight.type);
              return (
                <div
                  key={index}
                  className={`p-4 rounded-lg border ${getInsightColor(insight.severity)}`}
                >
                  <div className="flex items-start space-x-3">
                    <IconComponent className="h-5 w-5 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-medium">{insight.title}</h4>
                      <p className="text-sm mt-1">{insight.description}</p>
                      <p className="text-sm mt-2 font-medium">
                        Recommendation: {insight.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Query Trends */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Query Trends</h3>
          <div className="h-64">
            <Line
              data={trendsChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    beginAtZero: true,
                  },
                },
              }}
            />
          </div>
        </div>

        {/* Top Domains */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Top Queried Domains</h3>
          <div className="h-64">
            <Bar
              data={topDomainsChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y' as const,
                scales: {
                  x: {
                    beginAtZero: true,
                  },
                },
              }}
            />
          </div>
        </div>

        {/* Response Codes */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Response Codes</h3>
          <div className="h-64">
            <Doughnut
              data={errorTypesChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom' as const,
                  },
                },
              }}
            />
          </div>
        </div>

        {/* Zone Statistics */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Zone Statistics</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <GlobeAltIcon className="h-5 w-5 text-blue-600" />
                <span className="text-sm font-medium">Total Zones</span>
              </div>
              <span className="text-lg font-bold">{analyticsData.zones.total_zones}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ServerIcon className="h-5 w-5 text-green-600" />
                <span className="text-sm font-medium">Active Zones</span>
              </div>
              <span className="text-lg font-bold">{analyticsData.zones.active_zones}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ChartBarIcon className="h-5 w-5 text-purple-600" />
                <span className="text-sm font-medium">Total Records</span>
              </div>
              <span className="text-lg font-bold">{analyticsData.zones.total_records}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Client Analytics */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Top Clients</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Client IP
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Queries
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Unique Domains
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Success Rate
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {analyticsData.clients.clients.slice(0, 10).map((client: any, index: number) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {client.client_ip}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatNumber(client.query_count)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {client.unique_domains}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      client.success_rate >= 95 
                        ? 'bg-green-100 text-green-800'
                        : client.success_rate >= 90
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {client.success_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;