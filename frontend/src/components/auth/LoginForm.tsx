import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { EyeIcon, EyeSlashIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { LoginRequest } from '@/types'
import { Button, Input } from '@/components/ui'

interface LoginFormProps {
  onSuccess?: () => void
}

interface FormData {
  username: string
  password: string
  totp_code?: string
}

const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const { login } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [requires2FA, setRequires2FA] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    clearErrors,
  } = useForm<FormData>()

  const onSubmit = async (data: FormData) => {
    setIsLoading(true)
    clearErrors()

    try {
      const loginData: LoginRequest = {
        username: data.username,
        password: data.password,
      }

      if (data.totp_code) {
        loginData.totp_code = data.totp_code
      }

      await login(loginData)
      onSuccess?.()
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      
      if (errorMessage.includes('2FA') || errorMessage.includes('TOTP')) {
        setRequires2FA(true)
        setError('totp_code', { message: 'Please enter your 2FA code' })
      } else if (errorMessage.includes('username')) {
        setError('username', { message: errorMessage })
      } else if (errorMessage.includes('password')) {
        setError('password', { message: errorMessage })
      } else {
        setError('root', { message: errorMessage })
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900">
            <ShieldCheckIcon className="h-8 w-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-gray-100">
            Hybrid DNS Server
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Sign in to your account
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            <Input
              label="Username"
              type="text"
              autoComplete="username"
              required
              {...register('username', {
                required: 'Username is required',
              })}
              error={errors.username?.message}
            />

            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              {...register('password', {
                required: 'Password is required',
              })}
              error={errors.password?.message}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400"
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )}
                </button>
              }
            />

            {requires2FA && (
              <Input
                label="2FA Code"
                type="text"
                placeholder="Enter 6-digit code"
                maxLength={6}
                {...register('totp_code', {
                  required: requires2FA ? '2FA code is required' : false,
                  pattern: {
                    value: /^\d{6}$/,
                    message: '2FA code must be 6 digits',
                  },
                })}
                error={errors.totp_code?.message}
                helperText="Enter the 6-digit code from your authenticator app"
              />
            )}
          </div>

          {errors.root && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/50 p-4">
              <p className="text-sm text-red-600 dark:text-red-400">
                {errors.root.message}
              </p>
            </div>
          )}

          <Button
            type="submit"
            className="w-full"
            loading={isLoading}
            disabled={isLoading}
          >
            Sign in
          </Button>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                Secure DNS Management
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginForm