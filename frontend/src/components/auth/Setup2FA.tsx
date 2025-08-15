import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { QrCodeIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { authService } from '@/services/api'
import { Button, Input, Modal } from '@/components/ui'
import { toast } from 'react-toastify'

interface Setup2FAProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

interface FormData {
  token: string
}

const Setup2FA: React.FC<Setup2FAProps> = ({ isOpen, onClose, onSuccess }) => {
  const [qrCode, setQrCode] = useState<string>('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState<'setup' | 'verify' | 'complete'>('setup')

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>()

  const setupTwoFA = async () => {
    setIsLoading(true)
    try {
      const response = await authService.setup2FA()
      setQrCode(response.data.qr_code)
      setBackupCodes(response.data.backup_codes)
      setStep('verify')
    } catch (error) {
      toast.error('Failed to setup 2FA')
    } finally {
      setIsLoading(false)
    }
  }

  const verifyTwoFA = async (data: FormData) => {
    setIsLoading(true)
    try {
      await authService.verify2FA(data.token)
      setStep('complete')
      toast.success('2FA enabled successfully!')
      onSuccess?.()
    } catch (error) {
      toast.error('Invalid 2FA code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setStep('setup')
    setQrCode('')
    setBackupCodes([])
    reset()
    onClose()
  }

  const downloadBackupCodes = () => {
    const content = backupCodes.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'backup-codes.txt'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Setup Two-Factor Authentication"
      size="md"
    >
      {step === 'setup' && (
        <div className="space-y-4">
          <div className="text-center">
            <QrCodeIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              Enable Two-Factor Authentication
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Add an extra layer of security to your account by enabling 2FA.
            </p>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
              Before you begin:
            </h4>
            <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
              <li>• Install an authenticator app (Google Authenticator, Authy, etc.)</li>
              <li>• Make sure you have access to your mobile device</li>
              <li>• Keep your backup codes in a safe place</li>
            </ul>
          </div>

          <div className="flex space-x-3">
            <Button variant="outline" onClick={handleClose} className="flex-1">
              Cancel
            </Button>
            <Button onClick={setupTwoFA} loading={isLoading} className="flex-1">
              Continue
            </Button>
          </div>
        </div>
      )}

      {step === 'verify' && (
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-4">
              Scan QR Code with your authenticator app
            </h3>
            
            {qrCode && (
              <div className="flex justify-center mb-4">
                <img src={qrCode} alt="2FA QR Code" className="border rounded-lg" />
              </div>
            )}
            
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              After scanning, enter the 6-digit code from your app to verify the setup.
            </p>
          </div>

          <form onSubmit={handleSubmit(verifyTwoFA)} className="space-y-4">
            <Input
              label="Verification Code"
              type="text"
              placeholder="Enter 6-digit code"
              maxLength={6}
              {...register('token', {
                required: 'Verification code is required',
                pattern: {
                  value: /^\d{6}$/,
                  message: 'Code must be 6 digits',
                },
              })}
              error={errors.token?.message}
            />

            <div className="flex space-x-3">
              <Button variant="outline" onClick={handleClose} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" loading={isLoading} className="flex-1">
                Verify & Enable
              </Button>
            </div>
          </form>
        </div>
      )}

      {step === 'complete' && (
        <div className="space-y-4">
          <div className="text-center">
            <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              2FA Successfully Enabled!
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Your account is now protected with two-factor authentication.
            </p>
          </div>

          {backupCodes.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                Important: Save your backup codes
              </h4>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
                Store these codes in a safe place. You can use them to access your account if you lose your device.
              </p>
              
              <div className="bg-white dark:bg-gray-800 rounded border p-3 text-xs font-mono">
                {backupCodes.map((code, index) => (
                  <div key={index} className="text-gray-800 dark:text-gray-200">
                    {code}
                  </div>
                ))}
              </div>

              <div className="mt-3 flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={downloadBackupCodes}
                  className="flex-1"
                >
                  Download Codes
                </Button>
              </div>
            </div>
          )}

          <Button onClick={handleClose} className="w-full">
            Done
          </Button>
        </div>
      )}
    </Modal>
  )
}

export default Setup2FA