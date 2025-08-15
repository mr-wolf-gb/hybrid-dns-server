import React from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { rpzService } from '@/services/api'
import { RPZRule, RPZRuleFormData } from '@/types'
import { Modal, Button, Input, Select } from '@/components/ui'
import { isValidDomain } from '@/utils'
import { toast } from 'react-toastify'

interface RPZRuleModalProps {
  rule?: RPZRule | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const RPZRuleModal: React.FC<RPZRuleModalProps> = ({ rule, isOpen, onClose, onSuccess }) => {
  const isEditing = !!rule

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
  } = useForm<RPZRuleFormData>({
    defaultValues: rule ? {
      zone: rule.zone,
      domain: rule.domain,
      action: rule.action,
      category: rule.category,
      redirect_target: rule.redirect_target || '',
    } : {
      zone: 'rpz.malware',
      domain: '',
      action: 'block',
      category: 'malware',
      redirect_target: '',
    },
  })

  const watchAction = watch('action')

  // Create rule mutation
  const createMutation = useMutation({
    mutationFn: rpzService.createRule,
    onSuccess: () => {
      toast.success('RPZ rule created successfully')
      onSuccess()
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create rule')
    },
  })

  // Update rule mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<RPZRuleFormData>) => rpzService.updateRule(rule!.id, data),
    onSuccess: () => {
      toast.success('RPZ rule updated successfully')
      onSuccess()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update rule')
    },
  })

  const onSubmit = (data: RPZRuleFormData) => {
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
      title={isEditing ? 'Edit RPZ Rule' : 'Create RPZ Rule'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <Select
            label="RPZ Zone"
            options={[
              { value: 'rpz.malware', label: 'Malware Protection' },
              { value: 'rpz.phishing', label: 'Phishing Protection' },
              { value: 'rpz.social-media', label: 'Social Media Blocking' },
              { value: 'rpz.adult', label: 'Adult Content Blocking' },
              { value: 'rpz.gambling', label: 'Gambling Blocking' },
              { value: 'rpz.custom-block', label: 'Custom Block List' },
              { value: 'rpz.custom-allow', label: 'Custom Allow List' },
            ]}
            {...register('zone', { required: 'RPZ zone is required' })}
            error={errors.zone?.message}
          />

          <Select
            label="Category"
            options={[
              { value: 'malware', label: 'Malware' },
              { value: 'phishing', label: 'Phishing' },
              { value: 'social_media', label: 'Social Media' },
              { value: 'adult', label: 'Adult Content' },
              { value: 'gambling', label: 'Gambling' },
              { value: 'custom', label: 'Custom' },
            ]}
            {...register('category', { required: 'Category is required' })}
            error={errors.category?.message}
          />

          <div className="sm:col-span-2">
            <Input
              label="Domain"
              placeholder="example.com or *.example.com"
              {...register('domain', {
                required: 'Domain is required',
                validate: (value) => {
                  // Allow wildcards for RPZ rules
                  const cleanDomain = value.startsWith('*.') ? value.substring(2) : value
                  if (!isValidDomain(cleanDomain)) {
                    return 'Invalid domain format'
                  }
                  return true
                },
              })}
              error={errors.domain?.message}
              helperText="Use wildcards like *.example.com to match subdomains"
            />
          </div>

          <Select
            label="Action"
            options={[
              { value: 'block', label: 'Block (Drop)' },
              { value: 'redirect', label: 'Redirect' },
              { value: 'passthru', label: 'Allow (Pass Through)' },
            ]}
            {...register('action', { required: 'Action is required' })}
            error={errors.action?.message}
          />

          {watchAction === 'redirect' && (
            <Input
              label="Redirect Target"
              placeholder="blocked.example.com"
              {...register('redirect_target', {
                required: watchAction === 'redirect' ? 'Redirect target is required' : false,
                validate: (value) => {
                  if (watchAction === 'redirect' && value && !isValidDomain(value)) {
                    return 'Invalid redirect target domain'
                  }
                  return true
                },
              })}
              error={errors.redirect_target?.message}
              helperText="Domain to redirect blocked requests to"
            />
          )}
        </div>

        {/* Information box */}
        <div className="bg-blue-50 dark:bg-blue-900/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
            RPZ Rule Information:
          </h4>
          <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
            <li>• <strong>Block:</strong> Drop DNS queries for the domain (returns NXDOMAIN)</li>
            <li>• <strong>Redirect:</strong> Redirect queries to a different domain or IP</li>
            <li>• <strong>Allow:</strong> Allow queries to pass through (bypass other RPZ rules)</li>
            <li>• Use wildcards (*.example.com) to match all subdomains</li>
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
            {isEditing ? 'Update Rule' : 'Create Rule'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default RPZRuleModal