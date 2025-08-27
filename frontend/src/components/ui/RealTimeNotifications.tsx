import React, { useState, useEffect } from 'react'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'
import { useNotificationPreferences } from '@/hooks/useNotificationPreferences'
import {
  BellIcon,
  CheckIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XCircleIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline'
import { safeFormat } from '@/utils/dateUtils'
import clsx from 'clsx'

interface NotificationPanelProps {
  isOpen: boolean
  onClose: () => void
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({ isOpen, onClose }) => {
  const { events, unreadCount, acknowledgeEvent, clearEvents } = useRealTimeEvents()
  const { preferences, shouldShowNotification } = useNotificationPreferences()
  const [filter, setFilter] = useState<'all' | 'unread' | 'dns' | 'security' | 'health' | 'system'>('all')

  // Calculate filtered unread count based on preferences
  const filteredUnreadCount = events.filter(event => 
    !event.acknowledged && shouldShowNotification(event)
  ).length

  const filteredEvents = events.filter(event => {
    // First apply preference filtering
    if (!shouldShowNotification(event)) {
      return false
    }
    
    // Then apply UI filter
    if (filter === 'unread') return !event.acknowledged
    if (filter === 'dns') return event.type.includes('zone') || event.type.includes('record')
    if (filter === 'security') return event.type.includes('security') || event.type.includes('threat') || event.type.includes('rpz')
    if (filter === 'health') return event.type.includes('health') || event.type.includes('forwarder')
    if (filter === 'system') return event.type.includes('system') || event.type.includes('bind') || event.type.includes('config')
    return true
  })

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      default:
        return <InformationCircleIcon className="h-5 w-5 text-blue-500" />
    }
  }

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'success':
        return 'bg-green-50 border-green-200'
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  const formatEventType = (type: string) => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const getEventDescription = (event: any) => {
    switch (event.type) {
      case 'zone_created':
        return `Zone "${event.data.name}" was created`
      case 'zone_updated':
        return `Zone "${event.data.name}" was updated`
      case 'zone_deleted':
        return `Zone "${event.data.name}" was deleted`
      case 'record_created':
        return `Record "${event.data.name}" (${event.data.type}) was created`
      case 'record_updated':
        return `Record "${event.data.name}" (${event.data.type}) was updated`
      case 'record_deleted':
        return `Record "${event.data.name}" (${event.data.type}) was deleted`
      case 'forwarder_status_change':
        return `Forwarder ${event.data.forwarder_id} status changed from ${event.data.old_status} to ${event.data.new_status}`
      case 'security_alert':
        return event.data.message || 'Security alert detected'
      case 'threat_detected':
        return `${event.data.threat_type} threat detected: ${event.data.details || 'No details available'}`
      case 'bind_reload':
        return 'DNS server configuration reloaded successfully'
      case 'config_change':
        return `Configuration changed: ${event.data.component || 'Unknown component'}`
      default:
        return formatEventType(event.type)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-25" onClick={onClose} />

      <div className="absolute right-0 top-0 h-full w-96 bg-white shadow-xl">
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <div className="flex items-center space-x-2">
              <BellIcon className="h-5 w-5 text-gray-500" />
              <h2 className="text-lg font-medium text-gray-900">Notifications</h2>
              {filteredUnreadCount > 0 && (
                <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                  {filteredUnreadCount}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  onClose()
                  // Navigate to settings
                  window.location.href = '/settings?tab=notifications'
                }}
                className="rounded-md p-1 text-gray-400 hover:text-gray-500"
                title="Notification Settings"
              >
                <AdjustmentsHorizontalIcon className="h-4 w-4" />
              </button>
              <button
                onClick={onClose}
                className="rounded-md p-1 text-gray-400 hover:text-gray-500"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="border-b border-gray-200 px-4 py-2">
            <div className="flex space-x-1">
              {[
                { key: 'all', label: 'All' },
                { key: 'unread', label: 'Unread' },
                { key: 'dns', label: 'DNS' },
                { key: 'security', label: 'Security' },
                { key: 'health', label: 'Health' },
                { key: 'system', label: 'System' }
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setFilter(key as any)}
                  className={clsx(
                    'rounded-md px-2 py-1 text-xs font-medium',
                    filter === key
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Filtering Info */}
          {(preferences.enabled_severities.length < 5 || preferences.enabled_categories.length < 4) && (
            <div className="border-b border-gray-200 px-4 py-2 bg-blue-50 dark:bg-blue-900/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <InformationCircleIcon className="h-4 w-4 text-blue-500" />
                  <span className="text-xs text-blue-700 dark:text-blue-300">
                    Filtering: {preferences.enabled_severities.join(', ')} severity
                  </span>
                </div>
                <span className="text-xs text-blue-600 dark:text-blue-400">
                  {preferences.enabled_categories.length}/4 categories
                </span>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="border-b border-gray-200 px-4 py-2">
            <button
              onClick={clearEvents}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear all notifications
            </button>
          </div>

          {/* Notifications List */}
          <div className="flex-1 overflow-y-auto">
            {filteredEvents.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <BellIcon className="mx-auto h-12 w-12 text-gray-300" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No notifications</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {filter === 'all' ? 'All caught up!' : `No ${filter} notifications`}
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredEvents.map((event) => (
                  <div
                    key={event.id}
                    className={clsx(
                      'p-4 hover:bg-gray-50',
                      !event.acknowledged && 'bg-blue-50'
                    )}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        {getSeverityIcon(event.severity)}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">
                            {formatEventType(event.type)}
                          </p>
                          <div className="flex items-center space-x-1">
                            <time className="text-xs text-gray-500">
                              {(() => {
                                try {
                                  const date = new Date(event.timestamp);
                                  return isNaN(date.getTime()) ? 'Invalid' : safeFormat(date, 'HH:mm:ss');
                                } catch {
                                  return 'Invalid';
                                }
                              })()}
                            </time>
                            {!event.acknowledged && (
                              <button
                                onClick={() => acknowledgeEvent(event.id)}
                                className="rounded-full p-1 text-gray-400 hover:text-gray-600"
                                title="Mark as read"
                              >
                                <CheckIcon className="h-3 w-3" />
                              </button>
                            )}
                          </div>
                        </div>

                        <p className="mt-1 text-sm text-gray-600">
                          {getEventDescription(event)}
                        </p>

                        <div className="mt-2 text-xs text-gray-500">
                          {(() => {
                            try {
                              const date = new Date(event.timestamp);
                              return isNaN(date.getTime()) ? 'Invalid date' : safeFormat(date, 'MMM dd, yyyy HH:mm:ss');
                            } catch {
                              return 'Invalid date';
                            }
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export const RealTimeNotifications: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { events, unreadCount } = useRealTimeEvents()
  const { shouldShowNotification } = useNotificationPreferences()
  
  // Calculate filtered unread count based on preferences
  const filteredUnreadCount = events.filter(event => 
    !event.acknowledged && shouldShowNotification(event)
  ).length

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="relative rounded-md p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        title="Notifications"
      >
        <BellIcon className="h-6 w-6" />

        {/* Unread count badge */}
        {filteredUnreadCount > 0 && (
          <span className="absolute -top-1 -right-1 inline-flex items-center justify-center rounded-full bg-red-500 px-1.5 py-0.5 text-xs font-bold leading-none text-white min-w-[1.25rem] h-5">
            {filteredUnreadCount > 99 ? '99+' : filteredUnreadCount}
          </span>
        )}
      </button>

      <NotificationPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  )
}

export default RealTimeNotifications