import React from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { recordsService } from '@/services/api'
import { DNSRecord, RecordFormData } from '@/types'
import { Modal, Button, Input, Select } from '@/components/ui'
import { validateDNSRecord } from '@/utils'
import { toast } from 'react-toastify'

interface RecordModalProps {
  zoneId: number
  record?: DNSRecord | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const RecordModal: React.FC<RecordModalProps> = ({ 
  zoneId, 
  record, 
  isOpen, 
  onClose, 
  onSuccess 
}) => {
  const isEditing = !!record

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
    setValue,
  } = useForm<RecordFormData>({
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

  const watchType = watch('type')

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

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit DNS Record' : 'Create DNS Record'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <Input
            label="Record Name"
            placeholder="www"
            {...register('name', {
              required: 'Record name is required',
            })}
            error={errors.name?.message}
            helperText="Name or subdomain (use @ for root domain)"
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
                required: 'Record value is required',
                validate: (value) => {
                  if (!validateDNSRecord(watchType, value)) {
                    return `Invalid ${watchType} record format`
                  }
                  return true
                },
              })}
              error={errors.value?.message}
              helperText={getHelperTextForType(watchType)}
            />
          </div>

          <Input
            label="TTL"
            type="number"
            placeholder="3600"
            {...register('ttl', {
              required: 'TTL is required',
              min: { value: 1, message: 'TTL must be at least 1 second' },
              max: { value: 2147483647, message: 'TTL is too large' },
            })}
            error={errors.ttl?.message}
            helperText="Time To Live in seconds"
          />

          {(watchType === 'MX' || watchType === 'SRV') && (
            <Input
              label="Priority"
              type="number"
              placeholder="10"
              {...register('priority', {
                required: `Priority is required for ${watchType} records`,
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
                  min: { value: 1, message: 'Port must be between 1 and 65535' },
                  max: { value: 65535, message: 'Port must be between 1 and 65535' },
                })}
                error={errors.port?.message}
                helperText="Service port number"
              />
            </>
          )}
        </div>

        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={createMutation.isPending || updateMutation.isPending}
          >
            {isEditing ? 'Update Record' : 'Create Record'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default RecordModal