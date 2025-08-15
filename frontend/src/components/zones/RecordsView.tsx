import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { recordsService } from '@/services/api'
import { Zone, DNSRecord } from '@/types'
import { Card, Button, Table, Badge } from '@/components/ui'
import { formatDateTime, formatNumber } from '@/utils'
import { toast } from 'react-toastify'
import RecordModal from './RecordModal'

interface RecordsViewProps {
  zone: Zone
  onBack: () => void
  onCreateRecord: () => void
}

const RecordsView: React.FC<RecordsViewProps> = ({ zone, onBack, onCreateRecord }) => {
  const [selectedRecord, setSelectedRecord] = useState<DNSRecord | null>(null)
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false)
  
  const queryClient = useQueryClient()

  // Fetch records for the zone
  const { data: records, isLoading } = useQuery({
    queryKey: ['records', zone.id],
    queryFn: () => recordsService.getRecords(zone.id),
  })

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

  const columns = [
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
        <Badge variant="info">
          {record.type}
        </Badge>
      ),
    },
    {
      key: 'value',
      header: 'Value',
      render: (record: DNSRecord) => (
        <span className="font-mono text-sm break-all">
          {formatRecordValue(record)}
        </span>
      ),
    },
    {
      key: 'ttl',
      header: 'TTL',
      render: (record: DNSRecord) => (
        <span className="font-mono text-sm">
          {formatNumber(record.ttl)}s
        </span>
      ),
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

      {/* Stats and actions */}
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {records?.data?.length || 0}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Total Records
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {records?.data?.filter(r => r.is_active).length || 0}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Active Records
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {new Set(records?.data?.map(r => r.type) || []).size}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Record Types
            </div>
          </div>
        </div>

        <Button onClick={handleCreateRecord}>
          <PlusIcon className="h-4 w-4 mr-2" />
          Add Record
        </Button>
      </div>

      {/* Records table */}
      <Card>
        <Table
          data={records?.data || []}
          columns={columns}
          loading={isLoading}
          emptyMessage={`No DNS records found for ${zone.name}. Create your first record to get started.`}
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