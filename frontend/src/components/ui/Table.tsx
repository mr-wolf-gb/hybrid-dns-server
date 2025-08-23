import React, { ReactNode } from 'react'
import { cn } from '@/utils'
import Loading from './Loading'

interface Column<T> {
  key: string
  header: string | ReactNode
  render?: (item: T, index: number) => ReactNode
  sortable?: boolean
  className?: string
}

interface TableProps<T> {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  emptyMessage?: string
  className?: string
  onSort?: (key: string) => void
  sortKey?: string
  sortDirection?: 'asc' | 'desc'
}

function Table<T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No data available',
  className,
  onSort,
  sortKey,
  sortDirection,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-8">
          <Loading text="Loading data..." />
        </div>
      </div>
    )
  }

  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg shadow', className)}>
      <div className="overflow-x-auto overflow-y-visible">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    'px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider',
                    column.sortable && onSort && 'cursor-pointer hover:text-gray-700 dark:hover:text-gray-300',
                    column.className
                  )}
                  onClick={() => column.sortable && onSort && onSort(column.key)}
                >
                  <div className="flex items-center space-x-1">
                    {typeof column.header === 'string' ? <span>{column.header}</span> : column.header}
                    {column.sortable && onSort && (
                      <div className="flex flex-col">
                        <svg
                          className={cn(
                            'w-3 h-3',
                            sortKey === column.key && sortDirection === 'asc'
                              ? 'text-primary-600'
                              : 'text-gray-400'
                          )}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                        </svg>
                        <svg
                          className={cn(
                            'w-3 h-3 -mt-1',
                            sortKey === column.key && sortDirection === 'desc'
                              ? 'text-primary-600'
                              : 'text-gray-400'
                          )}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-12 text-center text-gray-500 dark:text-gray-400"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item, index) => (
                <tr
                  key={index}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        'px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100',
                        column.className
                      )}
                    >
                      {column.render ? column.render(item, index) : item[column.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Table