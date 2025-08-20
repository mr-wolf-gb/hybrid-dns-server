import React from 'react'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { DNSRecord, Zone } from '@/types'
import { Button, Badge, Table } from '@/components/ui'
import { formatDateTime, formatNumber } from '@/utils'

interface RecordListProps {
  records: DNSRecord[]
  zone: Zone
  selectedRecords: Set<number>
  selectAll: boolean
  loading?: boolean
  onSelectRecord: (recordId: number) => void
  onSelectAll: () => void
  onEditRecord: (record: DNSRecord) => void
  onDeleteRecord: (record: DNSRecord) => void
  onToggleRecord: (record: DNSRecord) => void
  emptyMessage?: string
}

const RecordList: React.FC<RecordListProps> = ({
  records,
  zone,
  selectedRecords,
  selectAll,
  loading = false,
  onSelectRecord,
  onSelectAll,
  onEditRecord,
  onDeleteRecord,
  onToggleRecord,
  emptyMessage,
}) => {
  // Enhanced validation function for records
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
          onChange={onSelectAll}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
      render: (record: DNSRecord) => (
        <input
          type="checkbox"
          checked={selectedRecords.has(record.id)}
          onChange={() => onSelectRecord(record.id)}
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
            onClick={() => onEditRecord(record)}
            title="Edit record"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onToggleRecord(record)}
            title={record.is_active ? 'Deactivate' : 'Activate'}
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
            onClick={() => onDeleteRecord(record)}
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
    <Table
      data={records}
      columns={columns}
      loading={loading}
      emptyMessage={emptyMessage}
    />
  )
}

export default RecordList