import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { recordsService } from '@/services/api'
import { Zone, DNSRecord } from '@/types'
import { Card, Button, Badge } from '@/components/ui'
import { formatNumber } from '@/utils'
import { toast } from 'react-toastify'
import RecordModal from './RecordModal'
import RecordList from './RecordList'
import RecordTypeFilter from './RecordTypeFilter'
import BulkRecordActions from './BulkRecordActions'

interface RecordsViewProps {
  zone: Zone
  onBack: () => void
}

const RecordsView: React.FC<RecordsViewProps> = ({ zone, onBack }) => {
  const [selectedRecord, setSelectedRecord] = useState<DNSRecord | null>(null)
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [selectedRecords, setSelectedRecords] = useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  
  const queryClient = useQueryClient()

  // Available record types for filtering (moved to RecordTypeFilter component)

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

  // Available types moved to RecordTypeFilter component

  // Validation function for records (moved to RecordList component)
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

  // Helper functions moved to RecordList component

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
            <Badge variant={zone.zone_type === 'master' ? 'success' : 'info'}>
              {zone.zone_type}
            </Badge>
            <Badge variant={zone.is_active ? 'success' : 'default'}>
              {zone.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Serial: {formatNumber(zone.serial || 0)}
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
            
            <RecordTypeFilter
              records={records?.data || []}
              selectedTypes={selectedTypes}
              onTypeToggle={handleTypeFilter}
              onClearFilters={clearFilters}
              showFilters={showFilters}
              onToggleFilters={() => setShowFilters(!showFilters)}
            />

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
        <RecordList
          records={filteredRecords}
          zone={zone}
          selectedRecords={selectedRecords}
          selectAll={selectAll}
          loading={isLoading}
          onSelectRecord={handleSelectRecord}
          onSelectAll={handleSelectAll}
          onEditRecord={handleEditRecord}
          onDeleteRecord={handleDeleteRecord}
          onToggleRecord={handleToggleRecord}
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