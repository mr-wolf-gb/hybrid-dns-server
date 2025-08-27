import React, { useState, useEffect } from 'react'
import { InformationCircleIcon, ServerIcon, GlobeAltIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { Card, Button, Badge, Loading } from '@/components/ui'
import { api } from '@/services/api'
import { toast } from 'react-toastify'

interface NetworkInterface {
  type: string
  address: string
  netmask: string
}

interface NetworkInfo {
  system_dns?: string
  system_dns_servers?: string[]
  network_interfaces?: Record<string, NetworkInterface[]>
  dns_error?: string
  interface_error?: string
}

interface NetworkInfoResponse {
  success: boolean
  network_info?: NetworkInfo
  error?: string
}

export const NetworkInfoTool: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchNetworkInfo = async () => {
    setIsLoading(true)
    try {
      const response = await api.get<NetworkInfoResponse>('/diagnostics/network-info')

      if (response.data.success && response.data.network_info) {
        setNetworkInfo(response.data.network_info)
        setLastUpdated(new Date())
        toast.success('Network information updated')
      } else {
        toast.error(`Failed to get network info: ${response.data.error}`)
      }
    } catch (error) {
      toast.error('Failed to fetch network information')
      console.error('Network info error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchNetworkInfo()
  }, [])

  const getInterfaceTypeColor = (type: string) => {
    switch (type) {
      case 'IPv4':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'IPv6':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  const isPrivateIP = (ip: string) => {
    const privateRanges = [
      /^10\./,
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
      /^192\.168\./,
      /^127\./,
      /^169\.254\./
    ]
    return privateRanges.some(range => range.test(ip))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <InformationCircleIcon className="h-5 w-5 mr-2" />
            Network Configuration Information
          </h3>
          <div className="flex items-center space-x-3">
            {lastUpdated && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={fetchNetworkInfo}
              disabled={isLoading}
            >
              {isLoading ? <Loading size="sm" /> : <ArrowPathIcon className="h-4 w-4" />}
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {networkInfo && (
        <>
          {/* DNS Configuration */}
          <Card className="p-6">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
              <GlobeAltIcon className="h-5 w-5 mr-2" />
              DNS Configuration
            </h4>

            <div className="space-y-4">
              {networkInfo.system_dns && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Primary DNS Server
                    </span>
                    <span className="font-mono text-gray-900 dark:text-white">
                      {networkInfo.system_dns}
                    </span>
                  </div>
                </div>
              )}

              {networkInfo.system_dns_servers && networkInfo.system_dns_servers.length > 0 && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Configured DNS Servers
                  </h5>
                  <div className="space-y-2">
                    {networkInfo.system_dns_servers.map((dns, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          DNS Server {index + 1}
                        </span>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-gray-900 dark:text-white">
                            {dns}
                          </span>
                          <Badge className={isPrivateIP(dns) ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}>
                            {isPrivateIP(dns) ? 'Private' : 'Public'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {networkInfo.dns_error && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                  <div className="text-sm text-yellow-700 dark:text-yellow-300">
                    <strong>DNS Configuration Error:</strong> {networkInfo.dns_error}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Network Interfaces */}
          {networkInfo.network_interfaces && (
            <Card className="p-6">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                <ServerIcon className="h-5 w-5 mr-2" />
                Network Interfaces
              </h4>

              <div className="space-y-4">
                {Object.entries(networkInfo.network_interfaces).map(([interfaceName, addresses]) => (
                  <div key={interfaceName} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-medium text-gray-900 dark:text-white">
                        {interfaceName}
                      </h5>
                      <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {addresses.length} address{addresses.length !== 1 ? 'es' : ''}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      {addresses.map((addr, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-white dark:bg-gray-700 rounded border">
                          <div className="flex items-center space-x-3">
                            <Badge className={getInterfaceTypeColor(addr.type)}>
                              {addr.type}
                            </Badge>
                            <span className="font-mono text-sm text-gray-900 dark:text-white">
                              {addr.address}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            {addr.netmask && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                Mask: {addr.netmask}
                              </span>
                            )}
                            {addr.type === 'IPv4' && (
                              <Badge className={isPrivateIP(addr.address) ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}>
                                {isPrivateIP(addr.address) ? 'Private' : 'Public'}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {networkInfo.interface_error && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mt-4">
                  <div className="text-sm text-yellow-700 dark:text-yellow-300">
                    <strong>Interface Error:</strong> {networkInfo.interface_error}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* Network Summary */}
          <Card className="p-6">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Network Summary
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Total Interfaces
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {networkInfo.network_interfaces ? Object.keys(networkInfo.network_interfaces).length : 0}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  IPv4 Addresses
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {networkInfo.network_interfaces
                    ? Object.values(networkInfo.network_interfaces)
                      .flat()
                      .filter(addr => addr.type === 'IPv4').length
                    : 0
                  }
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  IPv6 Addresses
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {networkInfo.network_interfaces
                    ? Object.values(networkInfo.network_interfaces)
                      .flat()
                      .filter(addr => addr.type === 'IPv6').length
                    : 0
                  }
                </div>
              </div>
            </div>
          </Card>

          {/* Diagnostic Tips */}
          <Card className="p-6">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Network Diagnostic Tips
            </h4>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                <p className="font-medium">Understanding Your Network Configuration:</p>
                <ul className="space-y-1 text-xs ml-4">
                  <li>• <strong>Private IP addresses</strong> (10.x.x.x, 192.168.x.x, 172.16-31.x.x) are used for internal networks</li>
                  <li>• <strong>Public IP addresses</strong> are routable on the internet</li>
                  <li>• <strong>DNS servers</strong> should be reachable and properly configured</li>
                  <li>• <strong>Multiple interfaces</strong> may indicate complex network setups or virtualization</li>
                  <li>• <strong>IPv6 addresses</strong> provide modern networking capabilities</li>
                </ul>
              </div>
            </div>
          </Card>
        </>
      )}

      {!networkInfo && !isLoading && (
        <Card className="p-6">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <InformationCircleIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No network information available. Click refresh to load data.</p>
          </div>
        </Card>
      )}
    </div>
  )
}