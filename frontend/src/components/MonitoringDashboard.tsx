import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  Activity, AlertTriangle, TrendingUp, TrendingDown, 
  Clock, Shield, Users, Globe, Zap, Database 
} from 'lucide-react';

interface PerformanceMetrics {
  queries_per_second: number;
  avg_response_time: number;
  cache_hit_rate: number;
  error_rate: number;
  blocked_rate: number;
}

interface RealTimeStats {
  total_queries: number;
  blocked_queries: number;
  block_rate: number;
  current_qps: number;
  avg_response_time: number;
  buffer_size: number;
  top_domains: Record<string, number>;
  top_clients: Record<string, number>;
  query_types: Record<string, number>;
}

interface TrendData {
  query_trends?: {
    query_volume_trend: string;
    response_time_trend: string;
    hourly_data: Array<{
      hour: string;
      query_count: number;
      avg_response_time: number;
      blocked_count: number;
    }>;
  };
  threat_trends?: {
    by_category: Record<string, any>;
    daily_data: Array<any>;
  };
  predictions?: {
    next_hour_queries?: {
      predicted_count: number;
      confidence: string;
      based_on_trend: string;
    };
    threat_level?: {
      current_trend: string;
      risk_level: string;
    };
  };
}

interface Anomaly {
  type: string;
  severity: string;
  current: number;
  expected: number;
  description: string;
}

const MonitoringDashboard: React.FC = () => {
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [realTimeStats, setRealTimeStats] = useState<RealTimeStats | null>(null);
  const [trendData, setTrendData] = useState<TrendData | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('24');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchPerformanceMetrics = useCallback(async () => {
    try {
      const response = await fetch(`/api/analytics/performance?hours=${timeRange}`);
      const data = await response.json();
      if (data.success) {
        setPerformanceMetrics(data.data);
      }
    } catch (err) {
      console.error('Error fetching performance metrics:', err);
    }
  }, [timeRange]);

  const fetchRealTimeStats = useCallback(async () => {
    try {
      const response = await fetch('/api/analytics/real-time');
      const data = await response.json();
      if (data.success) {
        setRealTimeStats(data.data);
      }
    } catch (err) {
      console.error('Error fetching real-time stats:', err);
    }
  }, []);

  const fetchTrendData = useCallback(async () => {
    try {
      const response = await fetch('/api/analytics/trends?days=7');
      const data = await response.json();
      if (data.success) {
        setTrendData(data.data);
      }
    } catch (err) {
      console.error('Error fetching trend data:', err);
    }
  }, []);

  const fetchAnomalies = useCallback(async () => {
    try {
      const response = await fetch('/api/analytics/anomalies');
      const data = await response.json();
      if (data.success) {
        setAnomalies(data.data.detected_anomalies || []);
      }
    } catch (err) {
      console.error('Error fetching anomalies:', err);
    }
  }, []);

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchPerformanceMetrics(),
        fetchRealTimeStats(),
        fetchTrendData(),
        fetchAnomalies()
      ]);
    } catch (err) {
      setError('Failed to load monitoring data');
    } finally {
      setLoading(false);
    }
  }, [fetchPerformanceMetrics, fetchRealTimeStats, fetchTrendData, fetchAnomalies]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchRealTimeStats();
      fetchAnomalies();
    }, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, fetchRealTimeStats, fetchAnomalies]);

  const clearCache = async () => {
    try {
      const response = await fetch('/api/analytics/cache/clear', { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        await fetchAllData();
      }
    } catch (err) {
      console.error('Error clearing cache:', err);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'decreasing': return <TrendingDown className="h-4 w-4 text-red-500" />;
      default: return <Activity className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'error': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className="m-4">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Performance Monitoring</h1>
        <div className="flex items-center space-x-4">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1 Hour</SelectItem>
              <SelectItem value="6">6 Hours</SelectItem>
              <SelectItem value="24">24 Hours</SelectItem>
              <SelectItem value="168">7 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={autoRefresh ? 'bg-green-50' : ''}
          >
            {autoRefresh ? 'Auto Refresh On' : 'Auto Refresh Off'}
          </Button>
          <Button onClick={fetchAllData}>Refresh</Button>
          <Button variant="outline" onClick={clearCache}>Clear Cache</Button>
        </div>
      </div>

      {/* Anomaly Alerts */}
      {anomalies.length > 0 && (
        <div className="space-y-2">
          {anomalies.map((anomaly, index) => (
            <Alert key={index} className={getSeverityColor(anomaly.severity)}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>{anomaly.type.replace('_', ' ').toUpperCase()}:</strong> {anomaly.description}
                <span className="ml-2 text-sm">
                  (Current: {anomaly.current}, Expected: {anomaly.expected})
                </span>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Real-time Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Queries/Second</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {realTimeStats?.current_qps?.toFixed(1) || '0.0'}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatNumber(realTimeStats?.total_queries || 0)} total today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {realTimeStats?.avg_response_time?.toFixed(1) || '0.0'}ms
            </div>
            <p className="text-xs text-muted-foreground">
              {trendData?.query_trends && getTrendIcon(trendData.query_trends.response_time_trend)}
              <span className="ml-1">
                {trendData?.query_trends?.response_time_trend || 'stable'}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Block Rate</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {realTimeStats?.block_rate?.toFixed(1) || '0.0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              {formatNumber(realTimeStats?.blocked_queries || 0)} blocked today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Buffer Size</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {realTimeStats?.buffer_size || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Pending processing
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Dashboard Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Query Volume Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Query Volume (24h)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={trendData?.query_trends?.hourly_data || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip />
                    <Area 
                      type="monotone" 
                      dataKey="query_count" 
                      stroke="#3b82f6" 
                      fill="#3b82f6" 
                      fillOpacity={0.3} 
                    />
                    <Area 
                      type="monotone" 
                      dataKey="blocked_count" 
                      stroke="#ef4444" 
                      fill="#ef4444" 
                      fillOpacity={0.3} 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Top Domains */}
            <Card>
              <CardHeader>
                <CardTitle>Top Domains</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(realTimeStats?.top_domains || {})
                    .slice(0, 10)
                    .map(([domain, count]) => (
                      <div key={domain} className="flex justify-between items-center">
                        <span className="text-sm truncate flex-1">{domain}</span>
                        <Badge variant="default">{count}</Badge>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span>Queries/Second:</span>
                    <span className="font-mono">{performanceMetrics?.queries_per_second?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Response Time:</span>
                    <span className="font-mono">{performanceMetrics?.avg_response_time?.toFixed(2) || '0.00'}ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cache Hit Rate:</span>
                    <span className="font-mono">{performanceMetrics?.cache_hit_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Error Rate:</span>
                    <span className="font-mono">{performanceMetrics?.error_rate?.toFixed(2) || '0.00'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Block Rate:</span>
                    <span className="font-mono">{performanceMetrics?.blocked_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Query Types Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Query Types</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(realTimeStats?.query_types || {}).map(([type, count]) => ({
                        name: type,
                        value: count
                      }))}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label
                    >
                      {Object.entries(realTimeStats?.query_types || {}).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={`hsl(${index * 45}, 70%, 60%)`} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          <div className="grid grid-cols-1 gap-6">
            {/* Predictions */}
            {trendData?.predictions && (
              <Card>
                <CardHeader>
                  <CardTitle>Predictions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {trendData.predictions.next_hour_queries && (
                      <div className="p-4 border rounded-lg">
                        <h4 className="font-semibold">Next Hour Queries</h4>
                        <p className="text-2xl font-bold text-blue-600">
                          {formatNumber(trendData.predictions.next_hour_queries.predicted_count)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Confidence: {trendData.predictions.next_hour_queries.confidence}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Trend: {trendData.predictions.next_hour_queries.based_on_trend}
                        </p>
                      </div>
                    )}
                    {trendData.predictions.threat_level && (
                      <div className="p-4 border rounded-lg">
                        <h4 className="font-semibold">Threat Level</h4>
                        <Badge 
                          className={`text-lg ${
                            trendData.predictions.threat_level.risk_level === 'high' ? 'bg-red-500' :
                            trendData.predictions.threat_level.risk_level === 'medium' ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                        >
                          {trendData.predictions.threat_level.risk_level.toUpperCase()}
                        </Badge>
                        <p className="text-sm text-muted-foreground mt-2">
                          Trend: {trendData.predictions.threat_level.current_trend}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Response Time Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Response Time Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendData?.query_trends?.hourly_data || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="avg_response_time" 
                      stroke="#3b82f6" 
                      name="Avg Response Time (ms)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Clients */}
            <Card>
              <CardHeader>
                <CardTitle>Top Clients</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(realTimeStats?.top_clients || {})
                    .slice(0, 10)
                    .map(([client, count]) => (
                      <div key={client} className="flex justify-between items-center">
                        <span className="text-sm font-mono">{client}</span>
                        <Badge variant="default">{count}</Badge>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>

            {/* Threat Categories */}
            {trendData?.threat_trends?.by_category && (
              <Card>
                <CardHeader>
                  <CardTitle>Threat Categories</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(trendData.threat_trends.by_category)
                      .slice(0, 10)
                      .map(([category, data]: [string, any]) => (
                        <div key={category} className="flex justify-between items-center">
                          <span className="text-sm">{category}</span>
                          <Badge variant="destructive">{data.total_threats || 0}</Badge>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MonitoringDashboard;