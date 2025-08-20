import React, { useState } from 'react'
import {
  ServerIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { Button, Input, Card, Badge } from '@/components/ui'
import { isValidIP, isValidPort } from '@/utils'

interface ServerConfig {
  ip: string
  port?: number
  priority?: number
  weight?: number
  enabled?: boolean
  health_status?: 'healthy' | 'unhealthy' | 'unknown'
  response_time?: number
  last_check?: string
}

interface ServerConfigCardProps {
  server: ServerConfig
  index: number
  onUpdate: (index: number, server: ServerConfig) => void
  onRemove: (index: number) => void
  canRemove: boolean
  register: any
  errors: any
}

const ServerConfigCard: React.FC<ServerConfigCardProps> = ({
  server,
  index,
  onUpdate,
  onRemove,
  canRemove,
  register,
  errors,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)

  const parseServerString = (serverString: string) => {
    const parts = serverString.split(':')
    return {
      ip: parts[0] || '',
      port: parts[1] ? parseInt(parts[1], 10) : 53,
    }
  }



  const testConnection = async () => {
    setIsTestingConnection(true)
    try {
      // Simulate connection test
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Mock result
      const isHealthy = Math.random() > 0.3
      const responseTime = Math.floor(Math.random() * 200) + 10
      
      onUpdate(index, {
        ...server,
        health_status: isHealthy ? 'healthy' : 'unhealthy',
        response_time: responseTime,
        last_check: new Date().toISOString(),
      })
    } catch (error) {
      onUpdate(index, {
        ...server,
        health_status: 'unhealthy',
        last_check: new Date().toISOString(),
      })
    } finally {
      setIsTestingConnection(false)
    }
  }

  const getHealthIcon = () => {
    switch (server.health_status) {
      case 'healthy':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />
      case 'unhealthy':
        return <XCircleIcon className="h-4 w-4 text-red-500" />
      default:
        return <ClockIcon className="h-4 w-4 text-gray-400" />
    }
  }

  const getHealthBadge = () => {
    switch (server.health_status) {
      case 'healthy':
        return <Badge variant="success" size="sm">Healthy</Badge>
      case 'unhealthy':
        return <Badge variant="danger" size="sm">Unhealthy</Badge>
      default:
        return <Badge variant="default" size="sm">Unknown</Badge>
    }
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <ServerIcon className="h-5 w-5 text-gray-500" />
          <div>
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              DNS Server {index + 1}
            </h4>
            {server.health_status && (
              <div className="flex items-center space-x-2 mt-1">
                {getHealthIcon()}
                {getHealthBadge()}
                {server.response_time && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {server.response_time}ms
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            title="Advanced settings"
          >
            <Cog6ToothIcon className="h-4 w-4" />
          </Button>
          {canRemove && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onRemove(index)}
              className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              title="Remove server"
            >
              <TrashIcon className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {/* Basic Configuration */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <Input
              label="IP Address"
              placeholder="192.168.1.10"
              {...register(`servers.${index}`, {
                required: 'DNS server is required',
                validate: (value: string) => {
                  const parsed = parseServerString(value)
                  if (!isValidIP(parsed.ip)) {
                    return 'Invalid IP address format'
                  }
                  if (parsed.port && !isValidPort(parsed.port)) {
                    return 'Invalid port number (1-65535)'
                  }
                  return true
                },
              })}
              error={errors.servers?.[index]?.message}
              helperText="IP address with optional port (e.g., 192.168.1.10:5353)"
            />
          </div>

          <div className="flex flex-col justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={testConnection}
              loading={isTestingConnection}
              className="w-full"
            >
              Test Connection
            </Button>
          </div>
        </div>

        {/* Advanced Configuration */}
        {showAdvanced && (
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Advanced Settings
            </h5>
            
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Input
                label="Priority"
                type="number"
                min="1"
                max="100"
                placeholder="10"
                value={server.priority || ''}
                onChange={(e) => onUpdate(index, {
                  ...server,
                  priority: e.target.value ? parseInt(e.target.value, 10) : undefined
                })}
                helperText="Lower = higher priority"
              />

              <Input
                label="Weight"
                type="number"
                min="1"
                max="1000"
                placeholder="100"
                value={server.weight || ''}
                onChange={(e) => onUpdate(index, {
                  ...server,
                  weight: e.target.value ? parseInt(e.target.value, 10) : undefined
                })}
                helperText="Load balancing weight"
              />

              <div className="flex items-center space-x-3 pt-6">
                <input
                  type="checkbox"
                  id={`server-${index}-enabled`}
                  checked={server.enabled !== false}
                  onChange={(e) => onUpdate(index, {
                    ...server,
                    enabled: e.target.checked
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label 
                  htmlFor={`server-${index}-enabled`}
                  className="text-sm text-gray-700 dark:text-gray-300"
                >
                  Enabled
                </label>
              </div>
            </div>

            {/* Server Statistics */}
            {server.health_status && (
              <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <h6 className="text-xs font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Server Statistics
                </h6>
                <div className="grid grid-cols-2 gap-4 text-xs text-gray-600 dark:text-gray-400">
                  <div>
                    <span className="font-medium">Status:</span> {server.health_status}
                  </div>
                  <div>
                    <span className="font-medium">Response Time:</span>{' '}
                    {server.response_time ? `${server.response_time}ms` : 'N/A'}
                  </div>
                  <div className="col-span-2">
                    <span className="font-medium">Last Check:</span>{' '}
                    {server.last_check 
                      ? new Date(server.last_check).toLocaleString()
                      : 'Never'
                    }
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

export default ServerConfigCard