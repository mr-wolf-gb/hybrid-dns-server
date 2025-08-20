import React from 'react'
import {
  InformationCircleIcon,
  ServerIcon,
  GlobeAltIcon,
  EnvelopeIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  CloudIcon,
} from '@heroicons/react/24/outline'
import { RecordFormData } from '@/types'
import { Card } from '@/components/ui'

interface RecordTemplate {
  id: string
  name: string
  description: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  data: Partial<RecordFormData>
  category: 'web' | 'mail' | 'security' | 'service' | 'infrastructure'
}

interface RecordTemplatesProps {
  recordType: string
  onApplyTemplate: (template: Partial<RecordFormData>) => void
}

const RecordTemplates: React.FC<RecordTemplatesProps> = ({
  recordType,
  onApplyTemplate,
}) => {
  const templates: Record<string, RecordTemplate[]> = {
    A: [
      {
        id: 'web-server',
        name: 'Web Server',
        description: 'Standard web server configuration',
        icon: GlobeAltIcon,
        category: 'web',
        data: { name: 'www', value: '192.168.1.10', ttl: 3600 },
      },
      {
        id: 'load-balancer',
        name: 'Load Balancer',
        description: 'Load balancer with shorter TTL for failover',
        icon: ServerIcon,
        category: 'infrastructure',
        data: { name: 'lb', value: '10.0.0.100', ttl: 300 },
      },
      {
        id: 'cdn-endpoint',
        name: 'CDN Endpoint',
        description: 'CDN endpoint with long TTL for caching',
        icon: CloudIcon,
        category: 'web',
        data: { name: 'cdn', value: '203.0.113.1', ttl: 86400 },
      },
      {
        id: 'api-server',
        name: 'API Server',
        description: 'API server endpoint',
        icon: CpuChipIcon,
        category: 'service',
        data: { name: 'api', value: '192.168.1.20', ttl: 3600 },
      },
    ],
    AAAA: [
      {
        id: 'ipv6-web-server',
        name: 'IPv6 Web Server',
        description: 'IPv6 web server configuration',
        icon: GlobeAltIcon,
        category: 'web',
        data: { name: 'www', value: '2001:db8::1', ttl: 3600 },
      },
      {
        id: 'ipv6-mail-server',
        name: 'IPv6 Mail Server',
        description: 'IPv6 mail server configuration',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: 'mail', value: '2001:db8::10', ttl: 3600 },
      },
    ],
    CNAME: [
      {
        id: 'www-alias',
        name: 'WWW Alias',
        description: 'Standard www subdomain alias',
        icon: GlobeAltIcon,
        category: 'web',
        data: { name: 'www', value: '@', ttl: 3600 },
      },
      {
        id: 'ftp-alias',
        name: 'FTP Alias',
        description: 'FTP service alias',
        icon: ServerIcon,
        category: 'service',
        data: { name: 'ftp', value: 'files.example.com', ttl: 3600 },
      },
      {
        id: 'mail-alias',
        name: 'Mail Alias',
        description: 'Mail service alias',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: 'mail', value: 'mail.example.com', ttl: 3600 },
      },
    ],
    MX: [
      {
        id: 'primary-mail',
        name: 'Primary Mail Server',
        description: 'Primary mail exchange server',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: '@', value: 'mail.example.com', priority: 10, ttl: 3600 },
      },
      {
        id: 'backup-mail',
        name: 'Backup Mail Server',
        description: 'Secondary mail exchange server',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: '@', value: 'mail2.example.com', priority: 20, ttl: 3600 },
      },
      {
        id: 'google-workspace',
        name: 'Google Workspace',
        description: 'Google Workspace mail configuration',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: '@', value: 'aspmx.l.google.com', priority: 1, ttl: 3600 },
      },
      {
        id: 'microsoft-365',
        name: 'Microsoft 365',
        description: 'Microsoft 365 mail configuration',
        icon: EnvelopeIcon,
        category: 'mail',
        data: { name: '@', value: 'outlook.com', priority: 0, ttl: 3600 },
      },
    ],
    TXT: [
      {
        id: 'spf-record',
        name: 'SPF Record',
        description: 'Sender Policy Framework record',
        icon: ShieldCheckIcon,
        category: 'security',
        data: { name: '@', value: 'v=spf1 include:_spf.google.com ~all', ttl: 3600 },
      },
      {
        id: 'dkim-record',
        name: 'DKIM Record',
        description: 'DomainKeys Identified Mail record',
        icon: ShieldCheckIcon,
        category: 'security',
        data: { name: 'default._domainkey', value: 'v=DKIM1; k=rsa; p=...', ttl: 3600 },
      },
      {
        id: 'dmarc-record',
        name: 'DMARC Record',
        description: 'Domain-based Message Authentication record',
        icon: ShieldCheckIcon,
        category: 'security',
        data: { name: '_dmarc', value: 'v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com', ttl: 3600 },
      },
      {
        id: 'domain-verification',
        name: 'Domain Verification',
        description: 'Generic domain verification record',
        icon: ShieldCheckIcon,
        category: 'security',
        data: { name: '@', value: 'verification-code-here', ttl: 300 },
      },
    ],
    SRV: [
      {
        id: 'sip-service',
        name: 'SIP Service',
        description: 'Session Initiation Protocol service',
        icon: CpuChipIcon,
        category: 'service',
        data: { name: '_sip._tcp', value: 'sip.example.com', priority: 10, weight: 5, port: 5060, ttl: 3600 },
      },
      {
        id: 'xmpp-service',
        name: 'XMPP Service',
        description: 'Extensible Messaging and Presence Protocol',
        icon: CpuChipIcon,
        category: 'service',
        data: { name: '_xmpp-server._tcp', value: 'xmpp.example.com', priority: 5, weight: 0, port: 5222, ttl: 3600 },
      },
      {
        id: 'minecraft-server',
        name: 'Minecraft Server',
        description: 'Minecraft game server',
        icon: CpuChipIcon,
        category: 'service',
        data: { name: '_minecraft._tcp', value: 'mc.example.com', priority: 0, weight: 5, port: 25565, ttl: 3600 },
      },
    ],
    PTR: [
      {
        id: 'reverse-dns',
        name: 'Reverse DNS',
        description: 'Standard reverse DNS record',
        icon: ServerIcon,
        category: 'infrastructure',
        data: { name: '10', value: 'server.example.com', ttl: 3600 },
      },
    ],
    NS: [
      {
        id: 'primary-ns',
        name: 'Primary Name Server',
        description: 'Primary authoritative name server',
        icon: ServerIcon,
        category: 'infrastructure',
        data: { name: '@', value: 'ns1.example.com', ttl: 86400 },
      },
      {
        id: 'secondary-ns',
        name: 'Secondary Name Server',
        description: 'Secondary authoritative name server',
        icon: ServerIcon,
        category: 'infrastructure',
        data: { name: '@', value: 'ns2.example.com', ttl: 86400 },
      },
    ],
  }

  const currentTemplates = templates[recordType] || []

  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'web':
        return 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
      case 'mail':
        return 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
      case 'security':
        return 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
      case 'service':
        return 'bg-purple-50 border-purple-200 dark:bg-purple-900/20 dark:border-purple-800'
      case 'infrastructure':
        return 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800'
      default:
        return 'bg-gray-50 border-gray-200 dark:bg-gray-900/20 dark:border-gray-800'
    }
  }

  const getCategoryTextColor = (category: string): string => {
    switch (category) {
      case 'web':
        return 'text-blue-900 dark:text-blue-100'
      case 'mail':
        return 'text-green-900 dark:text-green-100'
      case 'security':
        return 'text-red-900 dark:text-red-100'
      case 'service':
        return 'text-purple-900 dark:text-purple-100'
      case 'infrastructure':
        return 'text-orange-900 dark:text-orange-100'
      default:
        return 'text-gray-900 dark:text-gray-100'
    }
  }

  if (currentTemplates.length === 0) {
    return null
  }

  return (
    <Card className={`p-4 ${getCategoryColor('web')}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className={`text-sm font-medium ${getCategoryTextColor('web')}`}>
          Quick Templates for {recordType} Records
        </h3>
        <InformationCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {currentTemplates.map((template) => {
          const IconComponent = template.icon
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => onApplyTemplate(template.data)}
              className={`text-left p-3 rounded-lg border transition-colors hover:shadow-sm ${getCategoryColor(template.category)} hover:bg-opacity-80`}
            >
              <div className="flex items-start space-x-3">
                <div className={`flex-shrink-0 p-1 rounded ${getCategoryTextColor(template.category)}`}>
                  <IconComponent className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`font-medium text-sm ${getCategoryTextColor(template.category)}`}>
                    {template.name}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {template.description}
                  </div>
                  <div className="text-xs font-mono text-gray-500 dark:text-gray-500 mt-2 truncate">
                    {template.data.value}
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </Card>
  )
}

export default RecordTemplates