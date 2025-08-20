import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  ArrowPathIcon,
  DocumentCheckIcon
} from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone, ValidationResult } from '@/types'
import { Modal, Button, Badge } from '@/components/ui'
import { toast } from 'react-toastify'

interface ZoneValidationModalProps {
  zone: Zone
  isOpen: boolean
  onClose: () => void
}



const ZoneValidationModal: React.FC<ZoneValidationModalProps> = ({ 
  zone, 
  isOpen, 
  onClose 
}) => {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [validationType, setValidationType] = useState<'full' | 'configuration' | 'records'>('full')

  // Full zone validation
  const validateZoneMutation = useMutation({
    mutationFn: () => zonesService.validateZone(zone.id),
    onSuccess: (response) => {
      setValidationResult(response.data)
      if (response.data.valid) {
        toast.success('Zone validation passed')
      } else {
        toast.warning('Zone validation found issues')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to validate zone')
    },
  })

  // Configuration validation
  const validateConfigMutation = useMutation({
    mutationFn: () => zonesService.validateZoneConfiguration(zone.id),
    onSuccess: (response) => {
      setValidationResult(response.data)
      if (response.data.valid) {
        toast.success('Zone configuration validation passed')
      } else {
        toast.warning('Zone configuration validation found issues')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to validate zone configuration')
    },
  })

  // Records validation
  const validateRecordsMutation = useMutation({
    mutationFn: () => zonesService.validateZoneRecords(zone.id),
    onSuccess: (response) => {
      setValidationResult(response.data)
      if (response.data.valid) {
        toast.success('Zone records validation passed')
      } else {
        toast.warning('Zone records validation found issues')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to validate zone records')
    },
  })

  const handleValidation = () => {
    setValidationResult(null)
    
    switch (validationType) {
      case 'full':
        validateZoneMutation.mutate()
        break
      case 'configuration':
        validateConfigMutation.mutate()
        break
      case 'records':
        validateRecordsMutation.mutate()
        break
    }
  }

  const handleClose = () => {
    setValidationResult(null)
    setValidationType('full')
    onClose()
  }

  const isLoading = validateZoneMutation.isPending || 
                   validateConfigMutation.isPending || 
                   validateRecordsMutation.isPending

  const getValidationIcon = () => {
    if (!validationResult) return null
    
    if (validationResult.valid) {
      return <CheckCircleIcon className="h-8 w-8 text-green-500" />
    } else if (validationResult.errors.length > 0) {
      return <XCircleIcon className="h-8 w-8 text-red-500" />
    } else {
      return <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />
    }
  }

  const getValidationStatus = () => {
    if (!validationResult) return null
    
    if (validationResult.valid) {
      return (
        <div className="flex items-center space-x-2">
          <Badge variant="success">Valid</Badge>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Zone configuration is valid
          </span>
        </div>
      )
    } else if (validationResult.errors.length > 0) {
      return (
        <div className="flex items-center space-x-2">
          <Badge variant="danger">Invalid</Badge>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {validationResult.errors.length} error{validationResult.errors.length > 1 ? 's' : ''} found
          </span>
        </div>
      )
    } else {
      return (
        <div className="flex items-center space-x-2">
          <Badge variant="warning">Warning</Badge>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {validationResult.warnings.length} warning{validationResult.warnings.length > 1 ? 's' : ''} found
          </span>
        </div>
      )
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`Validate Zone: ${zone.name}`}
      size="lg"
    >
      <div className="space-y-6">
        {/* Zone Info */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                {zone.name}
              </h3>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant={zone.zone_type === 'master' ? 'success' : 'info'}>
                  {zone.zone_type}
                </Badge>
                <Badge variant={zone.is_active ? 'success' : 'default'}>
                  {zone.is_active ? 'Active' : 'Inactive'}
                </Badge>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Serial: {zone.serial}
                </span>
              </div>
            </div>
            <DocumentCheckIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        {/* Validation Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Validation Type
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <button
              type="button"
              onClick={() => setValidationType('full')}
              className={`p-3 text-left border rounded-lg transition-colors ${
                validationType === 'full'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="font-medium">Full Validation</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Complete zone and records check
              </div>
            </button>
            
            <button
              type="button"
              onClick={() => setValidationType('configuration')}
              className={`p-3 text-left border rounded-lg transition-colors ${
                validationType === 'configuration'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="font-medium">Configuration Only</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Zone settings and SOA validation
              </div>
            </button>
            
            <button
              type="button"
              onClick={() => setValidationType('records')}
              className={`p-3 text-left border rounded-lg transition-colors ${
                validationType === 'records'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="font-medium">Records Only</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                DNS records format validation
              </div>
            </button>
          </div>
        </div>

        {/* Validation Results */}
        {validationResult && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center space-x-3 mb-4">
              {getValidationIcon()}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Validation Results
                </h3>
                {getValidationStatus()}
              </div>
            </div>

            {/* Errors */}
            {validationResult.errors.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">
                  Errors ({validationResult.errors.length})
                </h4>
                <div className="space-y-2">
                  {validationResult.errors.map((error, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
                    >
                      <XCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-red-700 dark:text-red-300">
                        {error}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Warnings */}
            {validationResult.warnings.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-yellow-700 dark:text-yellow-300 mb-2">
                  Warnings ({validationResult.warnings.length})
                </h4>
                <div className="space-y-2">
                  {validationResult.warnings.map((warning, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg"
                    >
                      <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-yellow-700 dark:text-yellow-300">
                        {warning}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Success message */}
            {validationResult.valid && validationResult.errors.length === 0 && validationResult.warnings.length === 0 && (
              <div className="flex items-center space-x-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                <span className="text-sm text-green-700 dark:text-green-300">
                  Zone validation completed successfully with no issues found.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            Close
          </Button>
          <Button
            onClick={handleValidation}
            loading={isLoading}
            className="flex items-center space-x-2"
          >
            <ArrowPathIcon className="h-4 w-4" />
            <span>Run Validation</span>
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ZoneValidationModal