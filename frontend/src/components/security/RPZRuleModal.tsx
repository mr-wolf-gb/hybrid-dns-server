import React, { useState, useEffect } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  DocumentDuplicateIcon,
  PlusIcon,
  TrashIcon,
  CloudArrowUpIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XMarkIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { RPZRule, RPZRuleFormData } from '@/types'
import { Modal, Button, Input, Select, Card, Badge } from '@/components/ui'
import { isValidDomain, isValidIP } from '@/utils'
import { toast } from 'react-toastify'

interface RPZRuleModalProps {
  rule?: RPZRule | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  mode?: 'single' | 'bulk' | 'template'
}

interface RPZRuleTemplate {
  id: string
  name: string
  description: string
  category: string
  action: 'block' | 'redirect' | 'passthru'
  zone: string
  redirect_target?: string
  domains: string[]
}

interface BulkImportData {
  domains: string[]
  zone: string
  action: 'block' | 'redirect' | 'passthru'
  category: string
  redirect_target?: string
}

interface DomainValidationResult {
  domain: string
  valid: boolean
  error?: string
  suggestion?: string
}

const RPZRuleModal: React.FC<RPZRuleModalProps> = ({ 
  rule, 
  isOpen, 
  onClose, 
  onSuccess, 
  mode = 'single' 
}) => {
  const isEditing = !!rule
  const [currentMode, setCurrentMode] = useState<'single' | 'bulk' | 'template'>(mode)
  const [selectedTemplate, setSelectedTemplate] = useState<RPZRuleTemplate | null>(null)
  const [bulkDomains, setBulkDomains] = useState<string>('')
  const [domainValidation, setDomainValidation] = useState<DomainValidationResult[]>([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [importResults, setImportResults] = useState<{ success: number; failed: number; errors: string[] } | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
    setValue,
    control,
  } = useForm<RPZRuleFormData>({
    defaultValues: rule ? {
      rpz_zone: rule.rpz_zone,
      domain: rule.domain,
      action: rule.action,
      category: rule.category,
      redirect_target: rule.redirect_target || '',
    } : {
      rpz_zone: 'rpz.malware',
      domain: '',
      action: 'block',
      category: 'malware',
      redirect_target: '',
    },
  })

  const watchAction = watch('action')
  const watchZone = watch('rpz_zone')
  const watchCategory = watch('category')

  // Fetch rule templates
  const { data: templates } = useQuery({
    queryKey: ['rpz-templates'],
    queryFn: () => rpzService.getRuleTemplates(),
    enabled: isOpen,
  })

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

  // Bulk import mutation
  const bulkImportMutation = useMutation({
    mutationFn: (data: BulkImportData) => rpzService.bulkImportRules(data),
    onSuccess: (response) => {
      const { success, failed, errors } = response.data.data
      setImportResults({ success, failed, errors })
      toast.success(`Successfully imported ${success} rules${failed > 0 ? `, ${failed} failed` : ''}`)
      if (failed === 0) {
        onSuccess()
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to import rules')
    },
  })

  // Enhanced domain validation
  const validateDomain = (domain: string): DomainValidationResult => {
    const result: DomainValidationResult = { domain, valid: false }
    
    if (!domain.trim()) {
      result.error = 'Domain cannot be empty'
      return result
    }

    // Handle wildcard domains
    const cleanDomain = domain.startsWith('*.') ? domain.substring(2) : domain
    
    // Check for valid domain format
    if (!isValidDomain(cleanDomain)) {
      result.error = 'Invalid domain format'
      
      // Provide suggestions for common mistakes
      if (domain.includes(' ')) {
        result.suggestion = 'Remove spaces from domain'
      } else if (domain.startsWith('http://') || domain.startsWith('https://')) {
        result.suggestion = 'Remove protocol (http/https) from domain'
      } else if (domain.includes('/')) {
        result.suggestion = 'Remove path from domain'
      }
      
      return result
    }

    // Check for IP addresses (should use different validation)
    if (isValidIP(cleanDomain)) {
      result.error = 'Use IP address format for IP-based rules'
      return result
    }

    // Additional RPZ-specific validations
    if (domain.length > 253) {
      result.error = 'Domain name too long (max 253 characters)'
      return result
    }

    if (domain.includes('..')) {
      result.error = 'Domain cannot contain consecutive dots'
      return result
    }

    result.valid = true
    return result
  }

  // Validate bulk domains
  const validateBulkDomains = (domainsText: string): DomainValidationResult[] => {
    const domains = domainsText
      .split('\n')
      .map(d => d.trim())
      .filter(d => d.length > 0)
    
    return domains.map(validateDomain)
  }

  // Handle template selection
  const applyTemplate = (template: RPZRuleTemplate) => {
    setSelectedTemplate(template)
    setValue('rpz_zone', template.zone)
    setValue('action', template.action)
    setValue('category', template.category)
    if (template.redirect_target) {
      setValue('redirect_target', template.redirect_target)
    }
    
    if (currentMode === 'bulk' && template.domains.length > 0) {
      setBulkDomains(template.domains.join('\n'))
    } else if (template.domains.length > 0) {
      setValue('domain', template.domains[0])
    }
  }

  // Handle bulk import
  const handleBulkImport = () => {
    const validation = validateBulkDomains(bulkDomains)
    setDomainValidation(validation)
    
    const validDomains = validation.filter(v => v.valid).map(v => v.domain)
    const invalidDomains = validation.filter(v => !v.valid)
    
    if (invalidDomains.length > 0) {
      toast.error(`${invalidDomains.length} invalid domains found. Please fix them before importing.`)
      return
    }

    if (validDomains.length === 0) {
      toast.error('No valid domains to import')
      return
    }

    const formData = watch()
    const bulkData: BulkImportData = {
      domains: validDomains,
      zone: formData.rpz_zone,
      action: formData.action,
      category: formData.category,
      redirect_target: formData.redirect_target,
    }

    bulkImportMutation.mutate(bulkData)
  }

  const onSubmit = (data: RPZRuleFormData) => {
    if (currentMode === 'bulk') {
      handleBulkImport()
      return
    }

    if (isEditing) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data)
    }
  }

  const handleClose = () => {
    reset()
    setBulkDomains('')
    setDomainValidation([])
    setSelectedTemplate(null)
    setImportResults(null)
    setCurrentMode(mode)
    onClose()
  }

  // Update domain validation in real-time for bulk mode
  useEffect(() => {
    if (currentMode === 'bulk' && bulkDomains) {
      const validation = validateBulkDomains(bulkDomains)
      setDomainValidation(validation)
    }
  }, [bulkDomains, currentMode])

  const getActionDescription = (action: string) => {
    switch (action) {
      case 'block':
        return 'Completely block access to the domain (returns NXDOMAIN)'
      case 'redirect':
        return 'Redirect requests to a different domain or IP address'
      case 'passthru':
        return 'Allow access (bypass other RPZ rules for this domain)'
      default:
        return ''
    }
  }

  const getZoneDescription = (zone: string) => {
    switch (zone) {
      case 'rpz.malware':
        return 'Block known malware and malicious domains'
      case 'rpz.phishing':
        return 'Block phishing and fraudulent websites'
      case 'rpz.social-media':
        return 'Block social media platforms'
      case 'rpz.adult':
        return 'Block adult and inappropriate content'
      case 'rpz.gambling':
        return 'Block gambling and betting websites'
      case 'rpz.custom-block':
        return 'Custom domains to block'
      case 'rpz.custom-allow':
        return 'Custom domains to explicitly allow'
      default:
        return ''
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        isEditing 
          ? 'Edit RPZ Rule' 
          : currentMode === 'bulk' 
            ? 'Bulk Import RPZ Rules'
            : currentMode === 'template'
              ? 'Create Rule from Template'
              : 'Create RPZ Rule'
      }
      size="xl"
    >
      <div className="space-y-6">
        {/* Mode Selection */}
        {!isEditing && (
          <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setCurrentMode('single')}
              className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                currentMode === 'single'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              <DocumentTextIcon className="h-4 w-4 inline mr-2" />
              Single Rule
            </button>
            <button
              type="button"
              onClick={() => setCurrentMode('bulk')}
              className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                currentMode === 'bulk'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              <CloudArrowUpIcon className="h-4 w-4 inline mr-2" />
              Bulk Import
            </button>
            <button
              type="button"
              onClick={() => setCurrentMode('template')}
              className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                currentMode === 'template'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              <DocumentDuplicateIcon className="h-4 w-4 inline mr-2" />
              Templates
            </button>
          </div>
        )}

        {/* Template Selection */}
        {currentMode === 'template' && templates?.data && (
          <Card>
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                Rule Templates
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Choose a pre-configured template to quickly create rules
              </p>
            </div>
            <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
              {templates.data.map((template: RPZRuleTemplate) => (
                <div
                  key={template.id}
                  onClick={() => applyTemplate(template)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedTemplate?.id === template.id
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-gray-100">
                        {template.name}
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {template.description}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <Badge variant="info" size="sm">
                        {template.category}
                      </Badge>
                      <Badge variant={template.action === 'block' ? 'danger' : template.action === 'redirect' ? 'warning' : 'success'} size="sm">
                        {template.action}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {template.domains.length} domain{template.domains.length !== 1 ? 's' : ''} • Zone: {template.zone}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Import Results */}
        {importResults && (
          <Card className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20">
            <div className="p-4">
              <div className="flex items-center space-x-2">
                <CheckCircleIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
                <h3 className="font-medium text-green-800 dark:text-green-200">
                  Import Complete
                </h3>
              </div>
              <div className="mt-2 text-sm text-green-700 dark:text-green-300">
                <p>Successfully imported {importResults.success} rules</p>
                {importResults.failed > 0 && (
                  <p className="text-red-600 dark:text-red-400">
                    {importResults.failed} rules failed to import
                  </p>
                )}
                {importResults.errors.length > 0 && (
                  <div className="mt-2">
                    <p className="font-medium">Errors:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {importResults.errors.slice(0, 5).map((error, index) => (
                        <li key={index} className="text-xs">{error}</li>
                      ))}
                      {importResults.errors.length > 5 && (
                        <li className="text-xs">... and {importResults.errors.length - 5} more</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
              <div className="mt-3 flex space-x-2">
                <Button size="sm" onClick={handleClose}>
                  Close
                </Button>
                {importResults.failed > 0 && (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setImportResults(null)}
                  >
                    Try Again
                  </Button>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Main Form */}
        {!importResults && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {/* RPZ Zone Selection */}
              <div className="sm:col-span-2">
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
                  {...register('rpz_zone', { required: 'RPZ zone is required' })}
                  error={errors.rpz_zone?.message}
                  helperText={getZoneDescription(watchZone)}
                />
              </div>

              {/* Category and Action */}
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

              <Select
                label="Action"
                options={[
                  { value: 'block', label: 'Block (Drop)' },
                  { value: 'redirect', label: 'Redirect' },
                  { value: 'passthru', label: 'Allow (Pass Through)' },
                ]}
                {...register('action', { required: 'Action is required' })}
                error={errors.action?.message}
                helperText={getActionDescription(watchAction)}
              />

              {/* Domain Input - Single Mode */}
              {currentMode === 'single' && (
                <div className="sm:col-span-2">
                  <Input
                    label="Domain"
                    placeholder="example.com or *.example.com"
                    {...register('domain', {
                      required: currentMode === 'single' ? 'Domain is required' : false,
                      validate: (value) => {
                        if (currentMode !== 'single') return true
                        const validation = validateDomain(value)
                        return validation.valid || validation.error
                      },
                    })}
                    error={errors.domain?.message}
                    helperText="Use wildcards like *.example.com to match subdomains"
                  />
                </div>
              )}

              {/* Redirect Target */}
              {watchAction === 'redirect' && (
                <div className="sm:col-span-2">
                  <Input
                    label="Redirect Target"
                    placeholder="blocked.example.com or 127.0.0.1"
                    {...register('redirect_target', {
                      required: watchAction === 'redirect' ? 'Redirect target is required' : false,
                      validate: (value) => {
                        if (watchAction !== 'redirect' || !value) return true
                        if (!isValidDomain(value) && !isValidIP(value)) {
                          return 'Must be a valid domain or IP address'
                        }
                        return true
                      },
                    })}
                    error={errors.redirect_target?.message}
                    helperText="Domain or IP address to redirect blocked requests to"
                  />
                </div>
              )}
            </div>

            {/* Bulk Import Section */}
            {currentMode === 'bulk' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Domains to Import
                  </label>
                  <textarea
                    value={bulkDomains}
                    onChange={(e) => setBulkDomains(e.target.value)}
                    placeholder="Enter domains, one per line:&#10;example.com&#10;*.badsite.com&#10;malware.example.org"
                    className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100 font-mono text-sm"
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Enter one domain per line. Wildcards (*.example.com) are supported.
                  </p>
                </div>

                {/* Domain Validation Results */}
                {domainValidation.length > 0 && (
                  <Card>
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100">
                        Domain Validation Results
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {domainValidation.filter(v => v.valid).length} valid, {domainValidation.filter(v => !v.valid).length} invalid
                      </p>
                    </div>
                    <div className="p-4 max-h-48 overflow-y-auto">
                      <div className="space-y-2">
                        {domainValidation.map((validation, index) => (
                          <div
                            key={index}
                            className={`flex items-center justify-between p-2 rounded text-sm ${
                              validation.valid
                                ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
                                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
                            }`}
                          >
                            <div className="flex items-center space-x-2">
                              {validation.valid ? (
                                <CheckCircleIcon className="h-4 w-4 text-green-600 dark:text-green-400" />
                              ) : (
                                <XMarkIcon className="h-4 w-4 text-red-600 dark:text-red-400" />
                              )}
                              <span className="font-mono">{validation.domain}</span>
                            </div>
                            {validation.error && (
                              <div className="text-right">
                                <div className="text-xs">{validation.error}</div>
                                {validation.suggestion && (
                                  <div className="text-xs opacity-75">{validation.suggestion}</div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            )}

            {/* Advanced Options */}
            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center space-x-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
              >
                <Cog6ToothIcon className="h-4 w-4" />
                <span>Advanced Options</span>
              </button>

              {showAdvanced && (
                <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-4">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                          Enable logging for this rule
                        </span>
                      </label>
                    </div>
                    <div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                          Apply to all subdomains
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Information Box */}
            <div className="bg-blue-50 dark:bg-blue-900/50 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <InformationCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
                    RPZ Rule Information:
                  </h4>
                  <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                    <li>• <strong>Block:</strong> Drop DNS queries for the domain (returns NXDOMAIN)</li>
                    <li>• <strong>Redirect:</strong> Redirect queries to a different domain or IP</li>
                    <li>• <strong>Allow:</strong> Allow queries to pass through (bypass other RPZ rules)</li>
                    <li>• Use wildcards (*.example.com) to match all subdomains</li>
                    <li>• Rules are processed in order of priority within each zone</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending || bulkImportMutation.isPending}
              >
                {isEditing 
                  ? 'Update Rule' 
                  : currentMode === 'bulk' 
                    ? `Import ${domainValidation.filter(v => v.valid).length} Rules`
                    : 'Create Rule'
                }
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  )
}

export default RPZRuleModal