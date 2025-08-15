import React from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { zonesService } from '@/services/api'
import { Zone, ZoneFormData } from '@/types'
import { Modal, Button, Input, Select } from '@/components/ui'
import { toast } from 'react-toastify'

interface ZoneModalProps {
  zone?: Zone | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const ZoneModal: React.FC<ZoneModalProps> = ({ zone, isOpen, onClose, onSuccess }) => {
  const isEditing = !!zone

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
  } = useForm<ZoneFormData>({
    defaultValues: zone ? {
      name: zone.name,
      type: zone.type,
      master_server: zone.master_server || '',
      ttl: zone.ttl,
      refresh: zone.refresh,
      retry: zone.retry,
      expire: zone.expire,
      minimum: zone.minimum,
    } : {
      name: '',
      type: 'master',
      master_server: '',
      ttl: 3600,
      refresh: 10800,
      retry: 3600,
      expire: 604800,
      minimum: 86400,
    },
  })

  const watchType = watch('type')

  // Create zone mutation
  const createMutation = useMutation({
    mutationFn: zonesService.createZone,
    onSuccess: () => {
      toast.success('Zone created successfully')
      onSuccess()
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create zone')
    },
  })

  // Update zone mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<ZoneFormData>) => zonesService.updateZone(zone!.id, data),
    onSuccess: () => {
      toast.success('Zone updated successfully')
      onSuccess()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update zone')
    },
  })

  const onSubmit = (data: ZoneFormData) => {
    if (isEditing) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data)
    }
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit DNS Zone' : 'Create DNS Zone'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Input
              label="Zone Name"
              placeholder="example.com"
              {...register('name', {
                required: 'Zone name is required',
                pattern: {
                  value: /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i,
                  message: 'Invalid domain name format',
                },
              })}
              error={errors.name?.message}
              helperText="Enter the domain name for this zone (e.g., example.com)"
            />
          </div>

          <Select
            label="Zone Type"
            options={[
              { value: 'master', label: 'Master (Primary)' },
              { value: 'slave', label: 'Slave (Secondary)' },
              { value: 'forward', label: 'Forward' },
            ]}
            {...register('type', { required: 'Zone type is required' })}
            error={errors.type?.message}
          />

          {watchType === 'slave' && (
            <Input
              label="Master Server"
              placeholder="192.168.1.10"
              {...register('master_server', {
                required: watchType === 'slave' ? 'Master server is required for slave zones' : false,
              })}
              error={errors.master_server?.message}
              helperText="IP address of the master DNS server"
            />
          )}

          <Input
            label="Default TTL"
            type="number"
            placeholder="3600"
            {...register('ttl', {
              required: 'TTL is required',
              min: { value: 1, message: 'TTL must be at least 1 second' },
              max: { value: 2147483647, message: 'TTL is too large' },
            })}
            error={errors.ttl?.message}
            helperText="Default Time To Live in seconds"
          />
        </div>

        {watchType === 'master' && (
          <>
            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                SOA Record Settings
              </h3>
              
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <Input
                  label="Refresh Interval"
                  type="number"
                  placeholder="10800"
                  {...register('refresh', {
                    required: 'Refresh interval is required',
                    min: { value: 1, message: 'Refresh must be at least 1 second' },
                  })}
                  error={errors.refresh?.message}
                  helperText="How often secondaries check for updates (seconds)"
                />

                <Input
                  label="Retry Interval"
                  type="number"
                  placeholder="3600"
                  {...register('retry', {
                    required: 'Retry interval is required',
                    min: { value: 1, message: 'Retry must be at least 1 second' },
                  })}
                  error={errors.retry?.message}
                  helperText="How often to retry failed transfers (seconds)"
                />

                <Input
                  label="Expire Time"
                  type="number"
                  placeholder="604800"
                  {...register('expire', {
                    required: 'Expire time is required',
                    min: { value: 1, message: 'Expire must be at least 1 second' },
                  })}
                  error={errors.expire?.message}
                  helperText="When to stop answering queries (seconds)"
                />

                <Input
                  label="Minimum TTL"
                  type="number"
                  placeholder="86400"
                  {...register('minimum', {
                    required: 'Minimum TTL is required',
                    min: { value: 1, message: 'Minimum TTL must be at least 1 second' },
                  })}
                  error={errors.minimum?.message}
                  helperText="Minimum TTL for negative caching (seconds)"
                />
              </div>
            </div>
          </>
        )}

        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={createMutation.isPending || updateMutation.isPending}
          >
            {isEditing ? 'Update Zone' : 'Create Zone'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default ZoneModal