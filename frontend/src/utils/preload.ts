/**
 * Preload utility for lazy-loaded components
 * This helps improve perceived performance by preloading components
 * that are likely to be used soon
 */

// Preload functions for diagnostic tools
export const preloadDiagnosticTools = {
  dnsLookup: () => import('@/components/diagnostics/DNSLookupTool'),
  ping: () => import('@/components/diagnostics/PingTool'),
  zoneTest: () => import('@/components/diagnostics/ZoneTestTool'),
  forwarderTest: () => import('@/components/diagnostics/ForwarderTestTool'),
  threatTest: () => import('@/components/diagnostics/ThreatTestTool'),
  networkInfo: () => import('@/components/diagnostics/NetworkInfoTool'),
}

// Preload functions for pages
export const preloadPages = {
  dashboard: () => import('@/pages/Dashboard'),
  dnsZones: () => import('@/pages/DNSZones'),
  forwarders: () => import('@/pages/Forwarders'),
  security: () => import('@/pages/Security'),
  diagnostics: () => import('@/pages/DiagnosticTools'),
  queryLogs: () => import('@/pages/QueryLogs'),
  settings: () => import('@/pages/Settings'),
  healthMonitoring: () => import('@/pages/HealthMonitoring'),
  realTimeDashboard: () => import('@/pages/RealTimeDashboard'),
  events: () => import('@/pages/Events'),
  reports: () => import('@/pages/Reports'),
  analytics: () => import('@/pages/Analytics'),
}

// Preload commonly used pages on app initialization
export const preloadCriticalPages = () => {
  // Preload dashboard and DNS zones as they are most commonly accessed
  setTimeout(() => {
    preloadPages.dashboard()
    preloadPages.dnsZones()
  }, 1000) // Delay to not interfere with initial load
}

// Preload diagnostic tools when user navigates to diagnostics page
export const preloadAllDiagnosticTools = () => {
  Object.values(preloadDiagnosticTools).forEach(preload => {
    setTimeout(() => preload(), Math.random() * 2000) // Stagger the preloads
  })
}

// Preload specific diagnostic tool
export const preloadDiagnosticTool = (toolId: string) => {
  const preloadMap: Record<string, () => Promise<any>> = {
    'dns-lookup': preloadDiagnosticTools.dnsLookup,
    'ping': preloadDiagnosticTools.ping,
    'zone-test': preloadDiagnosticTools.zoneTest,
    'forwarder-test': preloadDiagnosticTools.forwarderTest,
    'threat-test': preloadDiagnosticTools.threatTest,
    'network-info': preloadDiagnosticTools.networkInfo,
  }
  
  const preloadFn = preloadMap[toolId]
  if (preloadFn) {
    preloadFn()
  }
}