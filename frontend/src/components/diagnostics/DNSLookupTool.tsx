import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { GlobeAltIcon, ClockIcon, ServerIcon } from '@heroicons/react/24/outline'
import { Card, Button, Input, Select, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface DNSLookupForm {
  hostname: string
  recordType: string
  nameserver?: string
  timeout: number
}

interface DNSLookupResult {
  hostname: string
  record_type: string
  nameserver?: string
  success: boolean
  results: string[]
  response_time: number
  error?: string
  additional_info: {
    ttl?: number
    canonical_name?: string
    nameserver_used?: string
  }
}

const recordTypes = [
  'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SOA', 'PTR', 'SRV', 'CAA'
]

export const DNSLookupTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<DNSLookupResult | null>(null)
  const [history, setHistory] = useState<DNSLookupResult[]>([])

  const { register, handleSubmit, formState: { errors }, reset } = useForm<DNSLookupForm>({
    defaultValues: {
      recordType: 'A',
      timeout: 5
    }
  })

  const onSubmit = async (data: DNSLookupForm) => {
    setIsLoading(true)
    try {
      const response = await api.post<DNSLookupResult>('/diagnostics/dns-lookup', {
        hostname: data.hostname,
        record_type: data.recordType,
        nameserver: data.nameserver || undefined,
        timeout: data.timeout
      })

      setResult(response.data)
      setHistory(prev => [response.data, ...prev.slice(0, 9)]) // Keep last 10 results
      
      if (response.data.success) {
        toast.success(`DNS lookup completed in ${response.data.response_time.toFixed(2)}s`)
      } else {
        toast.warning(`DNS lookup failed: ${response.data.error}`)
      }
    } catch (error) {
      toast.error('Failed to perform DNS lookup')
      console.error('DNS lookup error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const formatResponseTime = (time: number) => {
    if (time < 1) {
      return `${(time * 1000).toFixed(0)}ms`
    }
    return `${time.toFixed(2)}s`
  }

  return (
    <div className="space-y-6">
      {/* DNS Lookup Form */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <GlobeAltIcon className="h-5 w-5 mr-2" />
          DNS Lookup Configuration
        </h3>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Hostname/Domain *
              </label>
              <Input
                {...register('hostname', { 
                  required: 'Hostname is required',
                  pattern: {
                    value: /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$/,
                    message: 'Invalid hostname format'
                  }
                })}
                placeholder="example.com"
                error={errors.hostname?.message}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Record Type
              </label>
              <Select {...register('recordType')}>
                {recordTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </Select>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Custom Nameserver (optional)
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
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timeout (seconds)
              </label>
              <Input
                type="number"
                {...register('timeout', { 
                  min: { value: 1, message: 'Minimum timeout is 1 second' },
                  max: { value: 30, message: 'Maximum timeout is 30 seconds' }
                })}
                min="1"
                max="30"
                error={errors.timeout?.message}
              />
            </div>
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <Loading size="sm" /> : 'Perform Lookup'}
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
            Lookup Results
          </h3>
          
          <div className="space-y-4">
            {/* Status */}
            <div className="flex items-center space-x-4">
              <Badge className={result.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                {result.success ? 'SUCCESS' : 'FAILED'}
              </Badge>
              <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                <ClockIcon className="h-4 w-4 mr-1" />
                {formatResponseTime(result.response_time)}
              </div>
              {result.additional_info.nameserver_used && (
                <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                  <ServerIcon className="h-4 w-4 mr-1" />
                  {result.additional_info.nameserver_used}
                </div>
              )}
            </div>

            {/* Query Info */}
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Hostname:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{result.hostname}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Record Type:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{result.record_type}</span>
                </div>
                {result.additional_info.ttl && (
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">TTL:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">{result.additional_info.ttl}s</span>
                  </div>
                )}
              </div>
            </div>

            {/* Results or Error */}
            {result.success && result.results.length > 0 ? (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">DNS Records:</h4>
                <div className="bg-gray-900 dark:bg-gray-800 rounded-lg p-4 font-mono text-sm">
                  {result.results.map((record, index) => (
                    <div key={index} className="text-green-400 dark:text-green-300">
                      {record}
                    </div>
                  ))}
                </div>
              </div>
            ) : result.error && (
              <div>
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">Error:</h4>
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
                  {result.error}
                </div>
              </div>
            )}

            {/* Additional Info */}
            {result.additional_info.canonical_name && result.additional_info.canonical_name !== result.hostname && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Canonical Name:</h4>
                <div className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                  {result.additional_info.canonical_name}
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
            Recent Lookups
          </h3>
          
          <div className="space-y-2">
            {history.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge className={item.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {item.record_type}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.hostname}
                  </span>
                  {item.success && item.results.length > 0 && (
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      → {item.results[0]}
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {formatResponseTime(item.response_time)}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}