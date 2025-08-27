import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ServerIcon, CheckCircleIcon, XCircleIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Card, Button, Input, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface ZoneTestForm {
  zoneName: string
  nameserver?: string
}

interface ZoneTestResult {
  zone_name: string
  nameserver?: string
  success: boolean
  soa_record?: {
    primary_ns: string
    admin_email: string
    serial: number
    refresh: number
    retry: number
    expire: number
    minimum: number
  }
  ns_records: string[]
  zone_transfer_allowed: boolean
  dnssec_enabled: boolean
  error?: string
}

export const ZoneTestTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ZoneTestResult | null>(null)
  const [history, setHistory] = useState<ZoneTestResult[]>([])

  const { register, handleSubmit, formState: { errors }, reset } = useForm<ZoneTestForm>()

  const onSubmit = async (data: ZoneTestForm) => {
    setIsLoading(true)
    try {
      const response = await api.post<ZoneTestResult>('/diagnostics/zone-test', {
        zone_name: data.zoneName,
        nameserver: data.nameserver || undefined
      })

      setResult(response.data)
      setHistory(prev => [response.data, ...prev.slice(0, 9)]) // Keep last 10 results
      
      if (response.data.success) {
        toast.success(`Zone test completed for ${response.data.zone_name}`)
      } else {
        toast.warning(`Zone test failed: ${response.data.error}`)
      }
    } catch (error) {
      toast.error('Failed to perform zone test')
      console.error('Zone test error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  return (
    <div className="space-y-6">
      {/* Zone Test Form */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <ServerIcon className="h-5 w-5 mr-2" />
          Zone Test Configuration
        </h3>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Zone Name *
              </label>
              <Input
                {...register('zoneName', { 
                  required: 'Zone name is required',
                  pattern: {
                    value: /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$/,
                    message: 'Invalid zone name format'
                  }
                })}
                placeholder="example.com"
                error={errors.zoneName?.message}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Nameserver (optional)
              </label>
              <Input
                {...register('nameserver', {
                  pattern: {
                    value: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
                    message: 'Invalid IP address format'
                  }
                })}
                placeholder="8.8.8.8"
                error={errors.nameserver?.message}
              />
            </div>
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <Loading size="sm" /> : 'Test Zone'}
            </Button>
            <Button type="button" variant="outline" onClick={() => reset()}>
              Clear
            </Button>
          </div>
        </form>
      </Card>

      {/* Results */}
      {result && (
        <Card className="p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Zone Test Results
          </h3>
          
          <div className="space-y-6">
            {/* Overall Status */}
            <div className="flex items-center space-x-4">
              <Badge className={result.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                {result.success ? 'ZONE HEALTHY' : 'ZONE ISSUES'}
              </Badge>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Zone: {result.zone_name}
              </span>
              {result.nameserver && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Nameserver: {result.nameserver}
                </span>
              )}
            </div>

            {/* Feature Status Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">SOA Record</span>
                  {result.soa_record ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  )}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {result.soa_record ? 'Found' : 'Not found'}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">NS Records</span>
                  {result.ns_records.length > 0 ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  )}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {result.ns_records.length} nameservers
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">DNSSEC</span>
                  {result.dnssec_enabled ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-gray-400" />
                  )}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {result.dnssec_enabled ? 'Enabled' : 'Disabled'}
                </div>
              </div>
            </div>

            {/* SOA Record Details */}
            {result.soa_record && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center">
                  <ServerIcon className="h-4 w-4 mr-2" />
                  SOA Record Details
                </h4>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Primary NS:</span>
                      <div className="text-gray-900 dark:text-white font-mono">
                        {result.soa_record.primary_ns}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Admin Email:</span>
                      <div className="text-gray-900 dark:text-white font-mono">
                        {result.soa_record.admin_email}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Serial:</span>
                      <div className="text-gray-900 dark:text-white font-mono">
                        {result.soa_record.serial}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Refresh:</span>
                      <div className="text-gray-900 dark:text-white">
                        {formatTime(result.soa_record.refresh)}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Retry:</span>
                      <div className="text-gray-900 dark:text-white">
                        {formatTime(result.soa_record.retry)}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Expire:</span>
                      <div className="text-gray-900 dark:text-white">
                        {formatTime(result.soa_record.expire)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* NS Records */}
            {result.ns_records.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">
                  Nameservers ({result.ns_records.length})
                </h4>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="space-y-2">
                    {result.ns_records.map((ns, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <ServerIcon className="h-4 w-4 text-gray-400" />
                        <span className="text-sm font-mono text-gray-900 dark:text-white">
                          {ns}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Security Features */}
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center">
                <ShieldCheckIcon className="h-4 w-4 mr-2" />
                Security Features
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Zone Transfer (AXFR)
                    </span>
                    {result.zone_transfer_allowed ? (
                      <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                        ALLOWED
                      </Badge>
                    ) : (
                      <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        RESTRICTED
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {result.zone_transfer_allowed 
                      ? 'Zone transfers are allowed (security risk)'
                      : 'Zone transfers are properly restricted'
                    }
                  </div>
                </div>

                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      DNSSEC
                    </span>
                    {result.dnssec_enabled ? (
                      <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        ENABLED
                      </Badge>
                    ) : (
                      <Badge className="bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                        DISABLED
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {result.dnssec_enabled 
                      ? 'Zone is signed with DNSSEC'
                      : 'DNSSEC not configured'
                    }
                  </div>
                </div>
              </div>
            </div>

            {/* Error Message */}
            {result.error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">Error:</h4>
                <div className="text-sm text-red-700 dark:text-red-300">
                  {result.error}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* History */}
      {history.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Recent Zone Tests
          </h3>
          
          <div className="space-y-2">
            {history.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge className={item.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {item.success ? 'HEALTHY' : 'ISSUES'}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.zone_name}
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-sm text-gray-500 dark:text-gray-400">
                  <span>{item.ns_records.length} NS</span>
                  {item.dnssec_enabled && (
                    <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      DNSSEC
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}