import React from 'react'
import {
  TrashIcon,
  PlayIcon,
  PauseIcon,
  DocumentArrowDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@/components/ui'

interface BulkRuleActionsProps {
  selectedCount: number
  onBulkDelete: () => void
  onBulkActivate: () => void
  onBulkDeactivate: () => void
  onExport: () => void
  loading?: boolean
}

const BulkRuleActions: React.FC<BulkRuleActionsProps> = ({
  selectedCount,
  onBulkDelete,
  onBulkActivate,
  onBulkDeactivate,
  onExport,
  loading = false,
}) => {
  return (
    <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="text-sm font-medium text-blue-900 dark:text-blue-100">
            {selectedCount} rule{selectedCount !== 1 ? 's' : ''} selected
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onBulkActivate}
            loading={loading}
            className="text-green-600 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-900/20"
          >
            <PlayIcon className="h-4 w-4 mr-1" />
            Activate
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onBulkDeactivate}
            loading={loading}
            className="text-yellow-600 border-yellow-300 hover:bg-yellow-50 dark:text-yellow-400 dark:border-yellow-600 dark:hover:bg-yellow-900/20"
          >
            <PauseIcon className="h-4 w-4 mr-1" />
            Deactivate
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onExport}
            className="text-blue-600 border-blue-300 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-600 dark:hover:bg-blue-900/20"
          >
            <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
            Export
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onBulkDelete}
            loading={loading}
            className="text-red-600 border-red-300 hover:bg-red-50 dark:text-red-400 dark:border-red-600 dark:hover:bg-red-900/20"
          >
            <TrashIcon className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </div>
      
      <div className="mt-2 flex items-start space-x-2">
        <ExclamationTriangleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-700 dark:text-blue-300">
          Bulk operations will affect all selected rules. Changes to active rules will trigger a BIND configuration reload.
        </div>
      </div>
    </div>
  )
}

export default BulkRuleActions