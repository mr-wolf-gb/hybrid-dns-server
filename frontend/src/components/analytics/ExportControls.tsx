import React, { useState } from 'react'
import { 
  ArrowDownTrayIcon, 
  DocumentArrowDownIcon,
  ChartBarIcon,
  TableCellsIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline'

interface AnalyticsFilters {
  dateRange: {
    start: Date
    end: Date
  }
  interval: 'hour' | 'day' | 'week' | 'month'
  zones: number[]
  clients: string[]
  queryTypes: string[]
  categories: string[]
}

interface ExportControlsProps {
  filters: AnalyticsFilters
  onExport: (format: 'pdf' | 'csv' | 'json' | 'xlsx') => void
}

export const ExportControls: React.FC<ExportControlsProps> = ({
  filters,
  onExport,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const exportOptions = [
    {
      format: 'pdf' as const,
      label: 'PDF Report',
      description: 'Comprehensive report with charts and insights',
      icon: DocumentTextIcon,
      color: 'text-red-600',
    },
    {
      format: 'xlsx' as const,
      label: 'Excel Spreadsheet',
      description: 'Raw data in Excel format for analysis',
      icon: TableCellsIcon,
      color: 'text-green-600',
    },
    {
      format: 'csv' as const,
      label: 'CSV Data',
      description: 'Comma-separated values for data processing',
      icon: DocumentArrowDownIcon,
      color: 'text-blue-600',
    },
    {
      format: 'json' as const,
      label: 'JSON Data',
      description: 'Structured data in JSON format',
      icon: ChartBarIcon,
      color: 'text-purple-600',
    },
  ]

  const handleExport = async (format: 'pdf' | 'csv' | 'json' | 'xlsx') => {
    setIsExporting(true)
    try {
      await onExport(format)
    } finally {
      setIsExporting(false)
      setIsOpen(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
        {isExporting ? 'Exporting...' : 'Export'}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
          <div className="p-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Export Analytics Data
            </h3>
            
            {/* Export Options */}
            <div className="space-y-3">
              {exportOptions.map((option) => (
                <button
                  key={option.format}
                  onClick={() => handleExport(option.format)}
                  disabled={isExporting}
                  className="w-full flex items-start p-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  <option.icon className={`h-5 w-5 mr-3 mt-0.5 ${option.color}`} />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {option.label}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {option.description}
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {/* Export Settings */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                Export Settings
              </h4>
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex justify-between">
                  <span>Date Range:</span>
                  <span>
                    {filters.dateRange.start.toLocaleDateString()} - {filters.dateRange.end.toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Interval:</span>
                  <span className="capitalize">{filters.interval}</span>
                </div>
                {filters.zones.length > 0 && (
                  <div className="flex justify-between">
                    <span>Zones:</span>
                    <span>{filters.zones.length} selected</span>
                  </div>
                )}
                {filters.clients.length > 0 && (
                  <div className="flex justify-between">
                    <span>Clients:</span>
                    <span>{filters.clients.length} selected</span>
                  </div>
                )}
                {filters.queryTypes.length > 0 && (
                  <div className="flex justify-between">
                    <span>Query Types:</span>
                    <span>{filters.queryTypes.length} selected</span>
                  </div>
                )}
                {filters.categories.length > 0 && (
                  <div className="flex justify-between">
                    <span>Categories:</span>
                    <span>{filters.categories.length} selected</span>
                  </div>
                )}
              </div>
            </div>

            {/* Close Button */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setIsOpen(false)}
                className="w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}