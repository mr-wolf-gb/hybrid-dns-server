import React, { useState } from 'react'
import {
  WrenchScrewdriverIcon,
  GlobeAltIcon,
  ServerIcon,
  ShieldCheckIcon,
  CloudIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { Card, Button, Input, Select, Badge, Loading } from '@/components/ui'
import { DNSLookupTool } from '@/components/diagnostics/DNSLookupTool'
import { PingTool } from '@/components/diagnostics/PingTool'
import { ZoneTestTool } from '@/components/diagnostics/ZoneTestTool'
import { ForwarderTestTool } from '@/components/diagnostics/ForwarderTestTool'
import { ThreatTestTool } from '@/components/diagnostics/ThreatTestTool'
import { NetworkInfoTool } from '@/components/diagnostics/NetworkInfoTool'

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

  const filteredTools = diagnosticTools.filter(tool => 
    selectedCategory === 'all' || tool.category === selectedCategory
  )

  const renderTool = () => {
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
              >
                <option value="all">All Categories</option>
                <option value="dns">DNS Tools</option>
                <option value="network">Network Tools</option>
                <option value="security">Security Tools</option>
                <option value="system">System Tools</option>
              </Select>
            </div>
          </Card>

          {/* Tools Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTools.map((tool) => {
              const IconComponent = tool.icon
              return (
                <Card
                  key={tool.id}
                  className="p-6 hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-600"
                  onClick={() => setSelectedTool(tool.id)}
                >
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