import React, { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
    BellIcon,
    ExclamationTriangleIcon,
    InformationCircleIcon,
    CheckCircleIcon,
    XCircleIcon,
    AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'
import { Card, Button, Loading } from '@/components/ui'
import { toast } from 'react-toastify'
import { userService } from '@/services/api'
import clsx from 'clsx'

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

const SEVERITY_LEVELS = [
    {
        key: 'debug',
        label: 'Debug',
        description: 'Detailed debugging information',
        icon: InformationCircleIcon,
        color: 'text-gray-500',
        bgColor: 'bg-gray-50 dark:bg-gray-800',
        borderColor: 'border-gray-200 dark:border-gray-700'
    },
    {
        key: 'info',
        label: 'Info',
        description: 'General information messages',
        icon: InformationCircleIcon,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50 dark:bg-blue-900/20',
        borderColor: 'border-blue-200 dark:border-blue-700'
    },
    {
        key: 'warning',
        label: 'Warning',
        description: 'Warning conditions that need attention',
        icon: ExclamationTriangleIcon,
        color: 'text-yellow-500',
        bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
        borderColor: 'border-yellow-200 dark:border-yellow-700'
    },
    {
        key: 'error',
        label: 'Error',
        description: 'Error conditions that require action',
        icon: XCircleIcon,
        color: 'text-red-500',
        bgColor: 'bg-red-50 dark:bg-red-900/20',
        borderColor: 'border-red-200 dark:border-red-700'
    },
    {
        key: 'critical',
        label: 'Critical',
        description: 'Critical conditions requiring immediate attention',
        icon: XCircleIcon,
        color: 'text-red-600',
        bgColor: 'bg-red-100 dark:bg-red-900/40',
        borderColor: 'border-red-300 dark:border-red-600'
    }
]

const CATEGORY_TYPES = [
    {
        key: 'health',
        label: 'Health Updates',
        description: 'System health checks and forwarder status',
        icon: CheckCircleIcon,
        defaultEnabled: false
    },
    {
        key: 'dns',
        label: 'DNS Events',
        description: 'Zone and record changes',
        icon: InformationCircleIcon,
        defaultEnabled: true
    },
    {
        key: 'security',
        label: 'Security Events',
        description: 'Security alerts and threat detection',
        icon: ExclamationTriangleIcon,
        defaultEnabled: true
    },
    {
        key: 'system',
        label: 'System Events',
        description: 'System configuration and service changes',
        icon: AdjustmentsHorizontalIcon,
        defaultEnabled: true
    }
]

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

export const NotificationSettings: React.FC = () => {
    const [preferences, setPreferences] = useState<NotificationPreferences>(DEFAULT_PREFERENCES)
    const [hasChanges, setHasChanges] = useState(false)
    const queryClient = useQueryClient()

    // Fetch current preferences
    const { data: currentPreferences, isLoading } = useQuery({
        queryKey: ['notification-preferences'],
        queryFn: () => userService.getNotificationPreferences(),
        onSuccess: (data) => {
            if (data?.data) {
                setPreferences({ ...DEFAULT_PREFERENCES, ...data.data })
            }
        },
        onError: () => {
            // If preferences don't exist, use defaults
            setPreferences(DEFAULT_PREFERENCES)
        }
    })

    // Save preferences mutation
    const savePreferencesMutation = useMutation({
        mutationFn: (prefs: NotificationPreferences) =>
            userService.updateNotificationPreferences(prefs),
        onSuccess: () => {
            toast.success('Notification preferences saved successfully')
            setHasChanges(false)
            queryClient.invalidateQueries({ queryKey: ['notification-preferences'] })

            // Trigger a custom event to update the notification system
            window.dispatchEvent(new CustomEvent('notificationPreferencesUpdated', {
                detail: preferences
            }))
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to save notification preferences')
        }
    })

    const handleSeverityToggle = (severity: string) => {
        const newSeverities = preferences.enabled_severities.includes(severity)
            ? preferences.enabled_severities.filter(s => s !== severity)
            : [...preferences.enabled_severities, severity]

        setPreferences(prev => ({ ...prev, enabled_severities: newSeverities }))
        setHasChanges(true)
    }

    const handleCategoryToggle = (category: string) => {
        const newCategories = preferences.enabled_categories.includes(category)
            ? preferences.enabled_categories.filter(c => c !== category)
            : [...preferences.enabled_categories, category]

        setPreferences(prev => ({ ...prev, enabled_categories: newCategories }))
        setHasChanges(true)
    }

    const handleThrottleChange = (value: number) => {
        setPreferences(prev => ({ ...prev, throttle_duration: value * 1000 }))
        setHasChanges(true)
    }

    const handleMaxNotificationsChange = (value: number) => {
        setPreferences(prev => ({ ...prev, max_notifications_per_minute: value }))
        setHasChanges(true)
    }

    const handleSave = () => {
        savePreferencesMutation.mutate(preferences)
    }

    const handleReset = () => {
        setPreferences(DEFAULT_PREFERENCES)
        setHasChanges(true)
    }

    if (isLoading) {
        return <Loading size="lg" text="Loading notification preferences..." />
    }

    return (
        <div className="space-y-6">
            {/* Severity Filtering */}
            <Card
                title="Notification Severity"
                description="Choose which severity levels to show in notifications"
                action={<BellIcon className="h-5 w-5 text-gray-400" />}
            >
                <div className="space-y-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                        <div className="flex items-start space-x-3">
                            <InformationCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                            <div>
                                <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                                    Severity Filtering
                                </h4>
                                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                                    Select which severity levels you want to see. Higher severity levels (Warning, Error, Critical)
                                    are recommended to avoid missing important alerts.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-3">
                        {SEVERITY_LEVELS.map((severity) => {
                            const Icon = severity.icon
                            const isEnabled = preferences.enabled_severities.includes(severity.key)

                            return (
                                <div
                                    key={severity.key}
                                    className={clsx(
                                        'border rounded-lg p-4 cursor-pointer transition-all duration-200',
                                        isEnabled
                                            ? `${severity.bgColor} ${severity.borderColor} ring-2 ring-blue-500 ring-opacity-20`
                                            : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    )}
                                    onClick={() => handleSeverityToggle(severity.key)}
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                            <Icon className={clsx('h-5 w-5', isEnabled ? severity.color : 'text-gray-400')} />
                                            <div>
                                                <h4 className={clsx(
                                                    'text-sm font-medium',
                                                    isEnabled ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'
                                                )}>
                                                    {severity.label}
                                                </h4>
                                                <p className={clsx(
                                                    'text-xs',
                                                    isEnabled ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'
                                                )}>
                                                    {severity.description}
                                                </p>
                                            </div>
                                        </div>
                                        <div className={clsx(
                                            'w-4 h-4 rounded border-2 flex items-center justify-center',
                                            isEnabled
                                                ? 'bg-blue-500 border-blue-500'
                                                : 'border-gray-300 dark:border-gray-600'
                                        )}>
                                            {isEnabled && (
                                                <CheckCircleIcon className="h-3 w-3 text-white" />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </Card>

            {/* Category Filtering */}
            <Card
                title="Event Categories"
                description="Choose which types of events to show"
                action={<AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-400" />}
            >
                <div className="space-y-4">
                    <div className="grid grid-cols-1 gap-3">
                        {CATEGORY_TYPES.map((category) => {
                            const Icon = category.icon
                            const isEnabled = preferences.enabled_categories.includes(category.key)

                            return (
                                <div
                                    key={category.key}
                                    className={clsx(
                                        'border rounded-lg p-4 cursor-pointer transition-all duration-200',
                                        isEnabled
                                            ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700 ring-2 ring-blue-500 ring-opacity-20'
                                            : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    )}
                                    onClick={() => handleCategoryToggle(category.key)}
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                            <Icon className={clsx(
                                                'h-5 w-5',
                                                isEnabled ? 'text-blue-500' : 'text-gray-400'
                                            )} />
                                            <div>
                                                <h4 className={clsx(
                                                    'text-sm font-medium',
                                                    isEnabled ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'
                                                )}>
                                                    {category.label}
                                                </h4>
                                                <p className={clsx(
                                                    'text-xs',
                                                    isEnabled ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'
                                                )}>
                                                    {category.description}
                                                </p>
                                            </div>
                                        </div>
                                        <div className={clsx(
                                            'w-4 h-4 rounded border-2 flex items-center justify-center',
                                            isEnabled
                                                ? 'bg-blue-500 border-blue-500'
                                                : 'border-gray-300 dark:border-gray-600'
                                        )}>
                                            {isEnabled && (
                                                <CheckCircleIcon className="h-3 w-3 text-white" />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </Card>

            {/* Advanced Settings */}
            <Card
                title="Advanced Settings"
                description="Fine-tune notification behavior"
                action={<AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-400" />}
            >
                <div className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Throttle Duration (seconds)
                        </label>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                            Minimum time between similar notifications to prevent spam
                        </p>
                        <div className="flex items-center space-x-4">
                            <input
                                type="range"
                                min="1"
                                max="60"
                                value={preferences.throttle_duration / 1000}
                                onChange={(e) => handleThrottleChange(parseInt(e.target.value))}
                                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                            />
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 min-w-[3rem]">
                                {preferences.throttle_duration / 1000}s
                            </span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Max Notifications Per Minute
                        </label>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                            Maximum number of notifications to show per minute
                        </p>
                        <div className="flex items-center space-x-4">
                            <input
                                type="range"
                                min="1"
                                max="50"
                                value={preferences.max_notifications_per_minute}
                                onChange={(e) => handleMaxNotificationsChange(parseInt(e.target.value))}
                                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                            />
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 min-w-[3rem]">
                                {preferences.max_notifications_per_minute}
                            </span>
                        </div>
                    </div>
                </div>
            </Card>

            {/* Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button
                    variant="outline"
                    onClick={handleReset}
                    disabled={!hasChanges}
                >
                    Reset to Defaults
                </Button>

                <div className="flex items-center space-x-3">
                    {hasChanges && (
                        <span className="text-sm text-yellow-600 dark:text-yellow-400">
                            You have unsaved changes
                        </span>
                    )}
                    <Button
                        onClick={handleSave}
                        loading={savePreferencesMutation.isPending}
                        disabled={!hasChanges}
                    >
                        Save Preferences
                    </Button>
                </div>
            </div>
        </div>
    )
}

export default NotificationSettings