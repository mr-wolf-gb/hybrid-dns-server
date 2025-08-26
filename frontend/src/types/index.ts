// Generic types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

// Authentication types
export interface User {
  id: number
  username: string
  full_name: string
  email: string
  is_2fa_enabled: boolean
  is_active: boolean
  is_superuser: boolean
  created_at: string
  last_login?: string
}

export interface LoginRequest {
  username: string
  password: string
  totp_code?: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface Setup2FAResponse {
  qr_code: string
  backup_codes: string[]
}

// DNS Zone types
export interface Zone {
  id: number
  name: string
  zone_type: 'master' | 'slave' | 'forward'
  master_servers?: string[]
  forwarders?: string[]
  file_path?: string
  is_active: boolean
  serial?: number
  refresh: number
  retry: number
  expire: number
  minimum: number
  email: string
  description?: string
  created_at: string
  updated_at: string
  record_count?: number
}

export interface DNSRecord {
  id: number
  zone_id: number
  name: string
  type: 'A' | 'AAAA' | 'CNAME' | 'MX' | 'TXT' | 'SRV' | 'PTR' | 'NS'
  value: string
  priority?: number
  weight?: number
  port?: number
  ttl: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// Forwarder types
export interface Forwarder {
  id: number
  name: string
  domains: string[]
  forwarder_type: 'active_directory' | 'intranet' | 'public'
  servers: ForwarderServerConfig[]
  is_active: boolean
  health_check_enabled: boolean
  description?: string
  priority: number
  group_name?: string
  group_priority: number
  created_at: string
  updated_at: string
  // Legacy fields for backward compatibility
  domain?: string
  type?: 'ad' | 'intranet' | 'public'
  forward_policy?: 'first' | 'only'
  health_status?: 'healthy' | 'unhealthy' | 'unknown'
  last_health_check?: string
  response_time?: number
  query_count?: number
  success_rate?: number
  health_check_interval?: number
  health_check_timeout?: number
  health_check_retries?: number
  weight?: number
}

// RPZ types
export interface RPZRule {
  id: number
  zone: string
  domain: string
  action: 'block' | 'redirect' | 'passthru'
  category: 'malware' | 'phishing' | 'social_media' | 'adult' | 'gambling' | 'custom'
  redirect_target?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// Monitoring types
export interface DNSLog {
  id: number
  timestamp: string
  client_ip: string
  query_domain: string
  query_type: string
  response_code: string
  is_blocked: boolean
  blocked_category?: string
}

export interface SystemStats {
  id: number
  timestamp: string
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  queries_per_second: number
  cache_hit_rate: number
  blocked_queries: number
}

// Dashboard types
export interface DashboardStats {
  total_queries_today: number
  blocked_queries_today: number
  cache_hit_rate: number
  active_zones: number
  healthy_forwarders: number
  total_forwarders: number
  queries_per_hour: Array<{ hour: string; queries: number }>
  top_domains: Array<{ domain: string; count: number }>
  blocked_domains: Array<{ domain: string; count: number; category: string }>
  forwarder_health: Array<{ name: string; status: string; response_time: number }>
}

export interface RecentQuery {
  timestamp: string
  client_ip: string
  domain: string
  type: string
  status: string
  blocked: boolean
  category?: string
}

// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Validation types
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface ZoneStatistics {
  record_count: number
  last_modified: string | null
  serial: number
  health_status: string
  last_check: string | null
}

export interface ZoneHealth {
  status: 'healthy' | 'warning' | 'error' | 'unknown'
  last_check: string | null
  issues: string[]
  response_time?: number
}

// Form types
export interface ZoneFormData {
  name: string
  zone_type: 'master' | 'slave' | 'forward'
  master_servers: string[]
  forwarders: string[]
  email: string
  description?: string
  refresh: number
  retry: number
  expire: number
  minimum: number
}

export interface ZoneTemplate {
  id: string
  name: string
  description: string
  zone_type: 'master' | 'slave' | 'forward'
  defaults: Partial<ZoneFormData>
}

export interface RecordFormData {
  name: string
  type: 'A' | 'AAAA' | 'CNAME' | 'MX' | 'TXT' | 'SRV' | 'PTR' | 'NS'
  value: string
  priority?: number
  weight?: number
  port?: number
  ttl: number
}

export interface ForwarderFormData {
  name: string
  domain: string
  servers: string[]
  type: 'ad' | 'intranet' | 'public'
  forward_policy: 'first' | 'only'
  domains?: string[]
  health_check_enabled?: boolean
  health_check_interval?: number
  health_check_timeout?: number
  health_check_retries?: number
  priority?: number
  weight?: number
  description?: string
}

export interface ForwarderServerConfig {
  ip: string
  port?: number
  priority?: number
  weight?: number
  enabled?: boolean
}

export interface ForwarderCreatePayload {
  name: string
  domains: string[]
  forwarder_type: 'active_directory' | 'intranet' | 'public'
  servers: ForwarderServerConfig[]
  description?: string
  health_check_enabled?: boolean
  priority?: number
  group_name?: string
  group_priority?: number
}

export interface ForwarderTemplate {
  id: string
  name: string
  description: string
  type: 'ad' | 'intranet' | 'public'
  defaults: Partial<ForwarderFormData>
  is_system?: boolean
}

export interface ServerConfig {
  ip: string
  port?: number
  priority?: number
  weight?: number
  is_active?: boolean
}

export interface RPZRuleFormData {
  zone: string
  domain: string
  action: 'block' | 'redirect' | 'passthru'
  category: 'malware' | 'phishing' | 'social_media' | 'adult' | 'gambling' | 'custom'
  redirect_target?: string
}

export interface ThreatFeed {
  id: number
  name: string
  url: string
  category: string
  enabled: boolean
  auto_update: boolean
  update_interval: number
  last_update?: string
  last_success?: string
  rule_count: number
  status: 'active' | 'error' | 'updating' | 'disabled'
  error_message?: string
  created_at: string
  updated_at: string
}

export interface ThreatFeedFormData {
  name: string
  url: string
  category: string
  enabled: boolean
  auto_update: boolean
  update_interval: number
}

export interface SecurityStatistics {
  blocked_today: number
  blocked_this_week: number
  blocked_this_month: number
  top_blocked_domains: Array<{ domain: string; count: number; category: string }>
  blocks_by_hour: Array<{ hour: string; count: number }>
  threat_feed_stats: Array<{ feed: string; rules: number; last_update: string }>
  last_update?: string
}

export interface RPZRuleTemplate {
  id: string
  name: string
  description: string
  category: string
  action: 'block' | 'redirect' | 'passthru'
  zone: string
  redirect_target?: string
  domains: string[]
  created_at: string
  updated_at: string
}

export interface RPZRuleTemplateFormData {
  name: string
  description: string
  category: string
  action: 'block' | 'redirect' | 'passthru'
  zone: string
  redirect_target?: string
  domains: string[]
}

export interface BulkImportResult {
  success: number
  failed: number
  errors: string[]
  imported_rules: RPZRule[]
}

export interface DomainValidationResult {
  domain: string
  valid: boolean
  error?: string
  suggestion?: string
}

// Theme types
export type Theme = 'light' | 'dark'

// Navigation types
export interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  current: boolean
}

// Error types
export interface ApiError {
  message: string
  details?: string[]
  code?: string
}