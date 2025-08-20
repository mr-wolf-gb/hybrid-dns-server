import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  UserIcon,
  KeyIcon,
  ShieldCheckIcon,
  CogIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ServerIcon,
  ArrowUturnLeftIcon,
} from '@heroicons/react/24/outline'
import { authService, systemService } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { Card, Button, Input, Badge, Loading } from '@/components/ui'
import { formatDateTime } from '@/utils'
import { toast } from 'react-toastify'
import Setup2FA from '@/components/auth/Setup2FA'
import RollbackManager from '@/components/system/RollbackManager'

interface PasswordChangeForm {
  old_password: string
  new_password: string
  confirm_password: string
}

const Settings: React.FC = () => {
  const { user, updateUser } = useAuth()
  const [is2FAModalOpen, setIs2FAModalOpen] = useState(false)
  const [systemActionLoading, setSystemActionLoading] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('account')

  // Fetch system status
  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => systemService.getStatus(),
    refetchInterval: 30000,
  })

  // Fetch BIND status
  const { data: bindStatus } = useQuery({
    queryKey: ['bind-status'],
    queryFn: () => systemService.getBindStatus(),
    refetchInterval: 10000,
  })

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
    reset: resetPassword,
    watch,
  } = useForm<PasswordChangeForm>()

  const watchNewPassword = watch('new_password')

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: (data: { old_password: string; new_password: string }) =>
      authService.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed successfully')
      resetPassword()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to change password')
    },
  })

  // Disable 2FA mutation
  const disable2FAMutation = useMutation({
    mutationFn: (password: string) => authService.disable2FA(password),
    onSuccess: () => {
      toast.success('2FA has been disabled')
      updateUser({ ...user!, is_2fa_enabled: false })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to disable 2FA')
    },
  })

  const onPasswordSubmit = (data: PasswordChangeForm) => {
    changePasswordMutation.mutate({
      old_password: data.old_password,
      new_password: data.new_password,
    })
  }

  const handleDisable2FA = () => {
    const password = prompt('Enter your current password to disable 2FA:')
    if (password) {
      disable2FAMutation.mutate(password)
    }
  }

  const handleSystemAction = async (action: string) => {
    setSystemActionLoading(action)
    try {
      switch (action) {
        case 'reload-bind':
          await systemService.reloadBind()
          toast.success('BIND configuration reloaded successfully')
          break
        case 'restart-bind':
          await systemService.restartBind()
          toast.success('BIND service restarted successfully')
          break
        case 'flush-cache':
          await systemService.flushCache()
          toast.success('DNS cache flushed successfully')
          break
      }
    } catch (error) {
      toast.error(`Failed to ${action.replace('-', ' ')}`)
    } finally {
      setSystemActionLoading(null)
    }
  }

  if (!user) {
    return <Loading size="lg" text="Loading settings..." />
  }

  const tabs = [
    { id: 'account', name: 'Account', icon: UserIcon },
    { id: 'system', name: 'System', icon: ServerIcon },
    ...(user.is_superuser ? [{ id: 'rollback', name: 'Rollback', icon: ArrowUturnLeftIcon }] : []),
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Settings
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Manage your account and system configuration
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
              >
                <Icon className="h-5 w-5" />
                <span>{tab.name}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'account' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Account Information */}
          <Card
            title="Account Information"
            description="Your account details"
            action={<UserIcon className="h-5 w-5 text-gray-400" />}
          >
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Username
                </label>
                <p className="text-sm text-gray-900 dark:text-gray-100 font-mono">
                  {user.username}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Full Name
                </label>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {user.full_name || 'Not set'}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Email
                </label>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {user.email || 'Not set'}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Account Type
                </label>
                <div className="mt-1">
                  <Badge variant={user.is_superuser ? 'info' : 'default'}>
                    {user.is_superuser ? 'Administrator' : 'User'}
                  </Badge>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Last Login
                </label>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {user.last_login ? formatDateTime(user.last_login) : 'Never'}
                </p>
              </div>
            </div>
          </Card>

          {/* Two-Factor Authentication */}
          <Card
            title="Two-Factor Authentication"
            description="Secure your account with 2FA"
            action={<ShieldCheckIcon className="h-5 w-5 text-gray-400" />}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    2FA Status
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {user.is_2fa_enabled
                      ? 'Two-factor authentication is enabled'
                      : 'Two-factor authentication is disabled'
                    }
                  </p>
                </div>
                <Badge variant={user.is_2fa_enabled ? 'success' : 'default'}>
                  {user.is_2fa_enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>

              <div className="flex space-x-3">
                {user.is_2fa_enabled ? (
                  <Button
                    variant="outline"
                    onClick={handleDisable2FA}
                    loading={disable2FAMutation.isPending}
                  >
                    Disable 2FA
                  </Button>
                ) : (
                  <Button onClick={() => setIs2FAModalOpen(true)}>
                    Enable 2FA
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Change Password */}
          <Card
            title="Change Password"
            description="Update your account password"
            action={<KeyIcon className="h-5 w-5 text-gray-400" />}
          >
            <form onSubmit={handlePasswordSubmit(onPasswordSubmit)} className="space-y-4">
              <Input
                label="Current Password"
                type="password"
                {...registerPassword('old_password', {
                  required: 'Current password is required',
                })}
                error={passwordErrors.old_password?.message}
              />

              <Input
                label="New Password"
                type="password"
                {...registerPassword('new_password', {
                  required: 'New password is required',
                  minLength: {
                    value: 8,
                    message: 'Password must be at least 8 characters',
                  },
                  pattern: {
                    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                    message: 'Password must contain uppercase, lowercase, and numbers',
                  },
                })}
                error={passwordErrors.new_password?.message}
                helperText="At least 8 characters with uppercase, lowercase, and numbers"
              />

              <Input
                label="Confirm New Password"
                type="password"
                {...registerPassword('confirm_password', {
                  required: 'Please confirm your new password',
                  validate: (value) =>
                    value === watchNewPassword || 'Passwords do not match',
                })}
                error={passwordErrors.confirm_password?.message}
              />

              <Button
                type="submit"
                loading={changePasswordMutation.isPending}
                className="w-full"
              >
                Change Password
              </Button>
            </form>
          </Card>

          {/* System Status */}
          <Card
            title="System Status"
            description="DNS server system information"
            action={<ServerIcon className="h-5 w-5 text-gray-400" />}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    BIND Service
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    DNS server daemon status
                  </p>
                </div>
                <Badge variant={bindStatus?.data.data.running ? 'success' : 'danger'}>
                  {bindStatus?.data.data.running ? 'Running' : 'Stopped'}
                </Badge>
              </div>

              {systemStatus && (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        System Status
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Overall system health
                      </p>
                    </div>
                    <Badge variant="success">
                      {systemStatus.data.data.status}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        BIND Version
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                        {systemStatus.data.data.version}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Uptime
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {Math.floor(systemStatus.data.data.uptime / 3600)} hours
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* System Actions */}
          {user.is_superuser && (
            <Card
              title="System Actions"
              description="Administrative system controls"
              action={<CogIcon className="h-5 w-5 text-gray-400" />}
            >
              <div className="space-y-4">
                <div className="bg-yellow-50 dark:bg-yellow-900/50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                    <div>
                      <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                        Caution Required
                      </h4>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300">
                        These actions affect the entire DNS service
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('reload-bind')}
                    loading={systemActionLoading === 'reload-bind'}
                    className="w-full justify-start"
                  >
                    <CheckCircleIcon className="h-4 w-4 mr-2" />
                    Reload BIND Configuration
                  </Button>

                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('restart-bind')}
                    loading={systemActionLoading === 'restart-bind'}
                    className="w-full justify-start"
                  >
                    <ServerIcon className="h-4 w-4 mr-2" />
                    Restart BIND Service
                  </Button>

                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('flush-cache')}
                    loading={systemActionLoading === 'flush-cache'}
                    className="w-full justify-start"
                  >
                    <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                    Flush DNS Cache
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* System Tab */}
      {activeTab === 'system' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* System Status */}
          <Card
            title="System Status"
            description="DNS server system information"
            action={<ServerIcon className="h-5 w-5 text-gray-400" />}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    BIND Service
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    DNS server daemon status
                  </p>
                </div>
                <Badge variant={bindStatus?.data.data.running ? 'success' : 'danger'}>
                  {bindStatus?.data.data.running ? 'Running' : 'Stopped'}
                </Badge>
              </div>

              {systemStatus && (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        System Status
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Overall system health
                      </p>
                    </div>
                    <Badge variant="success">
                      {systemStatus.data.data.status}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        BIND Version
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                        {systemStatus.data.data.version}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Uptime
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {Math.floor(systemStatus.data.data.uptime / 3600)} hours
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* System Actions */}
          {user.is_superuser && (
            <Card
              title="System Actions"
              description="Administrative system controls"
              action={<CogIcon className="h-5 w-5 text-gray-400" />}
            >
              <div className="space-y-4">
                <div className="bg-yellow-50 dark:bg-yellow-900/50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                    <div>
                      <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                        Caution Required
                      </h4>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300">
                        These actions affect the entire DNS service
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('reload-bind')}
                    loading={systemActionLoading === 'reload-bind'}
                    className="w-full justify-start"
                  >
                    <CheckCircleIcon className="h-4 w-4 mr-2" />
                    Reload BIND Configuration
                  </Button>

                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('restart-bind')}
                    loading={systemActionLoading === 'restart-bind'}
                    className="w-full justify-start"
                  >
                    <ServerIcon className="h-4 w-4 mr-2" />
                    Restart BIND Service
                  </Button>

                  <Button
                    variant="outline"
                    onClick={() => handleSystemAction('flush-cache')}
                    loading={systemActionLoading === 'flush-cache'}
                    className="w-full justify-start"
                  >
                    <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                    Flush DNS Cache
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Rollback Tab */}
      {activeTab === 'rollback' && user.is_superuser && (
        <RollbackManager />
      )}

      {/* 2FA Setup Modal */}
      <Setup2FA
        isOpen={is2FAModalOpen}
        onClose={() => setIs2FAModalOpen(false)}
        onSuccess={() => {
          updateUser({ ...user!, is_2fa_enabled: true })
          setIs2FAModalOpen(false)
        }}
      />
    </div>
  )
}

export default Settings