import React, { useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import { forwardersService } from '@/services/api'
import { Forwarder, ForwarderFormData } from '@/types'
import { Modal, Button, Input, Select } from '@/components/ui'
import { isValidDomain, isValidIP } from '@/utils'
import { toast } from 'react-toastify'

interface ForwarderModalProps {
  forwarder?: Forwarder | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const ForwarderModal: React.FC<ForwarderModalProps> = ({ 
  forwarder, 
  isOpen, 
  onClose, 
  onSuccess 
}) => {
  const isEditing = !!forwarder

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ForwarderFormData>({
    defaultValues: forwarder ? {
      name: forwarder.name,
      domain: forwarder.domain,
      servers: forwarder.servers,
      type: forwarder.type,
      forward_policy: forwarder.forward_policy,
    } : {
      name: '',
      domain: '',
      servers: [''],
      type: 'public',
      forward_policy: 'first',
    },
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'servers',
  })

  // Create forwarder mutation
  const createMutation = useMutation({
    mutationFn: forwardersService.createForwarder,
    onSuccess: () => {
      toast.success('Forwarder created successfully')
      onSuccess()
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create forwarder')
    },
  })

  // Update forwarder mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<ForwarderFormData>) => 
      forwardersService.updateForwarder(forwarder!.id, data),
    onSuccess: () => {
      toast.success('Forwarder updated successfully')
      onSuccess()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update forwarder')
    },
  })

  const onSubmit = (data: ForwarderFormData) => {
    // Filter out empty servers
    const cleanData = {
      ...data,
      servers: data.servers.filter(server => server.trim() !== ''),
    }

    if (cleanData.servers.length === 0) {
      toast.error('At least one DNS server is required')
      return
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

  const addServer = () => {
    append('')
  }

  const removeServer = (index: number) => {
    if (fields.length > 1) {
      remove(index)
    }
  }

  const getDomainPlaceholder = (type: string): string => {
    switch (type) {
      case 'ad':
        return 'corp.local'
      case 'intranet':
        return 'intranet.company'
      case 'public':
        return 'google.com'
      default:
        return 'example.com'
    }
  }

  const getDomainHelperText = (type: string): string => {
    switch (type) {
      case 'ad':
        return 'Active Directory domain (e.g., corp.local, ad.company.com)'
      case 'intranet':
        return 'Internal intranet domain (e.g., intranet.company, internal.local)'
      case 'public':
        return 'Public domain or specific hostname to forward'
      default:
        return 'Domain to forward queries for'
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit DNS Forwarder' : 'Create DNS Forwarder'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <Input
            label="Forwarder Name"
            placeholder="AD Primary"
            {...register('name', {
              required: 'Name is required',
              minLength: { value: 2, message: 'Name must be at least 2 characters' },
            })}
            error={errors.name?.message}
            helperText="Descriptive name for this forwarder"
          />

          <Select
            label="Type"
            options={[
              { value: 'ad', label: 'Active Directory' },
              { value: 'intranet', label: 'Intranet' },
              { value: 'public', label: 'Public DNS' },
            ]}
            {...register('type', { required: 'Type is required' })}
            error={errors.type?.message}
          />

          <div className="sm:col-span-2">
            <Input
              label="Domain"
              placeholder={getDomainPlaceholder(register('type').value || 'public')}
              {...register('domain', {
                required: 'Domain is required',
                validate: (value) => {
                  if (!isValidDomain(value)) {
                    return 'Invalid domain format'
                  }
                  return true
                },
              })}
              error={errors.domain?.message}
              helperText={getDomainHelperText(register('type').value || 'public')}
            />
          </div>

          <Select
            label="Forward Policy"
            options={[
              { value: 'first', label: 'Forward First' },
              { value: 'only', label: 'Forward Only' },
            ]}
            {...register('forward_policy', { required: 'Forward policy is required' })}
            error={errors.forward_policy?.message}
            helperText="Forward first tries forwarders first, forward only uses only forwarders"
          />
        </div>

        {/* DNS Servers */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              DNS Servers
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addServer}
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Server
            </Button>
          </div>

          <div className="space-y-3">
            {fields.map((field, index) => (
              <div key={field.id} className="flex items-end space-x-2">
                <div className="flex-1">
                  <Input
                    placeholder="192.168.1.10"
                    {...register(`servers.${index}` as const, {
                      required: 'DNS server is required',
                      validate: (value) => {
                        if (!isValidIP(value)) {
                          return 'Invalid IP address format'
                        }
                        return true
                      },
                    })}
                    error={errors.servers?.[index]?.message}
                  />
                </div>
                
                {fields.length > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeServer(index)}
                    className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
          
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Add multiple DNS servers for redundancy. Queries will be load-balanced across healthy servers.
          </p>
        </div>

        {/* Examples */}
        <div className="bg-blue-50 dark:bg-blue-900/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
            Examples:
          </h4>
          <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
            <li>• <strong>Active Directory:</strong> corp.local → 192.168.1.10, 192.168.1.11</li>
            <li>• <strong>Intranet:</strong> intranet.company → 10.10.10.5, 10.10.10.6</li>
            <li>• <strong>Public DNS:</strong> * → 1.1.1.1, 8.8.8.8, 9.9.9.9</li>
          </ul>
        </div>

        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={createMutation.isPending || updateMutation.isPending}
          >
            {isEditing ? 'Update Forwarder' : 'Create Forwarder'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default ForwarderModal