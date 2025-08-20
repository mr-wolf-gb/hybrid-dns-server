import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { 
  ArrowUpTrayIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone } from '@/types'
import { Modal, Button, Badge } from '@/components/ui'
import { toast } from 'react-toastify'

interface ZoneImportExportModalProps {
  zone?: Zone
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  mode: 'import' | 'export'
}

const ZoneImportExportModal: React.FC<ZoneImportExportModalProps> = ({ 
  zone, 
  isOpen, 
  onClose,
  onSuccess,
  mode
}) => {
  const [importData, setImportData] = useState('')
  const [zoneName, setZoneName] = useState('')
  const [format, setFormat] = useState<'bind' | 'json'>('bind')
  const [exportData, setExportData] = useState('')

  // Export zone mutation
  const exportZoneMutation = useMutation({
    mutationFn: () => zonesService.exportZone(zone!.id, format),
    onSuccess: (response) => {
      setExportData(response.data)
      toast.success('Zone exported successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to export zone')
    },
  })

  // Import zone mutation
  const importZoneMutation = useMutation({
    mutationFn: (data: { name: string; zone_data: string; format: string }) => 
      zonesService.importZone(data),
    onSuccess: () => {
      toast.success('Zone imported successfully')
      onSuccess?.()
      handleClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to import zone')
    },
  })

  const handleExport = () => {
    if (!zone) return
    exportZoneMutation.mutate()
  }

  const handleImport = () => {
    if (!importData.trim() || !zoneName.trim()) {
      toast.error('Please provide zone name and data')
      return
    }

    importZoneMutation.mutate({
      name: zoneName,
      zone_data: importData,
      format
    })
  }

  const handleDownload = () => {
    if (!exportData || !zone) return

    const blob = new Blob([exportData], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${zone.name}.${format === 'bind' ? 'zone' : 'json'}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleClose = () => {
    setImportData('')
    setZoneName('')
    setExportData('')
    setFormat('bind')
    onClose()
  }

  const isLoading = exportZoneMutation.isPending || importZoneMutation.isPending

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'import' ? 'Import Zone' : `Export Zone: ${zone?.name}`}
      size="lg"
    >
      <div className="space-y-6">
        {/* Format Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setFormat('bind')}
              className={`p-3 text-left border rounded-lg transition-colors ${
                format === 'bind'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-5 w-5" />
                <div>
                  <div className="font-medium">BIND Zone File</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Standard DNS zone format
                  </div>
                </div>
              </div>
            </button>
            
            <button
              type="button"
              onClick={() => setFormat('json')}
              className={`p-3 text-left border rounded-lg transition-colors ${
                format === 'json'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-5 w-5" />
                <div>
                  <div className="font-medium">JSON Format</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Structured data format
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>

        {mode === 'import' ? (
          <>
            {/* Zone Name Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Zone Name
              </label>
              <input
                type="text"
                value={zoneName}
                onChange={(e) => setZoneName(e.target.value)}
                placeholder="example.com"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
              />
            </div>

            {/* Import Data Textarea */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Zone Data
              </label>
              <textarea
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder={format === 'bind' ? 
                  '$ORIGIN example.com.\n$TTL 3600\n@\tIN\tSOA\tns1.example.com. admin.example.com. (\n\t\t2024010101\t; Serial\n\t\t3600\t\t; Refresh\n\t\t1800\t\t; Retry\n\t\t604800\t\t; Expire\n\t\t86400\t\t; Minimum TTL\n)\n@\tIN\tNS\tns1.example.com.\n@\tIN\tA\t192.168.1.100' :
                  '{\n  "name": "example.com",\n  "type": "master",\n  "records": [\n    {\n      "name": "@",\n      "type": "A",\n      "value": "192.168.1.100",\n      "ttl": 3600\n    }\n  ]\n}'
                }
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100 font-mono text-sm"
              />
            </div>

            {/* Import Info */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <ExclamationTriangleIcon className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  <p className="font-medium mb-1">Import Guidelines:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Ensure the zone data is properly formatted</li>
                    <li>BIND format should include SOA and NS records</li>
                    <li>JSON format should follow the expected schema</li>
                    <li>Existing zones with the same name will be updated</li>
                  </ul>
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* Zone Info */}
            {zone && (
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                      {zone.name}
                    </h3>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant={zone.zone_type === 'master' ? 'success' : 'info'}>
                        {zone.zone_type}
                      </Badge>
                      <Badge variant={zone.is_active ? 'success' : 'default'}>
                        {zone.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {zone.record_count || 0} records
                      </span>
                    </div>
                  </div>
                  <ArrowDownTrayIcon className="h-8 w-8 text-gray-400" />
                </div>
              </div>
            )}

            {/* Export Data Display */}
            {exportData && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Exported Zone Data
                  </label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownload}
                    className="flex items-center space-x-1"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4" />
                    <span>Download</span>
                  </Button>
                </div>
                <textarea
                  value={exportData}
                  readOnly
                  rows={12}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 font-mono text-sm"
                />
              </div>
            )}

            {/* Export Success */}
            {exportData && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  <span className="text-sm text-green-700 dark:text-green-300">
                    Zone exported successfully. You can copy the data above or download it as a file.
                  </span>
                </div>
              </div>
            )}
          </>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            {mode === 'export' && exportData ? 'Close' : 'Cancel'}
          </Button>
          
          {mode === 'import' ? (
            <Button
              onClick={handleImport}
              loading={isLoading}
              disabled={!importData.trim() || !zoneName.trim()}
              className="flex items-center space-x-2"
            >
              <ArrowUpTrayIcon className="h-4 w-4" />
              <span>Import Zone</span>
            </Button>
          ) : (
            !exportData && (
              <Button
                onClick={handleExport}
                loading={isLoading}
                className="flex items-center space-x-2"
              >
                <ArrowDownTrayIcon className="h-4 w-4" />
                <span>Export Zone</span>
              </Button>
            )
          )}
        </div>
      </div>
    </Modal>
  )
}

export default ZoneImportExportModal