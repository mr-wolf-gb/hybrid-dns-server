import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { CloudIcon, ClockIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { Card, Button, Input, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface ForwarderTestForm {
  domain: string
  forwarderIp: string
  expectedResult?: string
}

interface ForwarderTestResult {
  domain: string
  forwarder_ip: string
  success: boolean
  resolved_ip?: string
  response_time: number
  forwarding_working: boolean
  error?: string
}

export const ForwarderTestTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ForwarderTestResult | null>(null)
  const [history, setHistory] = useState<ForwarderTestResult[]>([])

  const { register, handleSubmit, formState: { errors }, reset } = useForm<ForwarderTestForm>()

  const onSubmit = async (data: ForwarderTestForm) => {
    setIsLoading(true)
    try {
      const response = await api.post<ForwarderTestResult>('/diagnostics/forwarder-test', {
        domain: data.domain,
        forwarder_ip: data.forwarderIp,
        expected_result: data.expectedResult || undefined
      })

      setResult(response.data)
      setHistory(prev => [response.data, ...prev.slice(0, 9)]) // Keep last 10 results
      
      if (response.data.success && response.data.forwarding_working) {
        toast.success(`Forwarder test successful - ${response.data.response_time.toFixed(2)}s`)
      } else if (response.data.success && !response.data.forwarding_working) {
        toast.warning('Forwarder responded but result doesn\'t match expected')
      } else {
        toast.error(`Forwarder test failed: ${response.data.error}`)
      }
    } catch (error) {
      toast.error('Failed to perform forwarder test')
      console.error('Forwarder test error:', error)
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
      {/* Forwarder Test Form */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <CloudIcon className="h-5 w-5 mr-2" />
          Forwarder Test Configuration
        </h3>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Domain to Test *
              </label>
              <Input
                {...register('domain', { 
                  required: 'Domain is required',
                  pattern: {
                    value: /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$/,
                    message: 'Invalid domain format'
                  }
                })}
                placeholder="example.com"
                error={errors.domain?.message}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Forwarder IP Address *
              </label>
              <Input
                {...register('forwarderIp', { 
                  required: 'Forwarder IP is required',
                  pattern: {
                    value: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
                    message: 'Invalid IP address format'
                  }
                })}
                placeholder="8.8.8.8"
                error={errors.forwarderIp?.message}
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Expected Result (optional)
            </label>
            <Input
              {...register('expectedResult', {
                pattern: {
                  value: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
                  message: 'Invalid IP address format'
                }
              })}
              placeholder="192.168.1.1"
              error={errors.expectedResult?.message}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              If provided, the test will verify the resolved IP matches this value
            </p>
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <Loading size="sm" /> : 'Test Forwarder'}
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
            Forwarder Test Results
          </h3>
          
          <div className="space-y-4">
            {/* Status Overview */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Connection</div>
                <div className="flex items-center mt-1">
                  {result.success ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                  )}
                  <Badge className={result.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {result.success ? 'SUCCESS' : 'FAILED'}
                  </Badge>
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Forwarding</div>
                <div className="flex items-center mt-1">
                  {result.forwarding_working ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                  )}
                  <Badge className={result.forwarding_working ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {result.forwarding_working ? 'WORKING' : 'FAILED'}
                  </Badge>
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Response Time</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white flex items-center mt-1">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  {formatResponseTime(result.response_time)}
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Resolved IP</div>
                <div className="text-sm font-mono text-gray-900 dark:text-white mt-1">
                  {result.resolved_ip || 'N/A'}
                </div>
              </div>
            </div>

            {/* Test Details */}
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 dark:text-white mb-3">Test Configuration</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Domain:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-mono">{result.domain}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Forwarder:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-mono">{result.forwarder_ip}</span>
                </div>
              </div>
            </div>

            {/* Resolution Details */}
            {result.success && result.resolved_ip && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Resolution Success</h4>
                <div className="text-sm text-blue-800 dark:text-blue-200">
                  <div className="flex items-center justify-between">
                    <span>Domain <span className="font-mono">{result.domain}</span> resolved to:</span>
                    <span className="font-mono font-semibold">{result.resolved_ip}</span>
                  </div>
                  <div className="mt-2 text-xs">
                    Response time: {formatResponseTime(result.response_time)}
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {result.error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">Error Details:</h4>
                <div className="text-sm text-red-700 dark:text-red-300">
                  {result.error}
                </div>
              </div>
            )}

            {/* Troubleshooting Tips */}
            {!result.success && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <h4 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">Troubleshooting Tips:</h4>
                <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                  <li>• Verify the forwarder IP address is correct and reachable</li>
                  <li>• Check if the forwarder is configured to accept queries from your server</li>
                  <li>• Ensure the domain name is valid and exists</li>
                  <li>• Test with a known working DNS server (e.g., 8.8.8.8) first</li>
                  <li>• Check network connectivity and firewall rules</li>
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* History */}
      {history.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Recent Forwarder Tests
          </h3>
          
          <div className="space-y-2">
            {history.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge className={item.forwarding_working ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {item.forwarding_working ? 'OK' : 'FAIL'}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.domain}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    → {item.forwarder_ip}
                  </span>
                  {item.resolved_ip && (
                    <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                      ({item.resolved_ip})
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