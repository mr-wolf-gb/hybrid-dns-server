import React, { useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { useMutation, useQuery } from '@tanstack/react-query'
import { 
  PlusIcon, 
  TrashIcon, 
  BookmarkIcon,
  ServerIcon,
  GlobeAltIcon,
  HeartIcon,
  AdjustmentsHorizontalIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { forwardersService } from '@/services/api'
import { Forwarder, ForwarderFormData, ForwarderTemplate } from '@/types'
import { Modal, Button, Input, Select, Card, Badge } from '@/components/ui'
import { isValidDomain, isValidIP, isValidPort } from '@/utils'
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
  const [activeTab, setActiveTab] = useState<'basic' | 'servers' | 'domains' | 'health' | 'advanced'>('basic')
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')

  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    setValue,
    getValues,
  } = useForm<ForwarderFormData>({
    defaultValues: forwarder ? {
      name: forwarder.name,
      domain: forwarder.domains?.[0] || forwarder.domain || '',
      servers: Array.isArray(forwarder.servers) 
        ? forwarder.servers.map(server => 
            typeof server === 'string' 
              ? server 
              : `${server.ip}${server.port && server.port !== 53 ? `:${server.port}` : ''}`
          )
        : [],
      type: (forwarder.forwarder_type === 'active_directory' ? 'ad' : forwarder.forwarder_type) || forwarder.type || 'public',
      forward_policy: forwarder.forward_policy || 'first',
      domains: forwarder.domains?.slice(1) || [],
      health_check_enabled: forwarder.health_check_enabled ?? true,
      health_check_interval: forwarder.health_check_interval || 300,
      health_check_timeout: forwarder.health_check_timeout || 5,
      health_check_retries: forwarder.health_check_retries || 3,
      priority: forwarder.priority || 10,
      weight: forwarder.weight || 100,
      description: forwarder.description || '',
    } : {
      name: '',
      domain: '',
      servers: [''],
      type: 'public',
      forward_policy: 'first',
      domains: [],
      health_check_enabled: true,
      health_check_interval: 300,
      health_check_timeout: 5,
      health_check_retries: 3,
      priority: 10,
      weight: 100,
      description: '',
    },
  })

  const { fields: serverFields, append: appendServer, remove: removeServer } = useFieldArray({
    control,
    name: 'servers',
  } as any)

  const { fields: domainFields, append: appendDomain, remove: removeDomain } = useFieldArray({
    control,
    name: 'domains',
  } as any)

  // Fetch templates
  const { data: templates } = useQuery({
    queryKey: ['forwarder-templates'],
    queryFn: () => forwardersService.getTemplates(),
  })

  // Create template mutation
  const createTemplateMutation = useMutation({
    mutationFn: forwardersService.createTemplate,
    onSuccess: () => {
      toast.success('Template saved successfully')
      setShowSaveTemplate(false)
      setTemplateName('')
      setTemplateDescription('')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to save template')
    },
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
    setActiveTab('basic')
    setSelectedTemplate('')
    onClose()
  }

  const addServer = () => {
    appendServer('')
  }

  const removeServerField = (index: number) => {
    if (serverFields.length > 1) {
      removeServer(index)
    }
  }

  const addDomain = () => {
    appendDomain('')
  }

  const removeDomainField = (index: number) => {
    removeDomain(index)
  }

  const applyTemplate = (template: ForwarderTemplate) => {
    const defaults = template.defaults
    Object.entries(defaults).forEach(([key, value]) => {
      if (value !== undefined) {
        setValue(key as keyof ForwarderFormData, value as any)
      }
    })
    
    // Set servers if provided in template
    if (defaults.servers && defaults.servers.length > 0) {
      // Clear existing servers
      while (serverFields.length > 0) {
        removeServer(0)
      }
      // Add template servers
      defaults.servers.forEach(server => appendServer(server))
    }

    // Set domains if provided in template
    if (defaults.domains && defaults.domains.length > 0) {
      // Clear existing domains
      while (domainFields.length > 0) {
        removeDomain(0)
      }
      // Add template domains
      defaults.domains.forEach(domain => appendDomain(domain))
    }

    setSelectedTemplate(template.id)
    toast.success(`Applied template: ${template.name}`)
  }

  const saveAsTemplate = () => {
    const formData = getValues()
    
    const templateData = {
      name: templateName,
      description: templateDescription || `Template for ${formData.type} forwarders`,
      type: formData.type,
      defaults: {
        ...formData,
        name: '', // Don't include specific name in template
      },
    }

    createTemplateMutation.mutate(templateData)
  }

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'basic':
        return <InformationCircleIcon className="h-4 w-4" />
      case 'servers':
        return <ServerIcon className="h-4 w-4" />
      case 'domains':
        return <GlobeAltIcon className="h-4 w-4" />
      case 'health':
        return <HeartIcon className="h-4 w-4" />
      case 'advanced':
        return <AdjustmentsHorizontalIcon className="h-4 w-4" />
      default:
        return null
    }
  }

  const validateServerConfig = (server: string) => {
    if (!server.trim()) return 'Server is required'
    
    // Check for IP:port format
    const parts = server.split(':')
    const ip = parts[0]
    const port = parts[1]
    
    if (!isValidIP(ip)) {
      return 'Invalid IP address format'
    }
    
    if (port && !isValidPort(port)) {
      return 'Invalid port number (1-65535)'
    }
    
    return true
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
      size="xl"
    >
      <div className="space-y-6">
        {/* Template Selection */}
        {!isEditing && templates && templates.data && templates.data.length > 0 && (
          <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <BookmarkIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  Quick Start Templates
                </h3>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {templates.data.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => applyTemplate(template)}
                  className={`p-3 text-left rounded-lg border transition-colors ${
                    selectedTemplate === template.id
                      ? 'border-blue-500 bg-blue-100 dark:bg-blue-900/50'
                      : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600'
                  }`}
                >
                  <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                    {template.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {template.description}
                  </div>
                  <Badge 
                    size="sm" 
                    className="mt-2"
                    variant={template.type === 'ad' ? 'info' : template.type === 'intranet' ? 'warning' : 'success'}
                  >
                    {template.type.toUpperCase()}
                  </Badge>
                </button>
              ))}
            </div>
          </Card>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'basic', label: 'Basic Info' },
              { id: 'servers', label: 'DNS Servers' },
              { id: 'domains', label: 'Domain List' },
              { id: 'health', label: 'Health Checks' },
              { id: 'advanced', label: 'Advanced' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {getTabIcon(tab.id)}
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Info Tab */}
          {activeTab === 'basic' && (
            <div className="space-y-6">
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
                    label="Primary Domain"
                    placeholder={getDomainPlaceholder(watch('type') || 'public')}
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
                    helperText={getDomainHelperText(watch('type') || 'public')}
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

                <div className="sm:col-span-2">
                  <Input
                    label="Description"
                    placeholder="Optional description for this forwarder"
                    {...register('description')}
                    error={errors.description?.message}
                    helperText="Optional description to help identify this forwarder"
                  />
                </div>
              </div>

              {/* Policy Explanation */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Forward Policy Explanation
                </h4>
                <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-start space-x-2">
                    <CheckCircleIcon className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>Forward First:</strong> Try forwarders first, then fall back to recursion if they fail
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>Forward Only:</strong> Only use forwarders, never perform recursion
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* DNS Servers Tab */}
          {activeTab === 'servers' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                    DNS Server Configuration
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Configure the DNS servers that will handle forwarded queries
                  </p>
                </div>
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

              <div className="space-y-4">
                {serverFields.map((field, index) => (
                  <Card key={field.id} className="p-4">
                    <div className="flex items-start justify-between mb-4">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Server {index + 1}
                      </h4>
                      {serverFields.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeServerField(index)}
                          className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                      <div className="sm:col-span-2">
                        <Input
                          label="IP Address"
                          placeholder="192.168.1.10 or 192.168.1.10:53"
                          {...register(`servers.${index}` as const, {
                            required: 'DNS server is required',
                            validate: (value) => validateServerConfig(value),
                          })}
                          error={errors.servers?.[index]?.message}
                          helperText="IP address with optional port (default: 53)"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Status
                        </label>
                        <div className="flex items-center space-x-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">Unknown</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Server Configuration Tips */}
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
                  Server Configuration Tips
                </h4>
                <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                  <li>• Use IP addresses instead of hostnames to avoid circular dependencies</li>
                  <li>• Add multiple servers for redundancy and load balancing</li>
                  <li>• Specify custom ports using IP:port format (e.g., 192.168.1.10:5353)</li>
                  <li>• Order servers by preference - first server will be tried first</li>
                </ul>
              </div>
            </div>
          )}

          {/* Domain List Tab */}
          {activeTab === 'domains' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                    Additional Domains
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Specify additional domains that should use this forwarder
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addDomain}
                >
                  <PlusIcon className="h-4 w-4 mr-1" />
                  Add Domain
                </Button>
              </div>

              <div className="space-y-3">
                {domainFields.map((field, index) => (
                  <div key={field.id} className="flex items-end space-x-2">
                    <div className="flex-1">
                      <Input
                        label={`Domain ${index + 1}`}
                        placeholder="subdomain.example.com"
                        {...register(`domains.${index}` as const, {
                          validate: (value) => {
                            if (value && !isValidDomain(value)) {
                              return 'Invalid domain format'
                            }
                            return true
                          },
                        })}
                        error={errors.domains?.[index]?.message}
                      />
                    </div>
                    
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeDomainField(index)}
                      className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {domainFields.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <GlobeAltIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No additional domains configured</p>
                  <p className="text-sm">The primary domain will be used for all queries</p>
                </div>
              )}

              {/* Domain Examples */}
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <h4 className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                  Domain Examples
                </h4>
                <ul className="text-sm text-green-700 dark:text-green-300 space-y-1">
                  <li>• <strong>Wildcards:</strong> *.internal.company (matches all subdomains)</li>
                  <li>• <strong>Specific:</strong> mail.company.com, vpn.company.com</li>
                  <li>• <strong>Reverse DNS:</strong> 1.168.192.in-addr.arpa</li>
                </ul>
              </div>
            </div>
          )}

          {/* Health Check Tab */}
          {activeTab === 'health' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Health Check Configuration
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Configure how the system monitors the health of this forwarder
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="health_check_enabled"
                  {...register('health_check_enabled')}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="health_check_enabled" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Enable health monitoring
                </label>
              </div>

              {watch('health_check_enabled') && (
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                  <Input
                    label="Check Interval (seconds)"
                    type="number"
                    min="30"
                    max="3600"
                    {...register('health_check_interval', {
                      valueAsNumber: true,
                      min: { value: 30, message: 'Minimum interval is 30 seconds' },
                      max: { value: 3600, message: 'Maximum interval is 1 hour' },
                    })}
                    error={errors.health_check_interval?.message}
                    helperText="How often to check server health"
                  />

                  <Input
                    label="Timeout (seconds)"
                    type="number"
                    min="1"
                    max="30"
                    {...register('health_check_timeout', {
                      valueAsNumber: true,
                      min: { value: 1, message: 'Minimum timeout is 1 second' },
                      max: { value: 30, message: 'Maximum timeout is 30 seconds' },
                    })}
                    error={errors.health_check_timeout?.message}
                    helperText="Query timeout duration"
                  />

                  <Input
                    label="Max Retries"
                    type="number"
                    min="1"
                    max="10"
                    {...register('health_check_retries', {
                      valueAsNumber: true,
                      min: { value: 1, message: 'Minimum retries is 1' },
                      max: { value: 10, message: 'Maximum retries is 10' },
                    })}
                    error={errors.health_check_retries?.message}
                    helperText="Retries before marking unhealthy"
                  />
                </div>
              )}

              {/* Health Check Info */}
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                  Health Check Behavior
                </h4>
                <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                  <li>• Health checks use simple DNS queries to test server responsiveness</li>
                  <li>• Unhealthy servers are temporarily removed from rotation</li>
                  <li>• Servers are automatically re-enabled when they become healthy</li>
                  <li>• Disable health checks for servers that don't support test queries</li>
                </ul>
              </div>
            </div>
          )}

          {/* Advanced Tab */}
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Advanced Configuration
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Fine-tune forwarder behavior and performance settings
                </p>
              </div>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <Input
                  label="Priority"
                  type="number"
                  min="1"
                  max="100"
                  {...register('priority', {
                    valueAsNumber: true,
                    min: { value: 1, message: 'Minimum priority is 1' },
                    max: { value: 100, message: 'Maximum priority is 100' },
                  })}
                  error={errors.priority?.message}
                  helperText="Lower numbers = higher priority (1-100)"
                />

                <Input
                  label="Weight"
                  type="number"
                  min="1"
                  max="1000"
                  {...register('weight', {
                    valueAsNumber: true,
                    min: { value: 1, message: 'Minimum weight is 1' },
                    max: { value: 1000, message: 'Maximum weight is 1000' },
                  })}
                  error={errors.weight?.message}
                  helperText="Load balancing weight (1-1000)"
                />
              </div>

              {/* Advanced Settings Info */}
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <h4 className="text-sm font-medium text-purple-800 dark:text-purple-200 mb-2">
                  Advanced Settings Explanation
                </h4>
                <div className="space-y-2 text-sm text-purple-700 dark:text-purple-300">
                  <div>
                    <strong>Priority:</strong> When multiple forwarders match a domain, lower priority numbers are tried first
                  </div>
                  <div>
                    <strong>Weight:</strong> For forwarders with the same priority, weight determines load distribution
                  </div>
                </div>
              </div>

              {/* Save as Template */}
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Save as Template
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Save this configuration as a reusable template
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSaveTemplate(true)}
                  >
                    <BookmarkIcon className="h-4 w-4 mr-1" />
                    Save Template
                  </Button>
                </div>

                {showSaveTemplate && (
                  <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <Input
                      label="Template Name"
                      placeholder="My Custom Template"
                      value={templateName}
                      onChange={(e) => setTemplateName(e.target.value)}
                    />
                    <Input
                      label="Description"
                      placeholder="Template description"
                      value={templateDescription}
                      onChange={(e) => setTemplateDescription(e.target.value)}
                    />
                    <div className="flex space-x-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={saveAsTemplate}
                        loading={createTemplateMutation.isPending}
                        disabled={!templateName.trim()}
                      >
                        Save
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setShowSaveTemplate(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex justify-between items-center pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="flex space-x-2">
              {activeTab !== 'basic' && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    const tabs = ['basic', 'servers', 'domains', 'health', 'advanced']
                    const currentIndex = tabs.indexOf(activeTab)
                    if (currentIndex > 0) {
                      setActiveTab(tabs[currentIndex - 1] as any)
                    }
                  }}
                >
                  Previous
                </Button>
              )}
              {activeTab !== 'advanced' && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    const tabs = ['basic', 'servers', 'domains', 'health', 'advanced']
                    const currentIndex = tabs.indexOf(activeTab)
                    if (currentIndex < tabs.length - 1) {
                      setActiveTab(tabs[currentIndex + 1] as any)
                    }
                  }}
                >
                  Next
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
              >
                {isEditing ? 'Update Forwarder' : 'Create Forwarder'}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </Modal>
  )
}

export default ForwarderModal