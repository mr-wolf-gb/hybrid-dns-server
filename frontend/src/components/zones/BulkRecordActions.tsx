import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  TrashIcon,
  PencilIcon,
  DocumentArrowDownIcon,
  DocumentArrowUpIcon,
  CheckIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { DNSRecord, RecordFormData } from '@/types'
import { Button, Modal, Input, Select, Card } from '@/components/ui'
import { recordsService } from '@/services/api'
import { toast } from 'react-toastify'

interface BulkRecordActionsProps {
  zoneId: number
  selectedRecords: DNSRecord[]
  onClearSelection: () => void
  onRefresh: () => void
}

interface BulkEditData {
  ttl?: number
  is_active?: boolean
}

const BulkRecordActions: React.FC<BulkRecordActionsProps> = ({
  zoneId,
  selectedRecords,
  onClearSelection,
  onRefresh,
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [bulkEditData, setBulkEditData] = useState<BulkEditData>({})
  const [importData, setImportData] = useState('')
  const [importFormat, setImportFormat] = useState<'zone' | 'csv' | 'json'>('zone')

  const queryClient = useQueryClient()

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: async () => {
      const recordIds = selectedRecords.map(record => record.id)
      await recordsService.bulkDeleteRecords(zoneId, recordIds)
    },
    onSuccess: () => {
      toast.success(`Successfully deleted ${selectedRecords.length} records`)
      onRefresh()
      onClearSelection()
      setShowDeleteModal(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete records')
    },
  })

  // Bulk edit mutation
  const bulkEditMutation = useMutation({
    mutationFn: async (data: BulkEditData) => {
      const recordIds = selectedRecords.map(record => record.id)
      const updateData: Partial<RecordFormData> = {}
      if (data.ttl !== undefined) updateData.ttl = data.ttl
      await recordsService.bulkUpdateRecords(zoneId, recordIds, updateData)
    },
    onSuccess: () => {
      toast.success(`Successfully updated ${selectedRecords.length} records`)
      onRefresh()
      onClearSelection()
      setShowEditModal(false)
      setBulkEditData({})
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update records')
    },
  })

  // Bulk toggle mutation
  const bulkToggleMutation = useMutation({
    mutationFn: async (activate: boolean) => {
      const recordIds = selectedRecords
        .filter(record => record.is_active !== activate)
        .map(record => record.id)
      if (recordIds.length > 0) {
        await recordsService.bulkToggleRecords(zoneId, recordIds, activate)
      }
    },
    onSuccess: (_, activate) => {
      toast.success(`Successfully ${activate ? 'activated' : 'deactivated'} records`)
      onRefresh()
      onClearSelection()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update record status')
    },
  })

  // Import records mutation
  const importMutation = useMutation({
    mutationFn: async (data: { records: RecordFormData[] }) => {
      await recordsService.importRecords(zoneId, data)
    },
    onSuccess: (response) => {
      const result = response.data
      if (result.errors && result.errors.length > 0) {
        toast.warning(`Imported ${result.imported} records with ${result.errors.length} errors`)
        console.warn('Import errors:', result.errors)
      } else {
        toast.success(`Successfully imported ${result.imported} records`)
      }
      onRefresh()
      setShowImportModal(false)
      setImportData('')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to import records')
    },
  })

  const handleExport = () => {
    const exportData = selectedRecords.map(record => ({
      name: record.name,
      type: record.type,
      value: record.value,
      ttl: record.ttl,
      priority: record.priority,
      weight: record.weight,
      port: record.port,
    }))

    const dataStr = JSON.stringify(exportData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `dns-records-export-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast.success(`Exported ${selectedRecords.length} records`)
  }

  const parseImportData = (data: string, format: string): RecordFormData[] => {
    try {
      switch (format) {
        case 'json':
          return JSON.parse(data)
        
        case 'csv':
          const lines = data.trim().split('\n')
          const headers = lines[0].split(',').map(h => h.trim())
          return lines.slice(1).map(line => {
            const values = line.split(',').map(v => v.trim())
            const record: any = {}
            headers.forEach((header, index) => {
              if (values[index]) {
                switch (header.toLowerCase()) {
                  case 'ttl':
                  case 'priority':
                  case 'weight':
                  case 'port':
                    record[header.toLowerCase()] = parseInt(values[index])
                    break
                  default:
                    record[header.toLowerCase()] = values[index]
                }
              }
            })
            return record as RecordFormData
          })
        
        case 'zone':
          // Basic zone file parsing (simplified)
          const records: RecordFormData[] = []
          const lines2 = data.trim().split('\n')
          
          for (const line of lines2) {
            const trimmed = line.trim()
            if (!trimmed || trimmed.startsWith(';') || trimmed.startsWith('$')) continue
            
            const parts = trimmed.split(/\s+/)
            if (parts.length >= 4) {
              const record: RecordFormData = {
                name: parts[0] === '@' ? '' : parts[0],
                type: parts[3] as any,
                value: parts.slice(4).join(' '),
                ttl: parseInt(parts[1]) || 3600,
              }
              
              // Handle MX and SRV records
              if (record.type === 'MX' && parts.length >= 5) {
                record.priority = parseInt(parts[4])
                record.value = parts.slice(5).join(' ')
              } else if (record.type === 'SRV' && parts.length >= 7) {
                record.priority = parseInt(parts[4])
                record.weight = parseInt(parts[5])
                record.port = parseInt(parts[6])
                record.value = parts.slice(7).join(' ')
              }
              
              records.push(record)
            }
          }
          return records
        
        default:
          throw new Error('Unsupported format')
      }
    } catch (error) {
      throw new Error(`Failed to parse ${format.toUpperCase()} data: ${error}`)
    }
  }

  const handleImport = () => {
    try {
      const records = parseImportData(importData, importFormat)
      if (records.length === 0) {
        toast.error('No valid records found in import data')
        return
      }
      importMutation.mutate({ records })
    } catch (error: any) {
      toast.error(error.message)
    }
  }

  const handleBulkEdit = () => {
    if (Object.keys(bulkEditData).length === 0) {
      toast.error('Please specify at least one field to update')
      return
    }
    bulkEditMutation.mutate(bulkEditData)
  }

  const recordsByType = selectedRecords.reduce((acc, record) => {
    acc[record.type] = (acc[record.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const activeCount = selectedRecords.filter(r => r.is_active).length
  const inactiveCount = selectedRecords.length - activeCount

  return (
    <>
      <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <CheckIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2" />
              <span className="font-medium text-blue-900 dark:text-blue-100">
                {selectedRecords.length} record{selectedRecords.length !== 1 ? 's' : ''} selected
              </span>
            </div>
            
            <div className="text-sm text-blue-700 dark:text-blue-300">
              {Object.entries(recordsByType).map(([type, count]) => (
                <span key={type} className="mr-3">
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            >
              <XMarkIcon className="h-4 w-4 mr-1" />
              Clear
            </Button>

            <div className="border-l border-blue-300 dark:border-blue-600 pl-2 flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowEditModal(true)}
                className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-600 dark:text-blue-300 dark:hover:bg-blue-800"
              >
                <PencilIcon className="h-4 w-4 mr-1" />
                Edit
              </Button>

              {activeCount > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => bulkToggleMutation.mutate(false)}
                  loading={bulkToggleMutation.isPending}
                  className="border-orange-300 text-orange-700 hover:bg-orange-100 dark:border-orange-600 dark:text-orange-300 dark:hover:bg-orange-800"
                >
                  Deactivate ({activeCount})
                </Button>
              )}

              {inactiveCount > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => bulkToggleMutation.mutate(true)}
                  loading={bulkToggleMutation.isPending}
                  className="border-green-300 text-green-700 hover:bg-green-100 dark:border-green-600 dark:text-green-300 dark:hover:bg-green-800"
                >
                  Activate ({inactiveCount})
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-600 dark:text-blue-300 dark:hover:bg-blue-800"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                Export
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowImportModal(true)}
                className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-600 dark:text-blue-300 dark:hover:bg-blue-800"
              >
                <DocumentArrowUpIcon className="h-4 w-4 mr-1" />
                Import
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteModal(true)}
                className="border-red-300 text-red-700 hover:bg-red-100 dark:border-red-600 dark:text-red-300 dark:hover:bg-red-800"
              >
                <TrashIcon className="h-4 w-4 mr-1" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Bulk Delete Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Selected Records"
        size="md"
      >
        <div className="space-y-4">
          <div className="flex items-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-600 dark:text-red-400 mr-3" />
            <div>
              <h3 className="font-medium text-red-900 dark:text-red-100">
                Confirm Bulk Deletion
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                This action cannot be undone. You are about to delete {selectedRecords.length} DNS record{selectedRecords.length !== 1 ? 's' : ''}.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium text-gray-900 dark:text-gray-100">Records to be deleted:</h4>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {selectedRecords.map(record => (
                <div key={record.id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded text-sm">
                  <span className="font-mono">
                    {record.name || '@'} {record.type} {record.value}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">
                    TTL: {record.ttl}s
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="outline"
              onClick={() => setShowDeleteModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => bulkDeleteMutation.mutate()}
              loading={bulkDeleteMutation.isPending}
            >
              Delete {selectedRecords.length} Record{selectedRecords.length !== 1 ? 's' : ''}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Bulk Edit Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Edit Selected Records"
        size="md"
      >
        <div className="space-y-6">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Editing {selectedRecords.length} record{selectedRecords.length !== 1 ? 's' : ''}. 
            Only specify the fields you want to update.
          </div>

          <div className="space-y-4">
            <Input
              label="TTL (seconds)"
              type="number"
              placeholder="Leave empty to keep current values"
              value={bulkEditData.ttl || ''}
              onChange={(e) => setBulkEditData(prev => ({
                ...prev,
                ttl: e.target.value ? parseInt(e.target.value) : undefined
              }))}
              helperText="Time To Live - how long DNS resolvers cache these records"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="outline"
              onClick={() => setShowEditModal(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleBulkEdit}
              loading={bulkEditMutation.isPending}
            >
              Update Records
            </Button>
          </div>
        </div>
      </Modal>

      {/* Import Modal */}
      <Modal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        title="Import DNS Records"
        size="lg"
      >
        <div className="space-y-6">
          <div className="space-y-4">
            <Select
              label="Import Format"
              value={importFormat}
              onChange={(e) => setImportFormat(e.target.value as any)}
              options={[
                { value: 'json', label: 'JSON' },
                { value: 'csv', label: 'CSV' },
                { value: 'zone', label: 'Zone File' },
              ]}
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Import Data
              </label>
              <textarea
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder={
                  importFormat === 'json' 
                    ? '[\n  {\n    "name": "www",\n    "type": "A",\n    "value": "192.168.1.10",\n    "ttl": 3600\n  }\n]'
                    : importFormat === 'csv'
                    ? 'name,type,value,ttl\nwww,A,192.168.1.10,3600\nmail,A,192.168.1.20,3600'
                    : 'www 3600 IN A 192.168.1.10\nmail 3600 IN A 192.168.1.20'
                }
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="outline"
              onClick={() => setShowImportModal(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              loading={importMutation.isPending}
              disabled={!importData.trim()}
            >
              Import Records
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}

export default BulkRecordActions