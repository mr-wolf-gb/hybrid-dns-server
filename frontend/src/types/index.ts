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
  rpz_zone: string
  domain: string
  action: 'block' | 'redirect' | 'passthru'
  category: 'malware' | 'phishing' | 'social_media' | 'adult' | 'gambling' | 'custom'
  redirect_target?: string
  is_active: boolean
  source: string
  description?: string
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
  rpz_zone: string
  domain: string
  action: 'block' | 'redirect' | 'passthru'
  category: 'malware' | 'phishing' | 'social_media' | 'adult' | 'gambling' | 'custom'
  redirect_target?: string
}

export interface ThreatFeed {
  id: number
  name: string
  url: string
  feed_type: string
  format_type: string
  update_frequency: number
  description?: string
  is_active: boolean
  last_updated?: string
  last_update_status?: 'success' | 'failed' | 'pending' | 'never'
  last_update_error?: string
  rules_count: number
  created_at: string
  updated_at: string
}

export interface ThreatFeedFormData {
  name: string
  url: string
  feed_type: string
  format_type: string
  update_frequency: number
  description?: string
  is_active: boolean
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
}// Enhanced 
RPZ and Threat Feed types
export interface ThreatFeedStatus {
  id: number
  name: string
  is_active: boolean
  last_updated?: string
  last_update_status?: 'success' | 'failed' | 'pending' | 'never'
  last_update_error?: string
  rules_count: number
  next_update?: string
}

export interface ThreatFeedUpdateResult {
  feed_id: number
  status: 'success' | 'failed' | 'pending'
  message: string
  rules_added: number
  rules_updated: number
  rules_removed: number
  error?: string
}

export interface BulkThreatFeedUpdateResult {
  successful_updates: number
  failed_updates: number
  feed_results: ThreatFeedUpdateResult[]
}

export interface RPZStatistics {
  total_rules: number
  active_rules: number
  inactive_rules: number
  rules_by_action: Record<string, number>
  rules_by_source: Record<string, number>
  rules_by_category: Record<string, number>
  zone?: string
}

export interface BlockedQueryReport {
  query_results: BlockedQuery[]
  summary: {
    total_blocked: number
    unique_domains: number
    unique_clients: number
    time_period: string
  }
  hourly_breakdown: Array<{
    hour: string
    blocked_count: number
  }>
  filters_applied: {
    hours: number
    category?: string
    client_ip?: string
    domain?: string
  }
}

export interface BlockedQuery {
  id: number
  timestamp: string
  client_ip: string
  domain: string
  category: string
  action: string
  rpz_zone: string
}

export interface ThreatDetectionReport {
  report_period: {
    days: number
    start_date: string
    end_date: string
  }
  executive_summary: {
    total_threats_blocked: number
    unique_threat_domains: number
    threat_sources_identified: number
    most_active_threat_category: string
    average_daily_blocks: number
    threat_detection_rate: number
  }
  threat_categories: Record<string, {
    blocked_count: number
    unique_domains: number
    percentage: number
  }>
  feed_effectiveness: Array<{
    feed_name: string
    rules_count: number
    blocks_generated: number
    effectiveness_score: number
  }>
  threat_timeline: Array<{
    date: string
    blocked_count: number
    categories: Record<string, number>
  }>
  top_threat_sources: Array<{
    domain: string
    block_count: number
    category: string
    first_seen: string
    last_seen: string
  }>
}

export interface RPZBulkUpdateRequest {
  rule_ids: number[]
  update_data: Partial<RPZRuleFormData>
}

export interface RPZBulkUpdateResult {
  updated_count: number
  error_count: number
  errors: string[]
}

export interface RPZBulkDeleteRequest {
  rule_ids: number[]
}

export interface RPZBulkDeleteResult {
  deleted_count: number
  error_count: number
  errors: string[]
}

export interface RPZBulkCategorizeRequest {
  rule_ids: number[]
  new_category: string
}

export interface RPZBulkCategorizeResult {
  updated_count: number
  error_count: number
  errors: string[]
}

export interface RPZCategoryStatus {
  category: string
  status: 'enabled' | 'disabled' | 'mixed' | 'empty'
  total_rules: number
  active_rules: number
  inactive_rules: number
  enabled_percentage: number
}

export interface RPZCategoryToggleResult {
  category: string
  updated_count: number
  errors: string[]
}

export interface CustomThreatList {
  id: number
  name: string
  description?: string
  domains_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ThreatIntelligenceStats {
  threat_feeds: {
    total_feeds: number
    active_feeds: number
    feeds_by_type: Record<string, number>
    total_rules_from_feeds: number
    update_status_counts: Record<string, number>
    feeds_due_for_update: number
  }
  rpz_rules: RPZStatistics
  protection_coverage: {
    total_domains_protected: number
    active_threat_feeds: number
    custom_lists: number
    external_feeds: number
  }
  update_health: {
    feeds_up_to_date: number
    feeds_with_errors: number
    feeds_never_updated: number
    feeds_due_for_update: number
  }
  generated_at: string
}