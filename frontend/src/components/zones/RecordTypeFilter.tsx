import React from 'react'
import { FunnelIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { DNSRecord } from '@/types'
import { Button, Card, Badge } from '@/components/ui'

interface RecordTypeFilterProps {
  records: DNSRecord[]
  selectedTypes: string[]
  onTypeToggle: (type: string) => void
  onClearFilters: () => void
  showFilters: boolean
  onToggleFilters: () => void
}

const RecordTypeFilter: React.FC<RecordTypeFilterProps> = ({
  records,
  selectedTypes,
  onTypeToggle,
  onClearFilters,
  showFilters,
  onToggleFilters,
}) => {
  // Get available types from current records with counts
  const availableTypes = React.useMemo(() => {
    const typeCounts = records.reduce((acc, record) => {
      acc[record.type] = (acc[record.type] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    return Object.entries(typeCounts)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([type, count]) => ({ type, count }))
  }, [records])

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

  const hasActiveFilters = selectedTypes.length > 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={onToggleFilters}
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
            onClick={onClearFilters}
            className="flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <XMarkIcon className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {/* Type filters */}
      {showFilters && (
        <Card className="p-4">
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Filter by Record Type
            </h3>
            <div className="flex flex-wrap gap-2">
              {availableTypes.map(({ type, count }) => (
                <button
                  key={type}
                  onClick={() => onTypeToggle(type)}
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    selectedTypes.includes(type)
                      ? `${getRecordTypeColor(type)} ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-gray-800`
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {type}
                  <span className="ml-2 text-xs">
                    {count}
                  </span>
                </button>
              ))}
            </div>
            
            {availableTypes.length === 0 && (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No record types available
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

export default RecordTypeFilter