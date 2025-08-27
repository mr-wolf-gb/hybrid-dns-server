import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ShieldCheckIcon, ExclamationTriangleIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { Card, Button, Input, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface ThreatTestForm {
  domain: string
  url?: string
}

interface ThreatTestResult {
  domain: string
  url?: string
  is_blocked: boolean
  threat_category?: string
  rpz_rule_matched?: string
  dns_response?: string
  reputation_score?: number
  error?: string
}

export const ThreatTestTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ThreatTestResult | null>(null)
  const [history, setHistory] = useState<ThreatTestResult[]>([])

  const { register, handleSubmit, formState: { errors }, reset } = useForm<ThreatTestForm>()

  const onSubmit = async (data: ThreatTestForm) => {
    setIsLoading(true)
    try {
      const response = await api.post<ThreatTestResult>('/diagnostics/threat-test', {
        domain: data.domain,
        url: data.url || undefined
      })

      setResult(response.data)
      setHistory(prev => [response.data, ...prev.slice(0, 9)]) // Keep last 10 results
      
      if (response.data.is_blocked) {
        toast.warning(`Threat detected and blocked: ${response.data.threat_category || 'Unknown category'}`)
      } else {
        toast.success('No threats detected - domain appears safe')
      }
    } catch (error) {
      toast.error('Failed to perform threat test')
      console.error('Threat test error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getThreatLevelColor = (isBlocked: boolean, category?: string) => {
    if (isBlocked) {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    }
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  }

  const getReputationColor = (score?: number) => {
    if (!score) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    if (score >= 0.7) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  }

  const getReputationLabel = (score?: number) => {
    if (!score) return 'Unknown'
    if (score >= 0.7) return 'Good'
    if (score >= 0.4) return 'Neutral'
    return 'Poor'
  }

  return (
    <div className="space-y-6">
      {/* Threat Test Form */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <ShieldCheckIcon className="h-5 w-5 mr-2" />
          Threat & URL Test Configuration
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
                placeholder="suspicious-domain.com"
                error={errors.domain?.message}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Full URL (optional)
              </label>
              <Input
                {...register('url', {
                  pattern: {
                    value: /^https?:\/\/.+/,
                    message: 'URL must start with http:// or https://'
                  }
                })}
                placeholder="https://suspicious-domain.com/malware"
                error={errors.url?.message}
              />
            </div>
          </div>
          
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
              <div className="text-sm text-blue-800 dark:text-blue-200">
                <p className="font-medium mb-1">Security Testing Information:</p>
                <ul className="space-y-1 text-xs">
                  <li>• This tool checks if domains are blocked by your RPZ (Response Policy Zone) rules</li>
                  <li>• It performs DNS resolution to detect blocking mechanisms</li>
                  <li>• URL testing provides additional context for threat analysis</li>
                  <li>• Results help validate your DNS security configuration</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-3">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <Loading size="sm" /> : 'Test for Threats'}
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
            Threat Analysis Results
          </h3>
          
          <div className="space-y-6">
            {/* Threat Status Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Threat Status</div>
                <div className="flex items-center mt-2">
                  {result.is_blocked ? (
                    <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                  ) : (
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                  )}
                  <Badge className={getThreatLevelColor(result.is_blocked, result.threat_category)}>
                    {result.is_blocked ? 'BLOCKED' : 'ALLOWED'}
                  </Badge>
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Category</div>
                <div className="mt-2">
                  <Badge className={result.threat_category ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'}>
                    {result.threat_category || 'UNCATEGORIZED'}
                  </Badge>
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Reputation</div>
                <div className="mt-2">
                  <Badge className={getReputationColor(result.reputation_score)}>
                    {getReputationLabel(result.reputation_score)}
                    {result.reputation_score && ` (${(result.reputation_score * 100).toFixed(0)}%)`}
                  </Badge>
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
                {result.url && (
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">URL:</span>
                    <span className="ml-2 text-gray-900 dark:text-white font-mono break-all">{result.url}</span>
                  </div>
                )}
              </div>
            </div>

            {/* DNS Response */}
            {result.dns_response && (
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">DNS Resolution</h4>
                <div className="text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-700 dark:text-gray-300">Response:</span>
                    <span className="font-mono text-gray-900 dark:text-white">{result.dns_response}</span>
                  </div>
                  {result.dns_response === 'NXDOMAIN' && (
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      Domain does not exist or is blocked at DNS level
                    </div>
                  )}
                  {['127.0.0.1', '0.0.0.0', '::1'].includes(result.dns_response) && (
                    <div className="mt-2 text-xs text-orange-600 dark:text-orange-400">
                      Response indicates potential RPZ blocking (sinkhole IP)
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* RPZ Rule Match */}
            {result.rpz_rule_matched && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">RPZ Rule Matched</h4>
                <div className="text-sm text-red-700 dark:text-red-300">
                  <div className="font-mono bg-red-100 dark:bg-red-900/40 rounded px-2 py-1">
                    {result.rpz_rule_matched}
                  </div>
                  <div className="mt-2 text-xs">
                    This domain is blocked by your Response Policy Zone configuration
                  </div>
                </div>
              </div>
            )}

            {/* Security Assessment */}
            <div className={`rounded-lg p-4 border ${result.is_blocked 
              ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' 
              : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
            }`}>
              <h4 className={`font-medium mb-2 ${result.is_blocked 
                ? 'text-red-600 dark:text-red-400' 
                : 'text-green-600 dark:text-green-400'
              }`}>
                Security Assessment
              </h4>
              <div className={`text-sm ${result.is_blocked 
                ? 'text-red-700 dark:text-red-300' 
                : 'text-green-700 dark:text-green-300'
              }`}>
                {result.is_blocked ? (
                  <div>
                    <p className="font-medium">⚠️ Threat Detected and Blocked</p>
                    <ul className="mt-2 space-y-1 text-xs">
                      <li>• This domain has been identified as potentially malicious</li>
                      <li>• Your DNS security configuration is working correctly</li>
                      <li>• Users attempting to access this domain will be blocked</li>
                      {result.threat_category && <li>• Category: {result.threat_category}</li>}
                    </ul>
                  </div>
                ) : (
                  <div>
                    <p className="font-medium">✅ No Threats Detected</p>
                    <ul className="mt-2 space-y-1 text-xs">
                      <li>• This domain appears to be safe based on current rules</li>
                      <li>• DNS resolution completed normally</li>
                      <li>• No RPZ blocking rules matched this domain</li>
                      <li>• Users can access this domain normally</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Error Message */}
            {result.error && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <h4 className="font-medium text-yellow-600 dark:text-yellow-400 mb-2">Warning:</h4>
                <div className="text-sm text-yellow-700 dark:text-yellow-300">
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
            Recent Threat Tests
          </h3>
          
          <div className="space-y-2">
            {history.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge className={getThreatLevelColor(item.is_blocked, item.threat_category)}>
                    {item.is_blocked ? 'BLOCKED' : 'SAFE'}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.domain}
                  </span>
                  {item.threat_category && (
                    <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">
                      {item.threat_category}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                  {item.dns_response && (
                    <span className="font-mono">{item.dns_response}</span>
                  )}
                  {item.reputation_score && (
                    <Badge className={getReputationColor(item.reputation_score)}>
                      {getReputationLabel(item.reputation_score)}
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