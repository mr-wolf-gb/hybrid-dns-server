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
  }): Promise<AxiosResponse<Zone[]>> => {
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
  getRecords: (zone_id: number): Promise<AxiosResponse<DNSRecord[]>> =>
    api.get(`/zones/${zone_id}/records`),

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

  importRules: (category: string, url: string): Promise<AxiosResponse<ApiResponse<{ imported: number }>>> =>
    api.post('/rpz/import', { category, url }),

  updateThreatFeeds: (): Promise<AxiosResponse<ApiResponse<{ updated: number }>>> =>
    api.post('/rpz/update-feeds'),
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