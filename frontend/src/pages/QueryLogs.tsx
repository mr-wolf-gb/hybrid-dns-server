import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline'
import { dashboardService } from '@/services/api'
import { DNSLog } from '@/types'
import { Card, Button, Table, Badge, Input } from '@/components/ui'
import { formatDateTime, formatRelativeTime, getCategoryColor, debounce } from '@/utils'

const QueryLogs: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterBlocked, setFilterBlocked] = useState<boolean | null>(null)
  const perPage = 50

  // Debounce search to avoid too many API calls
  const debouncedSearch = debounce((search: string) => {
    setCurrentPage(1) // Reset to first page on new search
  }, 500)

  React.useEffect(() => {
    debouncedSearch(searchTerm)
  }, [searchTerm])

  // Fetch query logs
  const { data: logsResponse, isLoading } = useQuery({
    queryKey: ['query-logs', currentPage, searchTerm],
    queryFn: () => dashboardService.getQueryLogs(currentPage, perPage, searchTerm),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const logs = logsResponse?.data?.items || []
  const totalPages = logsResponse?.data?.pages || 1

  const handleSearchChange = (value: string) => {
    setSearchTerm(value)
  }

  const toggleBlockedFilter = () => {
    if (filterBlocked === null) {
      setFilterBlocked(true)
    } else if (filterBlocked === true) {
      setFilterBlocked(false)
    } else {
      setFilterBlocked(null)
    }
    setCurrentPage(1)
  }

  const getFilteredLogs = () => {
    if (filterBlocked === null) return logs
    return logs.filter(log => log.is_blocked === filterBlocked)
  }

  const filteredLogs = getFilteredLogs()

  const columns = [
    {
      key: 'timestamp',
      header: 'Time',
      render: (log: DNSLog) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {formatRelativeTime(log.timestamp)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {formatDateTime(log.timestamp)}
          </div>
        </div>
      ),
    },
    {
      key: 'client_ip',
      header: 'Client IP',
      render: (log: DNSLog) => (
        <span className="font-mono text-sm text-gray-900 dark:text-gray-100">
          {log.client_ip}
        </span>
      ),
    },
    {
      key: 'query_domain',
      header: 'Domain',
      render: (log: DNSLog) => (
        <div className="max-w-xs">
          <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
            {log.query_domain}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {log.query_type} record
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (log: DNSLog) => (
        <div className="flex items-center space-x-2">
          {log.is_blocked ? (
            <>
              <Badge variant="danger">Blocked</Badge>
              {log.blocked_category && (
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(log.blocked_category)}`}>
                  {log.blocked_category.replace('_', ' ')}
                </span>
              )}
            </>
          ) : (
            <Badge variant="success">Allowed</Badge>
          )}
        </div>
      ),
    },
    {
      key: 'response_code',
      header: 'Response',
      render: (log: DNSLog) => (
        <span className="font-mono text-sm text-gray-600 dark:text-gray-400">
          {log.response_code}
        </span>
      ),
    },
  ]

  const blockedCount = logs.filter(log => log.is_blocked).length
  const allowedCount = logs.length - blockedCount
  const topDomains = logs
    .reduce((acc, log) => {
      acc[log.query_domain] = (acc[log.query_domain] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  const topClients = logs
    .reduce((acc, log) => {
      acc[log.client_ip] = (acc[log.client_ip] || 0) + 1
      return acc
    }, {} as Record<string, number>)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          DNS Query Logs
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Monitor DNS queries in real-time
        </p>
      </div>

      {/* Stats and filters */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Stats cards */}
        <div className="lg:col-span-3">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                    <span className="text-blue-600 dark:text-blue-400 font-semibold">
                      {logs.length}
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Total Queries
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                    <span className="text-red-600 dark:text-red-400 font-semibold">
                      {blockedCount}
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Blocked
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                    <span className="text-green-600 dark:text-green-400 font-semibold">
                      {allowedCount}
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Allowed
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Search and filter */}
        <div className="space-y-4">
          <Input
            placeholder="Search domains or IPs..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="h-5 w-5" />}
          />
          
          <Button
            variant="outline"
            onClick={toggleBlockedFilter}
            className="w-full"
          >
            <FunnelIcon className="h-4 w-4 mr-2" />
            {filterBlocked === null 
              ? 'All Queries' 
              : filterBlocked 
                ? 'Blocked Only' 
                : 'Allowed Only'
            }
          </Button>
        </div>
      </div>

      {/* Analytics */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card 
          title="Top Queried Domains" 
          description="Most frequently requested domains"
        >
          <div className="space-y-3">
            {Object.entries(topDomains)
              .sort(([,a], [,b]) => b - a)
              .slice(0, 8)
              .map(([domain, count]) => (
                <div key={domain} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {domain}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </Card>

        <Card 
          title="Top Client IPs" 
          description="Most active DNS clients"
        >
          <div className="space-y-3">
            {Object.entries(topClients)
              .sort(([,a], [,b]) => b - a)
              .slice(0, 8)
              .map(([ip, count]) => (
                <div key={ip} className="flex items-center justify-between">
                  <span className="text-sm font-mono text-gray-900 dark:text-gray-100">
                    {ip}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </Card>
      </div>

      {/* Query logs table */}
      <Card>
        <Table
          data={filteredLogs}
          columns={columns}
          loading={isLoading}
          emptyMessage="No query logs found. DNS queries will appear here as they are processed."
        />
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default QueryLogs