import React, { useState } from 'react'
import { format } from 'date-fns'
import { CalendarIcon, FunnelIcon } from '@heroicons/react/24/outline'

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

interface AnalyticsFiltersProps {
  filters: AnalyticsFilters
  onFiltersChange: (filters: AnalyticsFilters) => void
}

export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  filters,
  onFiltersChange,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleDateRangeChange = (field: 'start' | 'end', value: string) => {
    onFiltersChange({
      ...filters,
      dateRange: {
        ...filters.dateRange,
        [field]: new Date(value),
      },
    })
  }

  const handleIntervalChange = (interval: 'hour' | 'day' | 'week' | 'month') => {
    onFiltersChange({
      ...filters,
      interval,
    })
  }

  const quickRanges = [
    { label: 'Last 24 hours', hours: 24 },
    { label: 'Last 7 days', hours: 24 * 7 },
    { label: 'Last 30 days', hours: 24 * 30 },
    { label: 'Last 90 days', hours: 24 * 90 },
  ]

  const handleQuickRange = (hours: number) => {
    const end = new Date()
    const start = new Date(end.getTime() - hours * 60 * 60 * 1000)
    onFiltersChange({
      ...filters,
      dateRange: { start, end },
    })
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
          <FunnelIcon className="h-5 w-5 mr-2" />
          Filters
        </h3>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
        >
          {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Date Range */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Start Date
          </label>
          <div className="relative">
            <input
              type="datetime-local"
              value={format(filters.dateRange.start, "yyyy-MM-dd'T'HH:mm")}
              onChange={(e) => handleDateRangeChange('start', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
            <CalendarIcon className="absolute right-3 top-2.5 h-5 w-5 text-gray-400 pointer-events-none" />
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            End Date
          </label>
          <div className="relative">
            <input
              type="datetime-local"
              value={format(filters.dateRange.end, "yyyy-MM-dd'T'HH:mm")}
              onChange={(e) => handleDateRangeChange('end', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
            <CalendarIcon className="absolute right-3 top-2.5 h-5 w-5 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Interval */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Interval
          </label>
          <select
            value={filters.interval}
            onChange={(e) => handleIntervalChange(e.target.value as any)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="hour">Hourly</option>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
        </div>

        {/* Quick Ranges */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Quick Ranges
          </label>
          <div className="flex flex-wrap gap-2">
            {quickRanges.map((range) => (
              <button
                key={range.label}
                onClick={() => handleQuickRange(range.hours)}
                className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-md text-gray-700 dark:text-gray-300"
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Query Types */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Query Types
              </label>
              <div className="space-y-1">
                {['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR'].map((type) => (
                  <label key={type} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.queryTypes.includes(type)}
                      onChange={(e) => {
                        const newTypes = e.target.checked
                          ? [...filters.queryTypes, type]
                          : filters.queryTypes.filter(t => t !== type)
                        onFiltersChange({
                          ...filters,
                          queryTypes: newTypes,
                        })
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      {type}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Categories */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Security Categories
              </label>
              <div className="space-y-1">
                {['malware', 'phishing', 'adult', 'social_media', 'gambling'].map((category) => (
                  <label key={category} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.categories.includes(category)}
                      onChange={(e) => {
                        const newCategories = e.target.checked
                          ? [...filters.categories, category]
                          : filters.categories.filter(c => c !== category)
                        onFiltersChange({
                          ...filters,
                          categories: newCategories,
                        })
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 capitalize">
                      {category.replace('_', ' ')}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Client IPs */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Client IPs
              </label>
              <textarea
                placeholder="Enter IP addresses, one per line"
                value={filters.clients.join('\n')}
                onChange={(e) => {
                  const clients = e.target.value.split('\n').filter(ip => ip.trim())
                  onFiltersChange({
                    ...filters,
                    clients,
                  })
                }}
                rows={3}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm"
              />
            </div>

            {/* Reset Filters */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Actions
              </label>
              <button
                onClick={() => {
                  const end = new Date()
                  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
                  onFiltersChange({
                    dateRange: { start, end },
                    interval: 'day',
                    zones: [],
                    clients: [],
                    queryTypes: [],
                    categories: [],
                  })
                }}
                className="w-full px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-md text-gray-700 dark:text-gray-300"
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}