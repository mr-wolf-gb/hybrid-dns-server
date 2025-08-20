import React, { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import {
  EyeIcon,
  DocumentDuplicateIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { recordsService } from '@/services/api'
import { DNSRecord, RecordFormData } from '@/types'
import { Modal, Button, Input, Select, Card } from '@/components/ui'
import { isValidIP, isValidDomain } from '@/utils'
import { toast } from 'react-toastify'
import RecordTemplates from './RecordTemplates'

interface RecordModalProps {
  zoneId: number
  record?: DNSRecord | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

// Record templates moved to RecordTemplates component

const RecordModal: React.FC<RecordModalProps> = ({ 
  zoneId, 
  record, 
  isOpen, 
  onClose, 
  onSuccess 
}) => {
  const isEditing = !!record
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
    setValue,
    trigger,
  } = useForm<RecordFormData>({
    mode: 'onChange',
    defaultValues: record ? {
      name: record.name,
      type: record.type,
      value: record.value,
      priority: record.priority,
      weight: record.weight,
      port: record.port,
      ttl: record.ttl,
    } : {
      name: '',
      type: 'A',
      value: '',
      priority: undefined,
      weight: undefined,
      port: undefined,
      ttl: 3600,
    },
  })

  const watchedValues = watch()
  const watchType = watch('type')
  const watchValue = watch('value')
  const watchName = watch('name')

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      if (record) {
        reset({
          name: record.name,
          type: record.type,
          value: record.value,
          priority: record.priority,
          weight: record.weight,
          port: record.port,
          ttl: record.ttl,
        })
      } else {
        reset({
          name: '',
          type: 'A',
          value: '',
          priority: undefined,
          weight: undefined,
          port: undefined,
          ttl: 3600,
        })
      }
      setSelectedTemplate('')
      // Reset preview state if needed
    }
  }, [isOpen, record, reset])

  // Clear type-specific fields when type changes
  useEffect(() => {
    if (watchType !== 'MX' && watchType !== 'SRV') {
      setValue('priority', undefined)
    }
    if (watchType !== 'SRV') {
      setValue('weight', undefined)
      setValue('port', undefined)
    }
    trigger()
  }, [watchType, setValue, trigger])

  // Create record mutation
  const createMutation = useMutation({
    mutationFn: (data: RecordFormData) => recordsService.createRecord(zoneId, data),
    onSuccess: () => {
      toast.success('DNS record created successfully')
      onSuccess()
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create record')
    },
  })

  // Update record mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<RecordFormData>) => 
      recordsService.updateRecord(zoneId, record!.id, data),
    onSuccess: () => {
      toast.success('DNS record updated successfully')
      onSuccess()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update record')
    },
  })

  // Apply template
  const applyTemplate = (template: Partial<RecordFormData>) => {
    if (template.name !== undefined) setValue('name', template.name)
    if (template.value !== undefined) setValue('value', template.value)
    if (template.ttl !== undefined) setValue('ttl', template.ttl)
    if (template.priority !== undefined) setValue('priority', template.priority)
    if (template.weight !== undefined) setValue('weight', template.weight)
    if (template.port !== undefined) setValue('port', template.port)
    setSelectedTemplate('')
    trigger()
  }

  // Enhanced validation functions
  const validateRecordName = (name: string): string | true => {
    if (!name.trim()) return 'Record name is required'
    if (name === '@') return true
    if (!/^[a-zA-Z0-9._-]+$/.test(name)) {
      return 'Name can only contain letters, numbers, dots, hyphens, and underscores'
    }
    if (name.length > 63) return 'Name cannot exceed 63 characters'
    return true
  }

  const validateRecordValue = (value: string, type: string): string | true => {
    if (!value.trim()) return 'Value is required'

    switch (type) {
      case 'A':
        if (!isValidIP(value) || !value.includes('.')) {
          return 'Must be a valid IPv4 address (e.g., 192.168.1.1)'
        }
        break
      case 'AAAA':
        if (!isValidIP(value) || !value.includes(':')) {
          return 'Must be a valid IPv6 address (e.g., 2001:db8::1)'
        }
        break
      case 'CNAME':
      case 'PTR':
      case 'NS':
        if (!isValidDomain(value) && value !== '@') {
          return 'Must be a valid domain name'
        }
        break
      case 'MX':
        if (!isValidDomain(value)) {
          return 'Must be a valid mail server domain'
        }
        break
      case 'TXT':
        if (value.length > 255) {
          return 'TXT record cannot exceed 255 characters'
        }
        break
      case 'SRV':
        if (!isValidDomain(value)) {
          return 'Must be a valid target domain'
        }
        break
    }
    return true
  }

  const validateTTL = (ttl: number): string | true => {
    if (ttl < 1) return 'TTL must be at least 1 second'
    if (ttl > 2147483647) return 'TTL is too large'
    if (ttl < 60) return 'Warning: TTL below 60 seconds may cause high DNS traffic'
    if (ttl > 86400) return 'Warning: TTL above 24 hours may delay updates'
    return true
  }

  // Get validation status for preview
  const getValidationStatus = () => {
    const nameValidation = validateRecordName(watchName)
    const valueValidation = validateRecordValue(watchValue, watchType)
    const ttlValidation = validateTTL(watchedValues.ttl)

    const hasErrors = nameValidation !== true || valueValidation !== true || 
                     (typeof ttlValidation === 'string' && ttlValidation.includes('must'))
    const hasWarnings = typeof ttlValidation === 'string' && ttlValidation.includes('Warning')

    return { hasErrors, hasWarnings, nameValidation, valueValidation, ttlValidation }
  }

  const onSubmit = (data: RecordFormData) => {
    // Clean up data based on record type
    const cleanData = { ...data }
    
    if (watchType !== 'MX' && watchType !== 'SRV') {
      cleanData.priority = undefined
    }
    
    if (watchType !== 'SRV') {
      cleanData.weight = undefined
      cleanData.port = undefined
    }

    if (isEditing) {
      updateMutation.mutate(cleanData)
    } else {
      createMutation.mutate(cleanData)
    }
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const getPlaceholderForType = (type: string): string => {
    switch (type) {
      case 'A':
        return '192.168.1.10'
      case 'AAAA':
        return '2001:db8::1'
      case 'CNAME':
        return 'target.example.com'
      case 'MX':
        return 'mail.example.com'
      case 'TXT':
        return 'Text content'
      case 'SRV':
        return 'target.example.com'
      case 'PTR':
        return 'hostname.example.com'
      case 'NS':
        return 'ns1.example.com'
      default:
        return 'Record value'
    }
  }

  const getHelperTextForType = (type: string): string => {
    switch (type) {
      case 'A':
        return 'IPv4 address'
      case 'AAAA':
        return 'IPv6 address'
      case 'CNAME':
        return 'Canonical name (alias target)'
      case 'MX':
        return 'Mail server hostname'
      case 'TXT':
        return 'Text record content'
      case 'SRV':
        return 'Service target hostname'
      case 'PTR':
        return 'Hostname for reverse DNS'
      case 'NS':
        return 'Name server hostname'
      default:
        return 'Record value'
    }
  }

  const validationStatus = getValidationStatus()

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit DNS Record' : 'Create DNS Record'}
      size="xl"
    >
      <div className="space-y-6">
        {/* Templates section */}
        {!isEditing && (
          <RecordTemplates
            recordType={watchType}
            onApplyTemplate={applyTemplate}
          />
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input
              label="Record Name"
              placeholder={watchType === 'PTR' ? '10' : 'www'}
              {...register('name', {
                validate: validateRecordName,
              })}
              error={errors.name?.message}
              helperText={
                watchType === 'PTR' 
                  ? "Last octet for reverse DNS (e.g., '10' for 192.168.1.10)"
                  : "Name or subdomain (use @ for root domain)"
              }
            />

            <Select
              label="Record Type"
              options={[
                { value: 'A', label: 'A - IPv4 Address' },
                { value: 'AAAA', label: 'AAAA - IPv6 Address' },
                { value: 'CNAME', label: 'CNAME - Canonical Name' },
                { value: 'MX', label: 'MX - Mail Exchange' },
                { value: 'TXT', label: 'TXT - Text' },
                { value: 'SRV', label: 'SRV - Service' },
                { value: 'PTR', label: 'PTR - Pointer' },
                { value: 'NS', label: 'NS - Name Server' },
              ]}
              {...register('type', { required: 'Record type is required' })}
              error={errors.type?.message}
            />

            <div className={watchType === 'SRV' ? 'sm:col-span-1' : 'sm:col-span-2'}>
              <Input
                label="Value"
                placeholder={getPlaceholderForType(watchType)}
                {...register('value', {
                  validate: (value) => validateRecordValue(value, watchType),
                })}
                error={errors.value?.message}
                helperText={getHelperTextForType(watchType)}
              />
            </div>

            <Input
              label="TTL (seconds)"
              type="number"
              placeholder="3600"
              {...register('ttl', {
                required: 'TTL is required',
                valueAsNumber: true,
                validate: validateTTL,
              })}
              error={errors.ttl?.message}
              helperText="Time To Live - how long DNS resolvers cache this record"
            />

            {(watchType === 'MX' || watchType === 'SRV') && (
              <Input
                label="Priority"
                type="number"
                placeholder="10"
                {...register('priority', {
                  required: `Priority is required for ${watchType} records`,
                  valueAsNumber: true,
                  min: { value: 0, message: 'Priority must be 0 or higher' },
                  max: { value: 65535, message: 'Priority must be 65535 or lower' },
                })}
                error={errors.priority?.message}
                helperText="Lower values have higher priority"
              />
            )}

            {watchType === 'SRV' && (
              <>
                <Input
                  label="Weight"
                  type="number"
                  placeholder="5"
                  {...register('weight', {
                    required: 'Weight is required for SRV records',
                    valueAsNumber: true,
                    min: { value: 0, message: 'Weight must be 0 or higher' },
                    max: { value: 65535, message: 'Weight must be 65535 or lower' },
                  })}
                  error={errors.weight?.message}
                  helperText="Relative weight for records with same priority"
                />

                <Input
                  label="Port"
                  type="number"
                  placeholder="80"
                  {...register('port', {
                    required: 'Port is required for SRV records',
                    valueAsNumber: true,
                    min: { value: 1, message: 'Port must be between 1 and 65535' },
                    max: { value: 65535, message: 'Port must be between 1 and 65535' },
                  })}
                  error={errors.port?.message}
                  helperText="Service port number"
                />
              </>
            )}
          </div>

          {/* Record Preview */}
          {(watchName || watchValue) && (
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center">
                  <EyeIcon className="h-4 w-4 mr-2" />
                  Record Preview
                </h3>
                <div className="flex items-center space-x-2">
                  {validationStatus.hasErrors && (
                    <XCircleIcon className="h-4 w-4 text-red-500" title="Has validation errors" />
                  )}
                  {validationStatus.hasWarnings && !validationStatus.hasErrors && (
                    <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500" title="Has warnings" />
                  )}
                  {!validationStatus.hasErrors && !validationStatus.hasWarnings && (
                    <CheckCircleIcon className="h-4 w-4 text-green-500" title="Valid record" />
                  )}
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 font-mono text-sm">
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                  <span>NAME</span>
                  <span>TYPE</span>
                  <span>VALUE</span>
                  <span>TTL</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <span className="text-blue-600 dark:text-blue-400">
                    {watchName || '@'}
                  </span>
                  <span className="text-purple-600 dark:text-purple-400">
                    {watchType}
                  </span>
                  <span className="text-green-600 dark:text-green-400 break-all">
                    {watchType === 'MX' && watchedValues.priority 
                      ? `${watchedValues.priority} ${watchValue}`
                      : watchType === 'SRV' && watchedValues.priority && watchedValues.weight && watchedValues.port
                      ? `${watchedValues.priority} ${watchedValues.weight} ${watchedValues.port} ${watchValue}`
                      : watchValue || '(empty)'}
                  </span>
                  <span className="text-orange-600 dark:text-orange-400">
                    {watchedValues.ttl}s
                  </span>
                </div>
              </div>

              {/* Validation messages */}
              {(validationStatus.hasErrors || validationStatus.hasWarnings) && (
                <div className="mt-3 space-y-1">
                  {validationStatus.nameValidation !== true && (
                    <div className="flex items-center text-sm text-red-600 dark:text-red-400">
                      <XCircleIcon className="h-3 w-3 mr-1" />
                      Name: {validationStatus.nameValidation}
                    </div>
                  )}
                  {validationStatus.valueValidation !== true && (
                    <div className="flex items-center text-sm text-red-600 dark:text-red-400">
                      <XCircleIcon className="h-3 w-3 mr-1" />
                      Value: {validationStatus.valueValidation}
                    </div>
                  )}
                  {typeof validationStatus.ttlValidation === 'string' && (
                    <div className={`flex items-center text-sm ${
                      validationStatus.ttlValidation.includes('Warning') 
                        ? 'text-yellow-600 dark:text-yellow-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {validationStatus.ttlValidation.includes('Warning') ? (
                        <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                      ) : (
                        <XCircleIcon className="h-3 w-3 mr-1" />
                      )}
                      TTL: {validationStatus.ttlValidation}
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}

          <div className="flex justify-between items-center pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-2">
              {watchValue && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `${watchName || '@'} ${watchedValues.ttl} IN ${watchType} ${
                        watchType === 'MX' && watchedValues.priority 
                          ? `${watchedValues.priority} ${watchValue}`
                          : watchType === 'SRV' && watchedValues.priority && watchedValues.weight && watchedValues.port
                          ? `${watchedValues.priority} ${watchedValues.weight} ${watchedValues.port} ${watchValue}`
                          : watchValue
                      }`
                    )
                    toast.success('Record copied to clipboard')
                  }}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <DocumentDuplicateIcon className="h-4 w-4 mr-1" />
                  Copy DNS Record
                </Button>
              )}
            </div>
            
            <div className="flex space-x-3">
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending}
                disabled={validationStatus.hasErrors}
              >
                {isEditing ? 'Update Record' : 'Create Record'}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </Modal>
  )
}

export default RecordModal