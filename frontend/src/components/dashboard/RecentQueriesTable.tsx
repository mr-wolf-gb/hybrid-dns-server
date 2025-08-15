import React from 'react'
import { RecentQuery } from '@/types'
import { Badge } from '@/components/ui'
import { formatRelativeTime } from '@/utils'

interface RecentQueriesTableProps {
  queries: RecentQuery[]
}

const RecentQueriesTable: React.FC<RecentQueriesTableProps> = ({ queries }) => {
  if (!queries || queries.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500 dark:text-gray-400 text-sm">
        No recent queries
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {queries.map((query, index) => (
        <div 
          key={index} 
          className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-b-0"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {query.domain}
              </span>
              {query.blocked && (
                <Badge variant="danger" size="sm">
                  Blocked
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {query.client_ip}
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500">•</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {query.type}
              </span>
              {query.category && (
                <>
                  <span className="text-xs text-gray-400 dark:text-gray-500">•</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {query.category}
                  </span>
                </>
              )}
            </div>
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            {formatRelativeTime(query.timestamp)}
          </div>
        </div>
      ))}
    </div>
  )
}

export default RecentQueriesTable