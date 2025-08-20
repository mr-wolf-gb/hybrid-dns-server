import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookmarkIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline'
import { forwardersService } from '@/services/api'
import { ForwarderTemplate } from '@/types'
import { Modal, Button, Input, Select, Card, Badge } from '@/components/ui'
import { toast } from 'react-toastify'

interface ForwarderTemplatesProps {
  isOpen: boolean
  onClose: () => void
  onTemplateSelect?: (template: ForwarderTemplate) => void
}

const ForwarderTemplates: React.FC<ForwarderTemplatesProps> = ({
  isOpen,
  onClose,
  onTemplateSelect,
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<ForwarderTemplate | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')
  const [templateType, setTemplateType] = useState<'ad' | 'intranet' | 'public'>('public')

  const queryClient = useQueryClient()

  // Fetch templates
  const { data: templates, isLoading } = useQuery({
    queryKey: ['forwarder-templates'],
    queryFn: () => forwardersService.getTemplates(),
  })

  // Create template mutation
  const createMutation = useMutation({
    mutationFn: forwardersService.createTemplate,
    onSuccess: () => {
      toast.success('Template created successfully')
      queryClient.invalidateQueries({ queryKey: ['forwarder-templates'] })
      resetForm()
      setIsEditModalOpen(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create template')
    },
  })

  // Update template mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ForwarderTemplate> }) =>
      forwardersService.updateTemplate(id, data),
    onSuccess: () => {
      toast.success('Template updated successfully')
      queryClient.invalidateQueries({ queryKey: ['forwarder-templates'] })
      resetForm()
      setIsEditModalOpen(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update template')
    },
  })

  // Delete template mutation
  const deleteMutation = useMutation({
    mutationFn: forwardersService.deleteTemplate,
    onSuccess: () => {
      toast.success('Template deleted successfully')
      queryClient.invalidateQueries({ queryKey: ['forwarder-templates'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete template')
    },
  })

  const resetForm = () => {
    setTemplateName('')
    setTemplateDescription('')
    setTemplateType('public')
    setSelectedTemplate(null)
  }

  const handleEdit = (template: ForwarderTemplate) => {
    setSelectedTemplate(template)
    setTemplateName(template.name)
    setTemplateDescription(template.description)
    setTemplateType(template.type)
    setIsEditModalOpen(true)
  }

  const handleDelete = (template: ForwarderTemplate) => {
    if (window.confirm(`Are you sure you want to delete the template "${template.name}"?`)) {
      deleteMutation.mutate(template.id)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const templateData = {
      name: templateName,
      description: templateDescription,
      type: templateType,
      defaults: getDefaultsForType(templateType),
    }

    if (selectedTemplate) {
      updateMutation.mutate({ id: selectedTemplate.id, data: templateData })
    } else {
      createMutation.mutate(templateData)
    }
  }

  const getDefaultsForType = (type: 'ad' | 'intranet' | 'public') => {
    switch (type) {
      case 'ad':
        return {
          type: 'ad' as const,
          forward_policy: 'first' as const,
          servers: ['192.168.1.10', '192.168.1.11'],
          domain: 'corp.local',
          health_check_enabled: true,
          health_check_interval: 300,
          priority: 10,
          weight: 100,
        }
      case 'intranet':
        return {
          type: 'intranet' as const,
          forward_policy: 'first' as const,
          servers: ['10.0.0.10', '10.0.0.11'],
          domain: 'internal.company',
          health_check_enabled: true,
          health_check_interval: 600,
          priority: 20,
          weight: 100,
        }
      case 'public':
        return {
          type: 'public' as const,
          forward_policy: 'first' as const,
          servers: ['1.1.1.1', '8.8.8.8'],
          domain: '',
          health_check_enabled: true,
          health_check_interval: 900,
          priority: 30,
          weight: 100,
        }
      default:
        return {}
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ad':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
      case 'intranet':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
      case 'public':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title="Forwarder Templates"
        size="lg"
      >
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage reusable forwarder configuration templates
            </p>
            <Button
              onClick={() => setIsEditModalOpen(true)}
              size="sm"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              New Template
            </Button>
          </div>

          {/* Templates List */}
          <div className="space-y-3">
            {isLoading ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                Loading templates...
              </div>
            ) : templates?.data && templates.data.length > 0 ? (
              templates.data.map((template) => (
                <Card key={template.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {template.name}
                        </h3>
                        <Badge className={getTypeColor(template.type)} size="sm">
                          {template.type.toUpperCase()}
                        </Badge>
                        {template.is_system && (
                          <Badge variant="info" size="sm">
                            System
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                        {template.description}
                      </p>
                      
                      {/* Template Details */}
                      <div className="grid grid-cols-2 gap-4 text-xs text-gray-500 dark:text-gray-400">
                        <div>
                          <span className="font-medium">Servers:</span>{' '}
                          {template.defaults.servers?.length || 0}
                        </div>
                        <div>
                          <span className="font-medium">Policy:</span>{' '}
                          {template.defaults.forward_policy || 'first'}
                        </div>
                        <div>
                          <span className="font-medium">Health Check:</span>{' '}
                          {template.defaults.health_check_enabled ? 'Enabled' : 'Disabled'}
                        </div>
                        <div>
                          <span className="font-medium">Priority:</span>{' '}
                          {template.defaults.priority || 10}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      {onTemplateSelect && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            onTemplateSelect(template)
                            onClose()
                          }}
                        >
                          <DocumentDuplicateIcon className="h-4 w-4" />
                        </Button>
                      )}
                      {!template.is_system && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(template)}
                          >
                            <PencilIcon className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(template)}
                            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </Card>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <BookmarkIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No templates found</p>
                <p className="text-sm">Create your first template to get started</p>
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Template Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          resetForm()
        }}
        title={selectedTemplate ? 'Edit Template' : 'Create Template'}
        size="md"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Template Name"
            placeholder="My Custom Template"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            required
          />

          <Input
            label="Description"
            placeholder="Template description"
            value={templateDescription}
            onChange={(e) => setTemplateDescription(e.target.value)}
            required
          />

          <Select
            label="Type"
            value={templateType}
            onChange={(e) => setTemplateType(e.target.value as any)}
            options={[
              { value: 'ad', label: 'Active Directory' },
              { value: 'intranet', label: 'Intranet' },
              { value: 'public', label: 'Public DNS' },
            ]}
          />

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Default Configuration Preview
            </h4>
            <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
              {Object.entries(getDefaultsForType(templateType)).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="font-medium">{key.replace(/_/g, ' ')}:</span>
                  <span>{Array.isArray(value) ? value.join(', ') : String(value)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsEditModalOpen(false)
                resetForm()
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {selectedTemplate ? 'Update' : 'Create'} Template
            </Button>
          </div>
        </form>
      </Modal>
    </>
  )
}

export default ForwarderTemplates