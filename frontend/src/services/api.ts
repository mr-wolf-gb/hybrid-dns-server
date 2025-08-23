import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  User,
  LoginRequest,
  LoginResponse,
  Setup2FAResponse,
  Zone,
  DNSRecord,
  Forwarder,
  RPZRule,
  DashboardStats,
  RecentQuery,
  DNSLog,
  SystemStats,
  ApiResponse,
  PaginatedResponse,
  ZoneFormData,
  RecordFormData,
  ForwarderFormData,
  ForwarderTemplate,
  RPZRuleFormData,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instances
export const authApi: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await authApi.post<LoginResponse>('/auth/refresh', {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token: newRefreshToken } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', newRefreshToken)

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// Authentication API
export const authService = {
  login: (credentials: LoginRequest): Promise<AxiosResponse<LoginResponse>> =>
    authApi.post('/auth/login', credentials),

  logout: (): Promise<AxiosResponse<void>> =>
    api.post('/auth/logout'),

  refreshToken: (refresh_token: string): Promise<AxiosResponse<LoginResponse>> =>
    authApi.post('/auth/refresh', { refresh_token }),

  getCurrentUser: (): Promise<AxiosResponse<User>> =>
    api.get('/auth/me'),

  setup2FA: (): Promise<AxiosResponse<Setup2FAResponse>> =>
    api.post('/auth/2fa/setup'),

  verify2FA: (token: string): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/auth/2fa/verify', { token }),

  disable2FA: (password: string): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/auth/2fa/disable', { password }),

  changePassword: (data: { old_password: string; new_password: string }): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/auth/change-password', data),
}

// Dashboard API
export const dashboardService = {
  getStats: (): Promise<AxiosResponse<DashboardStats>> =>
    api.get('/dashboard/stats'),

  getRecentQueries: (limit?: number): Promise<AxiosResponse<RecentQuery[]>> =>
    api.get(`/dashboard/recent-queries${limit ? `?limit=${limit}` : ''}`),

  getQueryLogs: (page?: number, per_page?: number, search?: string): Promise<AxiosResponse<PaginatedResponse<DNSLog>>> => {
    const params = new URLSearchParams()
    if (page) params.append('page', page.toString())
    if (per_page) params.append('per_page', per_page.toString())
    if (search) params.append('search', search)
    return api.get(`/dashboard/query-logs?${params.toString()}`)
  },

  getSystemStats: (hours?: number): Promise<AxiosResponse<SystemStats[]>> =>
    api.get(`/dashboard/system-stats${hours ? `?hours=${hours}` : ''}`),
}

// Zones API
export const zonesService = {
  getZones: (params?: {
    skip?: number
    limit?: number
    zone_type?: string
    active_only?: boolean
  }): Promise<AxiosResponse<PaginatedResponse<Zone>>> => {
    const searchParams = new URLSearchParams()
    if (params?.skip !== undefined) searchParams.append('skip', params.skip.toString())
    if (params?.limit !== undefined) searchParams.append('limit', params.limit.toString())
    if (params?.zone_type) searchParams.append('zone_type', params.zone_type)
    if (params?.active_only !== undefined) searchParams.append('active_only', params.active_only.toString())
    
    return api.get(`/zones?${searchParams.toString()}`)
  },

  getZone: (id: number): Promise<AxiosResponse<Zone>> =>
    api.get(`/zones/${id}`),

  createZone: (data: ZoneFormData): Promise<AxiosResponse<Zone>> =>
    api.post('/zones', data),

  updateZone: (id: number, data: Partial<ZoneFormData>): Promise<AxiosResponse<Zone>> =>
    api.put(`/zones/${id}`, data),

  deleteZone: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/zones/${id}`),

  toggleZone: (id: number): Promise<AxiosResponse<Zone>> =>
    api.post(`/zones/${id}/toggle`),

  reloadZone: (id: number): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post(`/zones/${id}/reload`),

  validateZone: (id: number): Promise<AxiosResponse<{ valid: boolean; errors: string[]; warnings: string[] }>> =>
    api.post(`/zones/${id}/validate`),

  validateZoneConfiguration: (id: number): Promise<AxiosResponse<{ valid: boolean; errors: string[]; warnings: string[] }>> =>
    api.post(`/zones/${id}/validate/configuration`),

  validateZoneRecords: (id: number): Promise<AxiosResponse<{ valid: boolean; errors: string[]; warnings: string[] }>> =>
    api.post(`/zones/${id}/validate/records`),

  getZoneStatistics: (id: number): Promise<AxiosResponse<{ record_count: number; last_modified: string; serial: number; health_status: string; last_check: string }>> =>
    api.get(`/zones/${id}/statistics`),

  getZoneHealth: (id: number): Promise<AxiosResponse<{ status: string; last_check: string; issues: string[]; response_time?: number }>> =>
    api.get(`/zones/${id}/health`),

  exportZone: (id: number, format?: string): Promise<AxiosResponse<string>> =>
    api.get(`/zones/${id}/export${format ? `?format=${format}` : ''}`),

  importZone: (data: { name: string; zone_data: string; format?: string }): Promise<AxiosResponse<Zone>> =>
    api.post('/zones/import', data),
}

// DNS Records API
export const recordsService = {
  getRecords: (zone_id: number, params?: {
    record_type?: string
    name?: string
    search?: string
    active_only?: boolean
    skip?: number
    limit?: number
    sort_by?: string
    sort_order?: string
  }): Promise<AxiosResponse<PaginatedResponse<DNSRecord>>> => {
    const searchParams = new URLSearchParams()
    if (params?.record_type) searchParams.append('record_type', params.record_type)
    if (params?.name) searchParams.append('name', params.name)
    if (params?.search) searchParams.append('search', params.search)
    if (params?.active_only !== undefined) searchParams.append('active_only', params.active_only.toString())
    if (params?.skip !== undefined) searchParams.append('skip', params.skip.toString())
    if (params?.limit !== undefined) searchParams.append('limit', params.limit.toString())
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order)
    
    return api.get(`/zones/${zone_id}/records?${searchParams.toString()}`)
  },

  getRecord: (zone_id: number, record_id: number): Promise<AxiosResponse<DNSRecord>> =>
    api.get(`/zones/${zone_id}/records/${record_id}`),

  createRecord: (zone_id: number, data: RecordFormData): Promise<AxiosResponse<DNSRecord>> =>
    api.post(`/zones/${zone_id}/records`, data),

  updateRecord: (zone_id: number, record_id: number, data: Partial<RecordFormData>): Promise<AxiosResponse<DNSRecord>> =>
    api.put(`/zones/${zone_id}/records/${record_id}`, data),

  deleteRecord: (zone_id: number, record_id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/zones/${zone_id}/records/${record_id}`),

  toggleRecord: (zone_id: number, record_id: number): Promise<AxiosResponse<DNSRecord>> =>
    api.post(`/zones/${zone_id}/records/${record_id}/toggle`),

  // Bulk operations
  bulkCreateRecords: (zone_id: number, records: RecordFormData[]): Promise<AxiosResponse<DNSRecord[]>> =>
    api.post(`/zones/${zone_id}/records/bulk`, { records }),

  bulkUpdateRecords: (zone_id: number, record_ids: number[], data: Partial<RecordFormData>): Promise<AxiosResponse<DNSRecord[]>> =>
    api.put(`/zones/${zone_id}/records/bulk`, { record_ids, ...data }),

  bulkDeleteRecords: (zone_id: number, record_ids: number[]): Promise<AxiosResponse<void>> =>
    api.delete(`/zones/${zone_id}/records/bulk`, { data: { record_ids } }),

  bulkToggleRecords: (zone_id: number, record_ids: number[], is_active: boolean): Promise<AxiosResponse<DNSRecord[]>> =>
    api.post(`/zones/${zone_id}/records/bulk/toggle`, { record_ids, is_active }),

  // Import/Export
  exportRecords: (zone_id: number, format?: 'json' | 'csv' | 'zone'): Promise<AxiosResponse<string>> =>
    api.get(`/zones/${zone_id}/records/export${format ? `?format=${format}` : ''}`),

  importRecords: (zone_id: number, data: { records: RecordFormData[], format?: string }): Promise<AxiosResponse<{ imported: number, errors: string[] }>> =>
    api.post(`/zones/${zone_id}/records/import`, data),
}

// Forwarders API
export const forwardersService = {
  getForwarders: (): Promise<AxiosResponse<Forwarder[]>> =>
    api.get('/forwarders'),

  getForwarder: (id: number): Promise<AxiosResponse<Forwarder>> =>
    api.get(`/forwarders/${id}`),

  createForwarder: (data: ForwarderFormData): Promise<AxiosResponse<Forwarder>> =>
    api.post('/forwarders', data),

  updateForwarder: (id: number, data: Partial<ForwarderFormData>): Promise<AxiosResponse<Forwarder>> =>
    api.put(`/forwarders/${id}`, data),

  deleteForwarder: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/forwarders/${id}`),

  toggleForwarder: (id: number): Promise<AxiosResponse<Forwarder>> =>
    api.post(`/forwarders/${id}/toggle`),

  testForwarder: (id: number, params?: { domain?: string; record_type?: string; timeout?: number }): Promise<AxiosResponse<ApiResponse<{ status: string; response_time: number }>>> =>
    api.post(`/forwarders/${id}/test`, params),

  getForwarderStatistics: (id: number): Promise<AxiosResponse<{ query_count: number; success_rate: number; avg_response_time: number; last_24h_queries: number }>> =>
    api.get(`/forwarders/${id}/statistics`),

  getForwarderHealth: (id: number): Promise<AxiosResponse<{ status: string; last_check: string; response_time?: number; issues: string[] }>> =>
    api.get(`/forwarders/${id}/health`),

  bulkTestForwarders: (forwarder_ids: number[]): Promise<AxiosResponse<ApiResponse<Array<{ id: number; status: string; response_time: number; error?: string }>>>> =>
    api.post('/forwarders/bulk/test', { forwarder_ids }),

  bulkToggleForwarders: (forwarder_ids: number[], is_active: boolean): Promise<AxiosResponse<Forwarder[]>> =>
    api.post('/forwarders/bulk/toggle', { forwarder_ids, is_active }),

  refreshHealthStatus: (): Promise<AxiosResponse<ApiResponse<{ updated: number }>>> =>
    api.post('/forwarders/health/refresh'),

  // Templates
  getTemplates: (): Promise<AxiosResponse<ForwarderTemplate[]>> =>
    api.get('/forwarders/templates'),

  createTemplate: (data: Omit<ForwarderTemplate, 'id'>): Promise<AxiosResponse<ForwarderTemplate>> =>
    api.post('/forwarders/templates', data),

  updateTemplate: (id: string, data: Partial<ForwarderTemplate>): Promise<AxiosResponse<ForwarderTemplate>> =>
    api.put(`/forwarders/templates/${id}`, data),

  deleteTemplate: (id: string): Promise<AxiosResponse<void>> =>
    api.delete(`/forwarders/templates/${id}`),
}

// RPZ API
export const rpzService = {
  getRules: (): Promise<AxiosResponse<RPZRule[]>> =>
    api.get('/rpz/rules'),

  getRule: (id: number): Promise<AxiosResponse<RPZRule>> =>
    api.get(`/rpz/rules/${id}`),

  createRule: (data: RPZRuleFormData): Promise<AxiosResponse<RPZRule>> =>
    api.post('/rpz/rules', data),

  updateRule: (id: number, data: Partial<RPZRuleFormData>): Promise<AxiosResponse<RPZRule>> =>
    api.put(`/rpz/rules/${id}`, data),

  deleteRule: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/rpz/rules/${id}`),

  toggleRule: (id: number): Promise<AxiosResponse<RPZRule>> =>
    api.post(`/rpz/rules/${id}/toggle`),

  // Bulk operations
  bulkDeleteRules: (ruleIds: number[]): Promise<AxiosResponse<void>> =>
    api.delete('/rpz/rules/bulk', { data: { rule_ids: ruleIds } }),

  bulkToggleRules: (ruleIds: number[], isActive: boolean): Promise<AxiosResponse<RPZRule[]>> =>
    api.post('/rpz/rules/bulk/toggle', { rule_ids: ruleIds, is_active: isActive }),

  // Import/Export
  importRules: (category: string, url: string): Promise<AxiosResponse<ApiResponse<{ imported: number }>>> =>
    api.post('/rpz/import', { category, url }),

  exportRules: (ruleIds?: number[]): Promise<AxiosResponse<string>> =>
    api.post('/rpz/export', { rule_ids: ruleIds }),

  // Threat feeds
  updateThreatFeeds: (): Promise<AxiosResponse<ApiResponse<{ updated: number }>>> =>
    api.post('/rpz/update-feeds'),

  getThreatFeeds: (): Promise<AxiosResponse<any[]>> =>
    api.get('/rpz/threat-feeds'),

  createThreatFeed: (data: any): Promise<AxiosResponse<any>> =>
    api.post('/rpz/threat-feeds', data),

  updateThreatFeed: (id: number, data: any): Promise<AxiosResponse<any>> =>
    api.put(`/rpz/threat-feeds/${id}`, data),

  deleteThreatFeed: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/rpz/threat-feeds/${id}`),

  updateSingleThreatFeed: (id: number): Promise<AxiosResponse<ApiResponse<{ imported: number }>>> =>
    api.post(`/rpz/threat-feeds/${id}/update`),

  toggleThreatFeed: (id: number, enabled: boolean): Promise<AxiosResponse<any>> =>
    api.post(`/rpz/threat-feeds/${id}/toggle`, { enabled }),

  // Enhanced threat feed methods
  getThreatFeedStatistics: (feedId?: number): Promise<AxiosResponse<any>> =>
    api.get('/rpz/threat-feeds/statistics', { params: feedId ? { feed_id: feedId } : {} }),

  getThreatFeedSchedule: (): Promise<AxiosResponse<any>> =>
    api.get('/rpz/threat-feeds/schedule'),

  scheduleThreatFeedUpdates: (): Promise<AxiosResponse<any>> =>
    api.post('/rpz/threat-feeds/schedule-updates'),

  createCustomThreatList: (data: {
    name: string
    domains: string[]
    category: string
    description?: string
  }): Promise<AxiosResponse<any>> =>
    api.post('/rpz/threat-feeds/custom', data),

  updateCustomThreatList: (feedId: number, domains: string[]): Promise<AxiosResponse<any>> =>
    api.put(`/rpz/threat-feeds/${feedId}/custom`, { domains }),

  // Statistics
  getStatistics: (): Promise<AxiosResponse<ApiResponse<{
    blocked_today: number
    blocked_this_week: number
    blocked_this_month: number
    top_blocked_domains: Array<{ domain: string; count: number; category: string }>
    blocks_by_hour: Array<{ hour: string; count: number }>
    threat_feed_stats: Array<{ feed: string; rules: number; last_update: string }>
  }>>> =>
    api.get('/rpz/statistics'),

  // Rule templates
  getRuleTemplates: (): Promise<AxiosResponse<any[]>> =>
    api.get('/rpz/templates'),

  createRuleTemplate: (data: any): Promise<AxiosResponse<any>> =>
    api.post('/rpz/templates', data),

  updateRuleTemplate: (id: string, data: any): Promise<AxiosResponse<any>> =>
    api.put(`/rpz/templates/${id}`, data),

  deleteRuleTemplate: (id: string): Promise<AxiosResponse<void>> =>
    api.delete(`/rpz/templates/${id}`),

  // Bulk import
  bulkImportRules: (data: {
    domains: string[]
    zone: string
    action: string
    category: string
    redirect_target?: string
  }): Promise<AxiosResponse<ApiResponse<{ success: number; failed: number; errors: string[] }>>> =>
    api.post('/rpz/bulk-import', data),
}

// Reports API
export const reportsApi = {
  // Templates
  getTemplates: (): Promise<AxiosResponse<any[]>> =>
    api.get('/reports/templates'),

  getTemplate: (templateId: string): Promise<AxiosResponse<any>> =>
    api.get(`/reports/templates/${templateId}`),

  createTemplate: (data: any): Promise<AxiosResponse<any>> =>
    api.post('/reports/templates', data),

  updateTemplate: (templateId: string, data: any): Promise<AxiosResponse<any>> =>
    api.put(`/reports/templates/${templateId}`, data),

  deleteTemplate: (templateId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/reports/templates/${templateId}`),

  // Schedules
  getSchedules: (): Promise<AxiosResponse<any[]>> =>
    api.get('/reports/schedules'),

  getSchedule: (scheduleId: string): Promise<AxiosResponse<any>> =>
    api.get(`/reports/schedules/${scheduleId}`),

  createSchedule: (data: any): Promise<AxiosResponse<any>> =>
    api.post('/reports/schedules', data),

  updateSchedule: (scheduleId: string, data: any): Promise<AxiosResponse<any>> =>
    api.put(`/reports/schedules/${scheduleId}`, data),

  deleteSchedule: (scheduleId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/reports/schedules/${scheduleId}`),

  runSchedule: (scheduleId: string): Promise<AxiosResponse<any>> =>
    api.post(`/reports/schedules/${scheduleId}/run`),

  // Report Generation
  generateReport: (data: {
    template_id: string;
    parameters?: any;
    start_date?: string;
    end_date?: string;
  }): Promise<AxiosResponse<any>> =>
    api.post('/reports/generate', data),

  exportReport: (data: {
    template_id: string;
    format: string;
    parameters?: any;
    start_date?: string;
    end_date?: string;
  }): Promise<AxiosResponse<any>> =>
    api.post('/reports/export', data, { responseType: 'blob' }),

  // Analytics
  getQueryTrends: (startDate: string, endDate: string, interval?: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/query-analytics', {
      params: { hours: 24 } // Convert date range to hours for now
    }),

  getTopDomains: (startDate: string, endDate: string, limit?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/top-domains', {
      params: { hours: 24, limit: limit || 20 }
    }),

  getClientAnalytics: (startDate: string, endDate: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/client-analytics', {
      params: { hours: 24 }
    }),

  getPerformanceAnalytics: (startDate: string, endDate: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/performance', {
      params: { hours: 24 }
    }),

  getErrorAnalytics: (startDate: string, endDate: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/response-time-analytics', {
      params: { hours: 24 }
    }),

  getSecurityAnalytics: (startDate: string, endDate: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/threat-analytics', {
      params: { days: 7 }
    }),

  getZoneAnalytics: (zoneId?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/query-analytics', {
      params: { hours: 24 }
    }),

  getAnalyticsInsights: (startDate: string, endDate: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/anomalies'),

  // History and Statistics
  getReportHistory: (limit?: number): Promise<AxiosResponse<any>> =>
    api.get('/reports/history', {
      params: limit ? { limit } : {}
    }),

  getReportingStatistics: (): Promise<AxiosResponse<any>> =>
    api.get('/reports/statistics'),
}

// Analytics API
export const analyticsService = {
  getPerformanceMetrics: (hours?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/performance', {
      params: hours ? { hours } : {}
    }),

  getQueryAnalytics: (hours?: number, useCache?: boolean): Promise<AxiosResponse<any>> =>
    api.get('/analytics/query-analytics', {
      params: { hours: hours || 24, use_cache: useCache !== false }
    }),

  getRealTimeAnalytics: (): Promise<AxiosResponse<any>> =>
    api.get('/analytics/real-time'),

  getTrendAnalysis: (days?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/trends', {
      params: { days: days || 30 }
    }),

  getAnomalyDetection: (): Promise<AxiosResponse<any>> =>
    api.get('/analytics/anomalies'),

  getTopDomains: (hours?: number, limit?: number, includeBlocked?: boolean): Promise<AxiosResponse<any>> =>
    api.get('/analytics/top-domains', {
      params: { 
        hours: hours || 24, 
        limit: limit || 50,
        include_blocked: includeBlocked !== false
      }
    }),

  getClientAnalytics: (hours?: number, limit?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/client-analytics', {
      params: { hours: hours || 24, limit: limit || 50 }
    }),

  getResponseTimeAnalytics: (hours?: number): Promise<AxiosResponse<any>> =>
    api.get('/analytics/response-time-analytics', {
      params: { hours: hours || 24 }
    }),

  getThreatAnalytics: (days?: number, category?: string): Promise<AxiosResponse<any>> =>
    api.get('/analytics/threat-analytics', {
      params: { 
        days: days || 7,
        ...(category && { category })
      }
    }),

  clearCache: (): Promise<AxiosResponse<any>> =>
    api.post('/analytics/cache/clear'),

  exportData: (hours?: number, format?: string, includeRawLogs?: boolean): Promise<AxiosResponse<any>> =>
    api.get('/analytics/export', {
      params: {
        hours: hours || 24,
        format: format || 'json',
        include_raw_logs: includeRawLogs || false
      }
    }),
}

// System API
export const systemService = {
  getStatus: (): Promise<AxiosResponse<ApiResponse<{ status: string; version: string; uptime: number }>>> =>
    api.get('/system/status'),

  reloadBind: (): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/system/bind/reload'),

  restartBind: (): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/system/bind/restart'),

  flushCache: (): Promise<AxiosResponse<ApiResponse<boolean>>> =>
    api.post('/system/bind/flush-cache'),

  getBindStatus: (): Promise<AxiosResponse<ApiResponse<{ running: boolean; pid?: number }>>> =>
    api.get('/system/bind/status'),

  getLogs: (lines?: number): Promise<AxiosResponse<ApiResponse<string[]>>> =>
    api.get(`/system/logs${lines ? `?lines=${lines}` : ''}`),
}