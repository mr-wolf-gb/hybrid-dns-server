import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { recordsService } from '@/services/api'
import { Zone, DNSRecord } from '@/types'
import { Card, Button, Table, Badge } from '@/components/ui'
import { formatDateTime, formatNumber } from '@/utils'
import { toast } from 'react-toastify'
import RecordModal from './RecordModal'
import BulkRecordActions from './BulkRecordActions'

interface RecordsViewProps {
  zone: Zone
  onBack: () => void
  onCreateRecord: () => void
}

const RecordsView: React.FC<RecordsViewProps> = ({ zone, onBack, onCreateRecord }) => {
  const [selectedRecord, setSelectedRecord] = useState<DNSRecord | null>(null)
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [selectedRecords, setSelectedRecords] = useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  
  const queryClient = useQueryClient()

  // Available record types for filtering
  const recordTypes = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS'] as const

  // Fetch records for the zone
  const { data: records, isLoading } = useQuery({
    queryKey: ['records', zone.id],
    queryFn: () => recordsService.getRecords(zone.id),
  })

  // Filter and search records
  const filteredRecords = useMemo(() => {
    if (!records?.data) return []

    let filtered = records.data

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(record => 
        record.name.toLowerCase().includes(query) ||
        record.value.toLowerCase().includes(query) ||
        record.type.toLowerCase().includes(query) ||
        `${record.name}.${zone.name}`.toLowerCase().includes(query)
      )
    }

    // Apply type filter
    if (selectedTypes.length > 0) {
      filtered = filtered.filter(record => selectedTypes.includes(record.type))
    }

    return filtered
  }, [records?.data, searchQuery, selectedTypes, zone.name])

  // Get available types from current records
  const availableTypes = useMemo(() => {
    if (!records?.data) return []
    const types = [...new Set(records.data.map(r => r.type))].sort()
    return types
  }, [records?.data])

  // Validation function for records
  const validateRecord = (record: DNSRecord): { status: 'valid' | 'warning' | 'error', message?: string } => {
    // Basic validation rules
    if (!record.value.trim()) {
      return { status: 'error', message: 'Empty value' }
    }

    switch (record.type) {
      case 'A':
        const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
        if (!ipv4Regex.test(record.value)) {
          return { status: 'error', message: 'Invalid IPv4 address' }
        }
        break
      case 'AAAA':
        const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$/
        if (!ipv6Regex.test(record.value)) {
          return { status: 'error', message: 'Invalid IPv6 address' }
        }
        break
      case 'CNAME':
        if (record.value === record.name || record.value === `${record.name}.${zone.name}`) {
          return { status: 'error', message: 'CNAME cannot point to itself' }
        }
        break
      case 'MX':
        if (!record.priority || record.priority < 0 || record.priority > 65535) {
          return { status: 'error', message: 'Invalid MX priority' }
        }
        break
      case 'SRV':
        if (!record.priority || !record.weight || !record.port) {
          return { status: 'error', message: 'Missing SRV parameters' }
        }
        if (record.port < 1 || record.port > 65535) {
          return { status: 'error', message: 'Invalid port number' }
        }
        break
    }

    // TTL validation
    if (record.ttl < 60) {
      return { status: 'warning', message: 'TTL below recommended minimum (60s)' }
    }

    if (record.ttl > 86400) {
      return { status: 'warning', message: 'TTL above recommended maximum (24h)' }
    }

    return { status: 'valid' }
  }

  // Delete record mutation
  const deleteRecordMutation = useMutation({
    mutationFn: ({ recordId }: { recordId: number }) =>
      recordsService.deleteRecord(zone.id, recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', zone.id] })
      toast.success('Record deleted successfully')
    },
    onError: () => {
      toast.error('Failed to delete record')
    },
  })

  // Toggle record mutation
  const toggleRecordMutation = useMutation({
    mutationFn: ({ recordId }: { recordId: number }) =>
      recordsService.toggleRecord(zone.id, recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', zone.id] })
      toast.success('Record status updated')
    },
    onError: () => {
      toast.error('Failed to update record status')
    },
  })

  const handleCreateRecord = () => {
    setSelectedRecord(null)
    setIsRecordModalOpen(true)
  }

  const handleEditRecord = (record: DNSRecord) => {
    setSelectedRecord(record)
    setIsRecordModalOpen(true)
  }

  const handleDeleteRecord = async (record: DNSRecord) => {
    if (window.confirm(`Are you sure you want to delete the ${record.type} record "${record.name}"?`)) {
      deleteRecordMutation.mutate({ recordId: record.id })
    }
  }

  const handleToggleRecord = (record: DNSRecord) => {
    toggleRecordMutation.mutate({ recordId: record.id })
  }

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['records', zone.id] })
  }

  const handleTypeFilter = (type: string) => {
    setSelectedTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    )
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedTypes([])
  }

  const hasActiveFilters = searchQuery.trim() || selectedTypes.length > 0

  // Selection handlers
  const handleSelectRecord = (recordId: number) => {
    setSelectedRecords(prev => {
      const newSet = new Set(prev)
      if (newSet.has(recordId)) {
        newSet.delete(recordId)
      } else {
        newSet.add(recordId)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedRecords(new Set())
      setSelectAll(false)
    } else {
      setSelectedRecords(new Set(filteredRecords.map(r => r.id)))
      setSelectAll(true)
    }
  }

  const handleClearSelection = () => {
    setSelectedRecords(new Set())
    setSelectAll(false)
  }

  const getSelectedRecordObjects = (): DNSRecord[] => {
    return filteredRecords.filter(record => selectedRecords.has(record.id))
  }

  // Update selectAll state when filtered records change
  React.useEffect(() => {
    if (filteredRecords.length === 0) {
      setSelectAll(false)
    } else {
      const allSelected = filteredRecords.every(record => selectedRecords.has(record.id))
      setSelectAll(allSelected)
    }
  }, [filteredRecords, selectedRecords])

  const formatRecordValue = (record: DNSRecord): string => {
    switch (record.type) {
      case 'MX':
        return `${record.priority} ${record.value}`
      case 'SRV':
        return `${record.priority} ${record.weight} ${record.port} ${record.value}`
      default:
        return record.value
    }
  }

  const getRecordTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      'A': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'AAAA': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
      'CNAME': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'MX': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'TXT': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      'SRV': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
      'PTR': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      'NS': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    }
    return colors[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }

  const getValidationIcon = (validation: { status: 'valid' | 'warning' | 'error', message?: string }) => {
    switch (validation.status) {
      case 'valid':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" title="Valid record" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500" title={validation.message} />
      case 'error':
        return <XCircleIcon className="h-4 w-4 text-red-500" title={validation.message} />
    }
  }

  const columns = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={selectAll}
          onChange={handleSelectAll}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
      render: (record: DNSRecord) => (
        <input
          type="checkbox"
          checked={selectedRecords.has(record.id)}
          onChange={() => handleSelectRecord(record.id)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
    },
    {
      key: 'validation',
      header: '',
      render: (record: DNSRecord) => {
        const validation = validateRecord(record)
        return (
          <div className="flex items-center justify-center">
            {getValidationIcon(validation)}
          </div>
        )
      },
    },
    {
      key: 'name',
      header: 'Name',
      render: (record: DNSRecord) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {record.name || '@'}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {record.name ? `${record.name}.${zone.name}` : zone.name}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (record: DNSRecord) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRecordTypeColor(record.type)}`}>
          {record.type}
        </span>
      ),
    },
    {
      key: 'value',
      header: 'Value',
      render: (record: DNSRecord) => (
        <div className="max-w-xs">
          <span className="font-mono text-sm break-all">
            {formatRecordValue(record)}
          </span>
          {(record.type === 'MX' || record.type === 'SRV') && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {record.type === 'MX' && `Priority: ${record.priority}`}
              {record.type === 'SRV' && `Priority: ${record.priority}, Weight: ${record.weight}, Port: ${record.port}`}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'ttl',
      header: 'TTL',
      render: (record: DNSRecord) => {
        const validation = validateRecord(record)
        const isWarning = validation.status === 'warning' && validation.message?.includes('TTL')
        return (
          <span className={`font-mono text-sm ${isWarning ? 'text-yellow-600 dark:text-yellow-400' : ''}`}>
            {formatNumber(record.ttl)}s
          </span>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (record: DNSRecord) => (
        <Badge variant={record.is_active ? 'success' : 'default'}>
          {record.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'updated_at',
      header: 'Last Updated',
      render: (record: DNSRecord) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatDateTime(record.updated_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (record: DNSRecord) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditRecord(record)}
            title="Edit record"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleToggleRecord(record)}
            title={record.is_active ? 'Deactivate' : 'Activate'}
            loading={toggleRecordMutation.isPending}
          >
            {record.is_active ? (
              <PauseIcon className="h-4 w-4" />
            ) : (
              <PlayIcon className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteRecord(record)}
            title="Delete record"
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Navigation header */}
      <div className="flex items-center space-x-4">
        <Button
          variant="outline"
          onClick={onBack}
          className="flex items-center"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-2" />
          Back to Zones
        </Button>
        
        <div className="border-l border-gray-300 dark:border-gray-600 pl-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            DNS Records: {zone.name}
          </h1>
          <div className="flex items-center space-x-4 mt-1">
            <Badge variant={zone.type === 'master' ? 'success' : 'info'}>
              {zone.type}
            </Badge>
            <Badge variant={zone.is_active ? 'success' : 'default'}>
              {zone.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Serial: {formatNumber(zone.serial)}
            </span>
          </div>
        </div>
      </div>

      {/* Bulk actions */}
      {selectedRecords.size > 0 && (
        <BulkRecordActions
          zoneId={zone.id}
          selectedRecords={getSelectedRecordObjects()}
          onClearSelection={handleClearSelection}
          onRefresh={handleRefresh}
        />
      )}

      {/* Search and filters */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1 max-w-2xl">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search records by name, value, or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center"
            >
              <FunnelIcon className="h-4 w-4 mr-2" />
              Filters
              {selectedTypes.length > 0 && (
                <Badge variant="info" className="ml-2">
                  {selectedTypes.length}
                </Badge>
              )}
            </Button>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                onClick={clearFilters}
                className="flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <XMarkIcon className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>

          <Button onClick={handleCreateRecord}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Record
          </Button>
        </div>

        {/* Type filters */}
        {showFilters && (
          <Card className="p-4">
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">Filter by Record Type</h3>
              <div className="flex flex-wrap gap-2">
                {availableTypes.map(type => (
                  <button
                    key={type}
                    onClick={() => handleTypeFilter(type)}
                    className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      selectedTypes.includes(type)
                        ? `${getRecordTypeColor(type)} ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-gray-800`
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {type}
                    <span className="ml-2 text-xs">
                      {records?.data?.filter(r => r.type === type).length || 0}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {hasActiveFilters ? filteredRecords.length : (records?.data?.length || 0)}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {hasActiveFilters ? 'Filtered' : 'Total'} Records
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {hasActiveFilters 
              ? filteredRecords.filter(r => r.is_active).length 
              : (records?.data?.filter(r => r.is_active).length || 0)
            }
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Active Records
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {hasActiveFilters 
              ? new Set(filteredRecords.map(r => r.type)).size
              : new Set(records?.data?.map(r => r.type) || []).size
            }
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Record Types
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {hasActiveFilters 
              ? filteredRecords.filter(r => validateRecord(r).status === 'error').length
              : (records?.data?.filter(r => validateRecord(r).status === 'error').length || 0)
            }
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Invalid Records
          </div>
        </div>
      </div>

      {/* Records table */}
      <Card>
        {hasActiveFilters && (
          <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Showing {filteredRecords.length} of {records?.data?.length || 0} records
                {searchQuery && (
                  <span className="ml-2">
                    matching "<span className="font-medium">{searchQuery}</span>"
                  </span>
                )}
                {selectedTypes.length > 0 && (
                  <span className="ml-2">
                    with types: {selectedTypes.join(', ')}
                  </span>
                )}
              </div>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  Clear filters
                </Button>
              )}
            </div>
          </div>
        )}
        <Table
          data={filteredRecords}
          columns={columns}
          loading={isLoading}
          emptyMessage={
            hasActiveFilters 
              ? "No records match your current filters. Try adjusting your search or clearing filters."
              : `No DNS records found for ${zone.name}. Create your first record to get started.`
          }
        />
      </Card>

      {/* Record modal */}
      {isRecordModalOpen && (
        <RecordModal
          zoneId={zone.id}
          record={selectedRecord}
          isOpen={isRecordModalOpen}
          onClose={() => setIsRecordModalOpen(false)}
          onSuccess={() => {
            setIsRecordModalOpen(false)
            queryClient.invalidateQueries({ 
              queryKey: ['records', zone.id] 
            })
          }}
        />
      )}
    </div>
  )
}

export default RecordsView