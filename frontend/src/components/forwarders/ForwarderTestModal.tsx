import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import {
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { forwardersService } from '@/services/api'
import { Forwarder } from '@/types'
import { Modal, Button, Input, Select, Card } from '@/components/ui'
import { toast } from 'react-toastify'

interface ForwarderTestModalProps {
  forwarder: Forwarder
  isOpen: boolean
  onClose: () => void
}

interface TestFormData {
  domain: string
  record_type: string
  timeout: number
}

interface TestResult {
  success: boolean
  response_time: number
  resolved_ips?: string[]
  error?: string
  server_responses: Array<{
    server: string
    success: boolean
    response_time: number
    resolved_ips?: string[]
    error?: string
  }>
}

const ForwarderTestModal: React.FC<ForwarderTestModalProps> = ({
  forwarder,
  isOpen,
  onClose,
}) => {
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isTestRunning, setIsTestRunning] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TestFormData>({
    defaultValues: {
      domain: forwarder.type === 'ad' ? 'corp.local' : 'google.com',
      record_type: 'A',
      timeout: 5,
    },
  })

  const testMutation = useMutation({
    mutationFn: async (_data: TestFormData) => {
      setIsTestRunning(true)
      setTestResult(null)
      
      // Simulate API call - replace with actual API endpoint
      await forwardersService.testForwarder(forwarder.id)
      
      // Mock detailed test result for demonstration
      const mockResult: TestResult = {
        success: Math.random() > 0.2,
        response_time: Math.floor(Math.random() * 200) + 10,
        resolved_ips: ['192.168.1.100', '192.168.1.101'],
        server_responses: forwarder.servers.map(server => ({
          server,
          success: Math.random() > 0.1,
          response_time: Math.floor(Math.random() * 150) + 5,
          resolved_ips: Math.random() > 0.5 ? ['192.168.1.100'] : undefined,
          error: Math.random() > 0.8 ? 'Connection timeout' : undefined,
        })),
      }
      
      return mockResult
    },
    onSuccess: (result) => {
      setTestResult(result)
      setIsTestRunning(false)
      if (result.success) {
        toast.success(`Test completed successfully in ${result.response_time}ms`)
      } else {
        toast.error('Test failed - check individual server results')
      }
    },
    onError: (error: any) => {
      setIsTestRunning(false)
      toast.error(error.response?.data?.detail || 'Test failed')
    },
  })

  const onSubmit = (data: TestFormData) => {
    testMutation.mutate(data)
  }

  const getResultIcon = (success: boolean) => {
    if (success) {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />
    }
    return <XCircleIcon className="h-5 w-5 text-red-500" />
  }

  const getResponseTimeColor = (responseTime: number) => {
    if (responseTime < 50) return 'text-green-600'
    if (responseTime < 200) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Test Forwarder: ${forwarder.name}`}
      size="xl"
    >
      <div className="space-y-6">
        {/* Test Configuration */}
        <Card className="p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
            Test Configuration
          </h3>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Input
                label="Domain to Test"
                placeholder="example.com"
                {...register('domain', {
                  required: 'Domain is required',
                })}
                error={errors.domain?.message}
              />
              
              <Select
                label="Record Type"
                options={[
                  { value: 'A', label: 'A (IPv4)' },
                  { value: 'AAAA', label: 'AAAA (IPv6)' },
                  { value: 'MX', label: 'MX (Mail)' },
                  { value: 'TXT', label: 'TXT (Text)' },
                  { value: 'CNAME', label: 'CNAME (Alias)' },
                  { value: 'NS', label: 'NS (Name Server)' },
                ]}
                {...register('record_type')}
              />
              
              <Input
                label="Timeout (seconds)"
                type="number"
                min="1"
                max="30"
                {...register('timeout', {
                  required: 'Timeout is required',
                  min: { value: 1, message: 'Minimum timeout is 1 second' },
                  max: { value: 30, message: 'Maximum timeout is 30 seconds' },
                })}
                error={errors.timeout?.message}
              />
            </div>
            
            <div className="flex justify-end">
              <Button
                type="submit"
                loading={isTestRunning}
                disabled={isTestRunning}
              >
                {isTestRunning ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <PlayIcon className="h-4 w-4 mr-2" />
                    Run Test
                  </>
                )}
              </Button>
            </div>
          </form>
        </Card>

        {/* Test Results */}
        {testResult && (
          <Card className="p-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              Test Results
            </h3>
            
            {/* Overall Result */}
            <div className="mb-6 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getResultIcon(testResult.success)}
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {testResult.success ? 'Test Successful' : 'Test Failed'}
                    </div>
                    <div className={`text-sm font-mono ${getResponseTimeColor(testResult.response_time)}`}>
                      Response Time: {testResult.response_time}ms
                    </div>
                  </div>
                </div>
                
                {testResult.resolved_ips && testResult.resolved_ips.length > 0 && (
                  <div className="text-right">
                    <div className="text-sm text-gray-500 dark:text-gray-400">Resolved IPs:</div>
                    <div className="font-mono text-sm text-gray-900 dark:text-gray-100">
                      {testResult.resolved_ips.join(', ')}
                    </div>
                  </div>
                )}
              </div>
              
              {testResult.error && (
                <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                  Error: {testResult.error}
                </div>
              )}
            </div>
            
            {/* Individual Server Results */}
            <div className="space-y-3">
              <h4 className="font-medium text-gray-900 dark:text-gray-100">
                Individual Server Results
              </h4>
              
              {testResult.server_responses.map((serverResult, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center space-x-3">
                    {getResultIcon(serverResult.success)}
                    <div>
                      <div className="font-mono text-sm text-gray-900 dark:text-gray-100">
                        {serverResult.server}
                      </div>
                      {serverResult.error && (
                        <div className="text-xs text-red-600 dark:text-red-400">
                          {serverResult.error}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className={`text-sm font-mono ${getResponseTimeColor(serverResult.response_time)}`}>
                      {serverResult.response_time}ms
                    </div>
                    {serverResult.resolved_ips && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {serverResult.resolved_ips.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Forwarder Info */}
        <Card className="p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
            Forwarder Information
          </h3>
          
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Domain</div>
              <div className="font-mono text-gray-900 dark:text-gray-100">{forwarder.domain}</div>
            </div>
            
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Type</div>
              <div className="text-gray-900 dark:text-gray-100">
                {forwarder.type === 'ad' ? 'Active Directory' : 
                 forwarder.type === 'intranet' ? 'Intranet' : 'Public DNS'}
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Policy</div>
              <div className="text-gray-900 dark:text-gray-100">{forwarder.forward_policy}</div>
            </div>
            
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Servers</div>
              <div className="font-mono text-sm text-gray-900 dark:text-gray-100">
                {forwarder.servers.join(', ')}
              </div>
            </div>
          </div>
        </Card>

        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ForwarderTestModal