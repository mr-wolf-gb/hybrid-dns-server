import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ServerIcon, ClockIcon, SignalIcon } from '@heroicons/react/24/outline'
import { Card, Button, Input, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface PingForm {
  target: string
  count: number
  timeout: number
}

interface PingResult {
  target: string
  success: boolean
  packets_sent: number
  packets_received: number
  packet_loss: number
  min_time?: number
  max_time?: number
  avg_time?: number
  error?: string
  raw_output: string
}

export const PingTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<PingResult | null>(null)
  const [history, setHistory] = useState<PingResult[]>([])

  const { register, handleSubmit, formState: { errors }, reset } = useForm<PingForm>({
    defaultValues: {
      count: 4,
      timeout: 5
    }
  })

  const onSubmit = async (data: PingForm) => {
    setIsLoading(true)
    try {
      const response = await api.post<PingResult>('/diagnostics/ping', data)

      setResult(response.data)
      setHistory(prev => [response.data, ...prev.slice(0, 9)]) // Keep last 10 results
      
      if (response.data.success) {
        toast.success(`Ping completed - ${response.data.packet_loss}% packet loss`)
      } else {
        toast.warning(`Ping failed: ${response.data.error}`)
      }
    } catch (error) {
      toast.error('Failed to perform ping test')
      console.error('Ping error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getPacketLossColor = (loss: number) => {
    if (loss === 0) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    if (loss < 25) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  }

  const formatTime = (time?: number) => {
    if (time === undefined || time === null) return 'N/A'
    return `${time.toFixed(1)}ms`
  }

  return (
    <div className="space-y-6">
      {/* Ping Form */}
      <Card className="p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
          <ServerIcon className="h-5 w-5 mr-2" />
          Ping Test Configuration
        </h3>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Target Host *
              </label>
              <Input
                {...register('target', { 
                  required: 'Target is required',
                  pattern: {
                    value: /^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$/,
                    message: 'Invalid hostname or IP address'
                  }
                })}
                placeholder="google.com or 8.8.8.8"
                error={errors.target?.message}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Packet Count
              </label>
              <Input
                type="number"
                {...register('count', { 
                  min: { value: 1, message: 'Minimum count is 1' },
                  max: { value: 20, message: 'Maximum count is 20' }
                })}
                min="1"
                max="20"
                error={errors.count?.message}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
              {isLoading ? <Loading size="sm" /> : 'Start Ping Test'}
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
            Ping Results
          </h3>
          
          <div className="space-y-4">
            {/* Status and Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</div>
                <Badge className={result.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                  {result.success ? 'SUCCESS' : 'FAILED'}
                </Badge>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Packets</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {result.packets_received}/{result.packets_sent}
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Packet Loss</div>
                <Badge className={getPacketLossColor(result.packet_loss)}>
                  {result.packet_loss.toFixed(1)}%
                </Badge>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Avg Time</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  {formatTime(result.avg_time)}
                </div>
              </div>
            </div>

            {/* Detailed Statistics */}
            {result.success && result.min_time !== undefined && (
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">Response Time Statistics</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Minimum:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{formatTime(result.min_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Average:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{formatTime(result.avg_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Maximum:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{formatTime(result.max_time)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {result.error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">Error:</h4>
                <div className="text-sm text-red-700 dark:text-red-300">
                  {result.error}
                </div>
              </div>
            )}

            {/* Raw Output */}
            {result.raw_output && (
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Raw Output:</h4>
                <div className="bg-gray-900 dark:bg-gray-800 rounded-lg p-4 font-mono text-sm text-green-400 dark:text-green-300 max-h-64 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{result.raw_output}</pre>
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
            Recent Ping Tests
          </h3>
          
          <div className="space-y-2">
            {history.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge className={item.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}>
                    {item.success ? 'OK' : 'FAIL'}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.target}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {item.packets_received}/{item.packets_sent} packets
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-sm text-gray-500 dark:text-gray-400">
                  <Badge className={getPacketLossColor(item.packet_loss)}>
                    {item.packet_loss.toFixed(1)}% loss
                  </Badge>
                  {item.avg_time && (
                    <span>{formatTime(item.avg_time)} avg</span>
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