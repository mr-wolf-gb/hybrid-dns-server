import React, { useState, useEffect } from 'react'
import { useForm, useFieldArray, Controller } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { zonesService } from '@/services/api'
import { Zone, ZoneFormData, ZoneTemplate } from '@/types'
import { Modal, Button, Input, Select } from '@/components/ui'
import { toast } from 'react-toastify'
import { PlusIcon, TrashIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline'

interface ZoneModalProps {
  zone?: Zone | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

// Predefined zone templates
const ZONE_TEMPLATES: ZoneTemplate[] = [
  {
    id: 'internal-domain',
    name: 'Internal Domain',
    description: 'Standard internal domain configuration',
    zone_type: 'master',
    defaults: {
      email: 'admin@company.local',
      refresh: 10800,
      retry: 3600,
      expire: 604800,
      minimum: 86400,
    }
  },
  {
    id: 'public-domain',
    name: 'Public Domain',
    description: 'Public-facing domain with shorter TTLs',
    zone_type: 'master',
    defaults: {
      email: 'hostmaster@example.com',
      refresh: 7200,
      retry: 1800,
      expire: 1209600,
      minimum: 3600,
    }
  },
  {
    id: 'slave-zone',
    name: 'Secondary Zone',
    description: 'Secondary zone from another DNS server',
    zone_type: 'slave',
    defaults: {
      email: 'admin@company.local',
      refresh: 10800,
      retry: 3600,
      expire: 604800,
      minimum: 86400,
    }
  },
  {
    id: 'forward-zone',
    name: 'Forward Zone',
    description: 'Forward queries to external DNS servers',
    zone_type: 'forward',
    defaults: {
      email: 'admin@company.local',
      forwarders: [{ value: '8.8.8.8' }, { value: '8.8.4.4' }],
    }
  }
]

const ZoneModal: React.FC<ZoneModalProps> = ({ zone, isOpen, onClose, onSuccess }) => {
  const isEditing = !!zone
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    reset,
    setValue,
    control,
    trigger,
  } = useForm<ZoneFormData>({
    mode: 'onChange',
    defaultValues: zone ? {
      name: zone.name,
      zone_type: zone.zone_type,
      master_servers: (zone.master_servers || []).map(server => ({ value: server })),
      forwarders: (zone.forwarders || []).map(forwarder => ({ value: forwarder })),
      email: zone.email,
      description: zone.description || '',
      refresh: zone.refresh,
      retry: zone.retry,
      expire: zone.expire,
      minimum: zone.minimum,
    } : {
      name: '',
      zone_type: 'master',
      master_servers: [],
      forwarders: [],
      email: '',
      description: '',
      refresh: 10800,
      retry: 3600,
      expire: 604800,
      minimum: 86400,
    },
  })

  const { fields: masterServerFields, append: appendMasterServer, remove: removeMasterServer } = useFieldArray({
    control,
    name: 'master_servers'
  })

  const { fields: forwarderFields, append: appendForwarder, remove: removeForwarder } = useFieldArray({
    control,
    name: 'forwarders'
  })

  const watchZoneType = watch('zone_type')

  // Apply template when selected
  const applyTemplate = (templateId: string) => {
    const template = ZONE_TEMPLATES.find(t => t.id === templateId)
    if (!template) return

    // Set zone type
    setValue('zone_type', template.zone_type)

    // Apply defaults
    Object.entries(template.defaults).forEach(([key, value]) => {
      if (key === 'master_servers' && Array.isArray(value)) {
        // Clear existing and add new master servers
        while (masterServerFields.length > 0) {
          removeMasterServer(0)
        }
        value.forEach(server => appendMasterServer(typeof server === 'string' ? { value: server } : server))
      } else if (key === 'forwarders' && Array.isArray(value)) {
        // Clear existing and add new forwarders
        while (forwarderFields.length > 0) {
          removeForwarder(0)
        }
        value.forEach(forwarder => appendForwarder(typeof forwarder === 'string' ? { value: forwarder } : forwarder))
      } else {
        setValue(key as keyof ZoneFormData, value as any)
      }
    })

    // Trigger validation
    trigger()
    setSelectedTemplate('')
  }

  // Domain name validation
  const validateDomainName = (value: string) => {
    if (!value) return 'Zone name is required'

    // Remove leading/trailing whitespace
    const trimmedValue = value.trim()
    if (trimmedValue !== value) {
      return 'Domain name cannot have leading or trailing spaces'
    }

    // Check length
    if (trimmedValue.length > 253) {
      return 'Domain name cannot exceed 253 characters'
    }

    // Basic domain name regex - allows internal domains like .local
    const domainRegex = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/
    if (!domainRegex.test(trimmedValue)) {
      return 'Invalid domain format. Use letters, numbers, dots, and hyphens only (e.g., example.com or internal.local)'
    }

    // Check for valid structure
    const parts = trimmedValue.split('.')
    if (parts.length < 2) {
      return 'Domain must have at least two parts (e.g., example.com or host.local)'
    }

    // Check each part
    for (const part of parts) {
      if (part.length === 0) {
        return 'Domain parts cannot be empty'
      }
      if (part.length > 63) {
        return 'Each domain part cannot exceed 63 characters'
      }
      if (part.startsWith('-') || part.endsWith('-')) {
        return 'Domain parts cannot start or end with hyphens'
      }
    }

    return true
  }

  // Email validation - standard email format only
  const validateEmail = (value: string) => {
    if (!value) return 'Email is required'

    // Standard email format validation
    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/

    if (!emailRegex.test(value)) {
      return 'Please enter a valid email address (e.g., admin@example.com)'
    }

    // Check domain length
    if (value.includes('@') && value.split('@')[1]) {
      const domain = value.split('@')[1]
      if (domain.length < 3) {
        return 'Email domain must be at least 3 characters long'
      }
    }

    return true
  }

  // Note: Email is validated in standard format but converted to DNS format before submission

  // IP address validation
  const validateIPAddress = (value: string) => {
    if (!value) return 'IP address is required'

    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
    if (!ipRegex.test(value)) {
      return 'Invalid IP address format'
    }

    return true
  }

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
    // Convert email from standard format to DNS format
    const convertEmailToDNSFormat = (email: string) => {
      if (email.includes('@')) {
        return email.replace('@', '.')
      }
      return email
    }

    // Clean up empty arrays and convert email format
    const cleanedData = {
      ...data,
      email: convertEmailToDNSFormat(data.email),
      master_servers: data.master_servers?.map(item => item.value).filter(server => server.trim() !== '') || [],
      forwarders: data.forwarders?.map(item => item.value).filter(forwarder => forwarder.trim() !== '') || [],
    } as any

    if (isEditing) {
      updateMutation.mutate(cleanedData)
    } else {
      createMutation.mutate(cleanedData)
    }
  }

  const handleClose = () => {
    reset()
    setSelectedTemplate('')
    setShowAdvanced(false)
    onClose()
  }

  // Note: Email is stored and displayed in standard format

  // Reset form when zone changes
  useEffect(() => {
    if (zone && isOpen) {
      reset({
        name: zone.name,
        zone_type: zone.zone_type,
        master_servers: (zone.master_servers || []).map(server => ({ value: server })),
        forwarders: (zone.forwarders || []).map(forwarder => ({ value: forwarder })),
        email: zone.email,
        description: zone.description || '',
        refresh: zone.refresh,
        retry: zone.retry,
        expire: zone.expire,
        minimum: zone.minimum,
      })
    }
  }, [zone, isOpen, reset])

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit DNS Zone' : 'Create DNS Zone'}
      size="xl"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Template Selection */}
        {!isEditing && (
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
            <div className="flex items-center space-x-3">
              <DocumentDuplicateIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div className="flex-1">
                <Select
                  label="Use Template (Optional)"
                  placeholder="Select a zone template..."
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  options={[
                    { value: '', label: 'No template' },
                    ...ZONE_TEMPLATES.map(template => ({
                      value: template.id,
                      label: `${template.name} - ${template.description}`
                    }))
                  ]}
                />
              </div>
              {selectedTemplate && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyTemplate(selectedTemplate)}
                >
                  Apply
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Basic Zone Information */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Input
              label="Zone Name"
              placeholder="example.com"
              {...register('name', { validate: validateDomainName })}
              error={errors.name?.message}
              helperText="Enter the domain name for this zone (e.g., example.com)"
              disabled={isEditing}
            />
          </div>

          <Select
            label="Zone Type"
            options={[
              { value: 'master', label: 'Master (Primary)' },
              { value: 'slave', label: 'Slave (Secondary)' },
              { value: 'forward', label: 'Forward' },
            ]}
            {...register('zone_type', { required: 'Zone type is required' })}
            error={errors.zone_type?.message}
            disabled={isEditing}
          />

          <Input
            label="Administrator Email"
            placeholder="admin@example.com"
            {...register('email', { validate: validateEmail })}
            error={errors.email?.message}
            helperText="Email address of the zone administrator (standard format: admin@example.com)"
          />

          <div className="sm:col-span-2">
            <Input
              label="Description (Optional)"
              placeholder="Brief description of this zone"
              {...register('description')}
              error={errors.description?.message}
              helperText="Optional description for documentation purposes"
            />
          </div>
        </div>

        {/* Zone Type Specific Fields */}
        {watchZoneType === 'slave' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              Master Servers
            </h3>

            <div className="space-y-3">
              {masterServerFields.map((field, index) => (
                <div key={field.id} className="flex items-end space-x-3">
                  <div className="flex-1">
                    <Controller
                      name={`master_servers.${index}.value`}
                      control={control}
                      rules={{ validate: validateIPAddress }}
                      render={({ field, fieldState }) => (
                        <Input
                          {...field}
                          label={index === 0 ? "Master Server IP" : ""}
                          placeholder="192.168.1.10"
                          error={fieldState.error?.message}
                        />
                      )}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeMasterServer(index)}
                    className="mb-1"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => appendMasterServer({ value: '' })}
                className="flex items-center space-x-2"
              >
                <PlusIcon className="h-4 w-4" />
                <span>Add Master Server</span>
              </Button>
            </div>
          </div>
        )}

        {watchZoneType === 'forward' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              Forwarder Servers
            </h3>

            <div className="space-y-3">
              {forwarderFields.map((field, index) => (
                <div key={field.id} className="flex items-end space-x-3">
                  <div className="flex-1">
                    <Controller
                      name={`forwarders.${index}.value`}
                      control={control}
                      rules={{ validate: validateIPAddress }}
                      render={({ field, fieldState }) => (
                        <Input
                          {...field}
                          label={index === 0 ? "Forwarder IP" : ""}
                          placeholder="8.8.8.8"
                          error={fieldState.error?.message}
                        />
                      )}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeForwarder(index)}
                    className="mb-1"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => appendForwarder({ value: '' })}
                className="flex items-center space-x-2"
              >
                <PlusIcon className="h-4 w-4" />
                <span>Add Forwarder</span>
              </Button>
            </div>
          </div>
        )}

        {/* SOA Settings for Master Zones */}
        {watchZoneType === 'master' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                SOA Record Settings
              </h3>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <Input
                label="Refresh Interval"
                type="number"
                placeholder="10800"
                {...register('refresh', {
                  required: 'Refresh interval is required',
                  min: { value: 300, message: 'Refresh must be at least 300 seconds (5 minutes)' },
                  max: { value: 86400, message: 'Refresh cannot exceed 86400 seconds (24 hours)' },
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
                  min: { value: 300, message: 'Retry must be at least 300 seconds (5 minutes)' },
                  max: { value: 86400, message: 'Retry cannot exceed 86400 seconds (24 hours)' },
                })}
                error={errors.retry?.message}
                helperText="How often to retry failed transfers (seconds)"
              />

              {showAdvanced && (
                <>
                  <Input
                    label="Expire Time"
                    type="number"
                    placeholder="604800"
                    {...register('expire', {
                      required: 'Expire time is required',
                      min: { value: 86400, message: 'Expire must be at least 86400 seconds (1 day)' },
                      max: { value: 2419200, message: 'Expire cannot exceed 2419200 seconds (28 days)' },
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
                      min: { value: 300, message: 'Minimum TTL must be at least 300 seconds (5 minutes)' },
                      max: { value: 86400, message: 'Minimum TTL cannot exceed 86400 seconds (24 hours)' },
                    })}
                    error={errors.minimum?.message}
                    helperText="Minimum TTL for negative caching (seconds)"
                  />
                </>
              )}
            </div>

            {showAdvanced && (
              <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  <strong>Note:</strong> These values affect DNS propagation and caching behavior.
                  Lower values mean faster updates but higher server load. Higher values mean
                  slower updates but better performance.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={createMutation.isPending || updateMutation.isPending}
            disabled={!isValid}
          >
            {isEditing ? 'Update Zone' : 'Create Zone'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default ZoneModal