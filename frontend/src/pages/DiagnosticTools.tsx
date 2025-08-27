import React, { useState, useEffect } from 'react'
import {
  WrenchScrewdriverIcon,
  GlobeAltIcon,
  ServerIcon,
  ShieldCheckIcon,
  CloudIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { Card, Button, Select, Badge } from '@/components/ui'
import { preloadAllDiagnosticTools, preloadDiagnosticTool } from '@/utils/preload'
// Lazy load diagnostic tool components for better performance
const DNSLookupTool = React.lazy(() => import('@/components/diagnostics/DNSLookupTool').then(m => ({ default: m.DNSLookupTool })))
const PingTool = React.lazy(() => import('@/components/diagnostics/PingTool').then(m => ({ default: m.PingTool })))
const ZoneTestTool = React.lazy(() => import('@/components/diagnostics/ZoneTestTool').then(m => ({ default: m.ZoneTestTool })))
const ForwarderTestTool = React.lazy(() => import('@/components/diagnostics/ForwarderTestTool').then(m => ({ default: m.ForwarderTestTool })))
const ThreatTestTool = React.lazy(() => import('@/components/diagnostics/ThreatTestTool').then(m => ({ default: m.ThreatTestTool })))
const NetworkInfoTool = React.lazy(() => import('@/components/diagnostics/NetworkInfoTool').then(m => ({ default: m.NetworkInfoTool })))

type DiagnosticTool = 
  | 'dns-lookup'
  | 'ping'
  | 'zone-test'
  | 'forwarder-test'
  | 'threat-test'
  | 'network-info'

interface ToolConfig {
  id: DiagnosticTool
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  category: 'dns' | 'network' | 'security' | 'system'
}

const diagnosticTools: ToolConfig[] = [
  {
    id: 'dns-lookup',
    name: 'DNS Lookup',
    description: 'Resolve DNS records for any domain with detailed information',
    icon: GlobeAltIcon,
    category: 'dns'
  },
  {
    id: 'ping',
    name: 'Ping Test',
    description: 'Test network connectivity and latency to any host',
    icon: ServerIcon,
    category: 'network'
  },
  {
    id: 'zone-test',
    name: 'Zone Testing',
    description: 'Validate DNS zone configuration and health',
    icon: ServerIcon,
    category: 'dns'
  },
  {
    id: 'forwarder-test',
    name: 'Forwarder Test',
    description: 'Test DNS forwarder configuration and functionality',
    icon: CloudIcon,
    category: 'dns'
  },
  {
    id: 'threat-test',
    name: 'Threat & URL Test',
    description: 'Check domains and URLs for threats and RPZ blocking',
    icon: ShieldCheckIcon,
    category: 'security'
  },
  {
    id: 'network-info',
    name: 'Network Information',
    description: 'Display system network configuration and DNS settings',
    icon: InformationCircleIcon,
    category: 'system'
  }
]

const categoryColors = {
  dns: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  network: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  security: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  system: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
}

const DiagnosticTools: React.FC = () => {
  const [selectedTool, setSelectedTool] = useState<DiagnosticTool | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // Preload all diagnostic tools when component mounts
  useEffect(() => {
    preloadAllDiagnosticTools()
  }, [])

  // Preload specific tool when user hovers over it
  const handleToolHover = (toolId: DiagnosticTool) => {
    preloadDiagnosticTool(toolId)
  }

  const filteredTools = diagnosticTools.filter(tool => 
    selectedCategory === 'all' || tool.category === selectedCategory
  )

  const renderTool = () => {
    const toolComponent = (() => {
      switch (selectedTool) {
        case 'dns-lookup':
          return <DNSLookupTool />
        case 'ping':
          return <PingTool />
        case 'zone-test':
          return <ZoneTestTool />
        case 'forwarder-test':
          return <ForwarderTestTool />
        case 'threat-test':
          return <ThreatTestTool />
        case 'network-info':
          return <NetworkInfoTool />
        default:
          return null
      }
    })()

    if (!toolComponent) return null

    return (
      <React.Suspense fallback={
        <Card className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-500 dark:text-gray-400">Loading diagnostic tool...</p>
            </div>
          </div>
        </Card>
      }>
        {toolComponent}
      </React.Suspense>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <WrenchScrewdriverIcon className="h-8 w-8 mr-3 text-primary-600" />
            Diagnostic Tools
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Comprehensive DNS and network diagnostic utilities
          </p>
        </div>
        
        {selectedTool && (
          <Button
            variant="outline"
            onClick={() => setSelectedTool(null)}
          >
            Back to Tools
          </Button>
        )}
      </div>

      {!selectedTool ? (
        <>
          {/* Category Filter */}
          <Card className="p-4">
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Filter by category:
              </label>
              <Select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-48"
                options={[
                  { value: 'all', label: 'All Categories' },
                  { value: 'dns', label: 'DNS Tools' },
                  { value: 'network', label: 'Network Tools' },
                  { value: 'security', label: 'Security Tools' },
                  { value: 'system', label: 'System Tools' }
                ]}
              />
            </div>
          </Card>

          {/* Tools Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTools.map((tool) => {
              const IconComponent = tool.icon
              return (
                <div
                  key={tool.id}
                  className="cursor-pointer"
                  onClick={() => setSelectedTool(tool.id)}
                  onMouseEnter={() => handleToolHover(tool.id)}
                >
                  <Card className="p-6 hover:shadow-lg transition-shadow border-2 hover:border-primary-300 dark:hover:border-primary-600">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <IconComponent className="h-8 w-8 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                          {tool.name}
                        </h3>
                        <Badge className={categoryColors[tool.category]}>
                          {tool.category.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {tool.description}
                      </p>
                      <div className="mt-4">
                        <Button size="sm" className="w-full">
                          Open Tool
                        </Button>
                      </div>
                    </div>
                  </div>
                  </Card>
                </div>
              )
            })}
          </div>

          {/* Quick Actions */}
          <Card className="p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Quick Actions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button
                variant="outline"
                onClick={() => setSelectedTool('dns-lookup')}
                className="flex items-center justify-center space-x-2"
              >
                <GlobeAltIcon className="h-5 w-5" />
                <span>Quick DNS Lookup</span>
              </Button>
              <Button
                variant="outline"
                onClick={() => setSelectedTool('ping')}
                className="flex items-center justify-center space-x-2"
              >
                <ServerIcon className="h-5 w-5" />
                <span>Quick Ping Test</span>
              </Button>
              <Button
                variant="outline"
                onClick={() => setSelectedTool('network-info')}
                className="flex items-center justify-center space-x-2"
              >
                <InformationCircleIcon className="h-5 w-5" />
                <span>Network Info</span>
              </Button>
            </div>
          </Card>
        </>
      ) : (
        /* Selected Tool */
        <div className="space-y-6">
          {/* Tool Header */}
          <Card className="p-4">
            <div className="flex items-center space-x-4">
              {(() => {
                const tool = diagnosticTools.find(t => t.id === selectedTool)
                if (!tool) return null
                const IconComponent = tool.icon
                return (
                  <>
                    <IconComponent className="h-8 w-8 text-primary-600 dark:text-primary-400" />
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                        {tool.name}
                      </h2>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {tool.description}
                      </p>
                    </div>
                    <div className="ml-auto">
                      <Badge className={categoryColors[tool.category]}>
                        {tool.category.toUpperCase()}
                      </Badge>
                    </div>
                  </>
                )
              })()}
            </div>
          </Card>

          {/* Tool Component */}
          {renderTool()}
        </div>
      )}
    </div>
  )
}

export default DiagnosticTools