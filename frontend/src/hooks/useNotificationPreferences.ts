import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { userService } from '@/services/api'

interface NotificationPreferences {
  enabled_severities: string[]
  enabled_categories: string[]
  show_health_updates: boolean
  show_system_events: boolean
  show_dns_events: boolean
  show_security_events: boolean
  throttle_duration: number
  max_notifications_per_minute: number
}

const DEFAULT_PREFERENCES: NotificationPreferences = {
  enabled_severities: ['warning', 'error', 'critical'],
  enabled_categories: ['dns', 'security', 'system'],
  show_health_updates: false,
  show_system_events: true,
  show_dns_events: true,
  show_security_events: true,
  throttle_duration: 5000,
  max_notifications_per_minute: 10
}

export const useNotificationPreferences = () => {
  const [preferences, setPreferences] = useState<NotificationPreferences>(DEFAULT_PREFERENCES)

  // Fetch preferences from API
  const { data, isLoading, error } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: () => userService.getNotificationPreferences(),
  })

  // Handle data updates with useEffect instead of onSuccess
  useEffect(() => {
    if (data?.data?.data) {
      setPreferences({ ...DEFAULT_PREFERENCES, ...data.data.data })
    } else if (error) {
      // If preferences don't exist, use defaults
      setPreferences(DEFAULT_PREFERENCES)
    }
  }, [data, error])

  // Listen for preference updates
  useEffect(() => {
    const handlePreferencesUpdate = (event: CustomEvent) => {
      setPreferences(event.detail)
    }

    window.addEventListener('notificationPreferencesUpdated', handlePreferencesUpdate as EventListener)
    
    return () => {
      window.removeEventListener('notificationPreferencesUpdated', handlePreferencesUpdate as EventListener)
    }
  }, [])

  // Helper function to check if a notification should be shown
  const shouldShowNotification = (event: any): boolean => {
    // Check severity filter
    if (!preferences.enabled_severities.includes(event.severity || 'info')) {
      return false
    }

    // Check category filter
    const eventCategory = getEventCategory(event.type)
    if (!preferences.enabled_categories.includes(eventCategory)) {
      return false
    }

    // Special handling for health updates
    if (eventCategory === 'health' && !preferences.show_health_updates) {
      return false
    }

    return true
  }

  // Helper function to determine event category from event type
  const getEventCategory = (eventType: string): string => {
    if (eventType.includes('health') || eventType.includes('forwarder')) {
      return 'health'
    }
    if (eventType.includes('zone') || eventType.includes('record') || eventType.includes('dns')) {
      return 'dns'
    }
    if (eventType.includes('security') || eventType.includes('threat') || eventType.includes('rpz')) {
      return 'security'
    }
    if (eventType.includes('system') || eventType.includes('bind') || eventType.includes('config')) {
      return 'system'
    }
    return 'system' // default category
  }

  return {
    preferences,
    isLoading,
    error,
    shouldShowNotification,
    getEventCategory
  }
}

export default useNotificationPreferences