import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useFieldArray } from 'react-hook-form'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { RPZRuleTemplate, RPZRuleTemplateFormData } from '@/types'
import {
  Modal,
  Button,
  Input,
  Select,
  Card,
  Badge,
  Table
} from '@/components/ui'
import { toast } from 'react-toastify'

interface RPZRuleTemplatesProps {
  isOpen: boolean onClose: () => void onTemplateSelect?: (template: RPZRuleTemplate) => void
}

const RPZRuleTemplates: React.FC<RPZRuleTemplatesProps> = ({ isOpen, onClose, onTemplateSelect }) => {
  const [selectedTemplate, setSelectedTemplate] = useState<RPZRuleTemplate | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: {
      errors
    },
    reset,
    control
  } = useForm<RPZRuleTemplateFormData>({
    defaultValues: {
      name: '',
      description: '',
      category: 'malware',
      action: 'block',
      zone: 'rpz.malware',
      redirect_target: '',
      domains: ['']
    }
  })

  const { fields, append, remove } = useFieldArray<RPZRuleTemplateFormData,
    'domains',
    'id'>({ control, name: 'domains' })

  // Fetch templates
  const { data: templates, isLoading } = useQuery({
    queryKey: ['rpz-templates'],
    queryFn: () => rpzService.getRuleTemplates(),
    enabled: isOpen
  })

  // Create template mutation
  const createTemplateMutation = useMutation({
    mutationFn: rpzService.createRuleTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rpz-templates'] })
      toast.success('Template created successfully')
      setIsFormOpen(false)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create template')
    }
  })

  // Update template mutation
  const updateTemplateMutation = useMutation({
    mutationFn: (
      { id, data }: {
        id: string;
        data: RPZRuleTemplateFormData
      }
    ) => rpzService.updateRuleTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rpz-templates'] })
      toast.success('Template updated successfully')
      setIsFormOpen(false)
      setSelectedTemplate(null)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update template')
    }
  })

  // Delete template mutation
  const deleteTemplateMutation = useMutation({
    mutationFn: rpzService.deleteRuleTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rpz-templates'] })
      toast.success('Template deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete template')
    }
  })

  const handleCreateTemplate = () => {
    setSelectedTemplate(null)
    reset({
      name: '',
      description: '',
      category: 'malware',
      action: 'block',
      zone: 'rpz.malware',
      redirect_target: '',
      domains: ['']
    })
    setIsFormOpen(true)
  }

  const handleEditTemplate = (template: RPZRuleTemplate) => {
    setSelectedTemplate(template)
    reset({
      name: template.name,
      description: template.description,
      category: template.category,
      action: template.action,
      zone: template.zone,
      redirect_target: template.redirect_target || '',
      domains: template.domains.length > 0 ? template.domains : ['']
    })
    setIsFormOpen(true)
  }

  const handleDeleteTemplate = (template: RPZRuleTemplate) => {
    if (window.confirm(`Are you sure you want to delete the template "${template.name
      }"?`)) {
      deleteTemplateMutation.mutate(template.id)
    }
  }

  const handleUseTemplate = (template: RPZRuleTemplate) => {
    if (onTemplateSelect) {
      onTemplateSelect(template)
      onClose()
    }
  }

  const onSubmit = (data: RPZRuleTemplateFormData) => { // Filter out empty domains
    const cleanedData = {
      ...data,
      domains: data.domains.filter(domain => domain.trim().length > 0)
    }

    if (selectedTemplate) {
      updateTemplateMutation.mutate({ id: selectedTemplate.id, data: cleanedData })
    } else {
      createTemplateMutation.mutate(cleanedData)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Template Name',
      render: (template: RPZRuleTemplate) => (<div> < div className="font-medium text-gray-900 dark:text-gray-100" > {
        template.name
      } < /div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {template.description}
        </div > </div>)
        }, {
          key: 'category',
        header: 'Category',
            render: (template : RPZRuleTemplate) => (<Badge variant="info"> {
          template.category.replace('_', ' ')
        } < /Badge>
          ),
    },
          {
            key: 'action',
          header: 'Action',
      render: (template: RPZRuleTemplate) => (
          <Badge
            variant={
              template.action === 'block'
                ? 'danger'
                : template.action === 'redirect'
                  ? 'warning'
                  : 'success'
            }
          >
            {template.action}
          </Badge >)
        }, {
            key: 'domains',
          header: 'Domains',
            render: (template : RPZRuleTemplate) => (<div className="text-sm text-gray-900 dark:text-gray-100"> {
            template.domains.length
          }
            domain {
              template.domains.length !== 1 ? 's' : ''
            } < /div>
            ),
    },
            {
              key: 'zone',
            header: 'Zone',
      render: (template: RPZRuleTemplate) => (
            <div className="text-sm font-mono text-gray-600 dark:text-gray-400">
              {template.zone}
            </div >)
    }, {
              key: 'actions',
            header: 'Actions',
    render: (template : RPZRuleTemplate) => (<div className="flex items-center space-x-2"> {
              onTemplateSelect && (< Button variant="ghost" size="sm" onClick=
                {() => handleUseTemplate(template)
                }
                title="Use template" > <DocumentDuplicateIcon className="h-4 w-4" /> < /Button>
          )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleEditTemplate(template)}
                  title="Edit template"
                >
                  <PencilIcon className="h-4 w-4" /> </Button> < Button variant="ghost" size="sm" onClick=
                    {() => handleDeleteTemplate(template)
                    }
                    title="Delete template" className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300" > <TrashIcon className="h-4 w-4" /> < /Button>
                </div >)
            },]

                const templatesData = templates ?. data || [] return(< Modal isOpen={
                  isOpen
                }
                  onClose={
                    onClose
                  }
                  title="RPZ Rule Templates" size="xl" > <div className="space-y-6"> { /* Header */
                  } < div className="flex items-center justify-between" > <div> < h3 className="text-lg font-medium text-gray-900 dark:text-gray-100" > Rule Templates < /h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Create and manage reusable rule templates for common scenarios
                    </p > </div> < Button onClick={
                      handleCreateTemplate
                    } > <PlusIcon className="h-4 w-4 mr-2" /> New Template < /Button>
                    </div > { /* Templates Table */
                    } < Card > <Table
                      data={templatesData}
                      columns={columns}
                      loading={isLoading}
                      emptyMessage="No templates created yet. Create your first template to get started."
                    /> < /Card>

                      {/ * Template Form Modal * /}
                      {isFormOpen && (
                        <Modal
                          isOpen={isFormOpen}
                          onClose={() => {
                            setIsFormOpen(false)
                            setSelectedTemplate(null)
                            reset()
                          }}
                          title={selectedTemplate ? 'Edit Template' : 'Create Template'}
                          size="lg"
                        >
                          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                              <div className="sm:col-span-2">
                                <Input
                                  label="Template Name"
                                  placeholder="Malware Blocking Template"
                                  {...register('name', { required: 'Template name is required' })}
                                  error={errors.name?.message}
                                /> </div> < div className="sm:col-span-2" > <Input
                                  label="Description"
                                  placeholder="Template for blocking known malware domains"
                                  {...register('description', { required: 'Description is required' })}
                                  error={errors.description?.message}
                                /> < /div>

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
                                /> <Select
                                  label="Action"
                                  options={[
                                    { value: 'block', label: 'Block (Drop)' }, { value: 'redirect', label: 'Redirect' }, { value: 'passthru', label: 'Allow (Pass Through)' },]}
                                  {...register('action', { required: 'Action is required' })}
                                  error={errors.action?.message}
                                /> < div className="sm:col-span-2" > <Select
                                  label="RPZ Zone"
                                  options={[
                                    { value: 'rpz.malware', label: 'Malware Protection' }, { value: 'rpz.phishing', label: 'Phishing Protection' }, { value: 'rpz.social-media', label: 'Social Media Blocking' }, { value: 'rpz.adult', label: 'Adult Content Blocking' }, { value: 'rpz.gambling', label: 'Gambling Blocking' }, { value: 'rpz.custom-block', label: 'Custom Block List' }, { value: 'rpz.custom-allow', label: 'Custom Allow List' },]}
                                  {...register('zone', { required: 'RPZ zone is required' })}
                                  error={errors.zone?.message}
                                /> < /div>

                                  {/ * Domains * /}
                                  <div className="sm:col-span-2">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                      Template Domains
                                    </label > <div className="space-y-2"> {
                                      fields.map((field, index) => (<div key={field.id} className="flex items-center space-x-2"> < Input placeholder = "example.com or *.example.com" {
                    ...register(`domains.${index}` as const)
                }
                className = "flex-1" /> {
                        fields.length > 1 && (< Button type = "button" variant = "ghost" size = "sm" onClick =
                            {() => remove(index)
                        }
                        className = "text-red-600 hover:text-red-700" > <XMarkIcon className="h-4 w-4" /> < /Button>
                        )}
                      </div >)
                    )} < Button type = "button" variant = "outline" size = "sm" onClick = {
                    () => append('')
                } > <PlusIcon className="h-4 w-4 mr-2" /> Add Domain < /Button>
                  </div > <p className="mt-1 text-sm text-gray-500 dark:text-gray-400"> Add example domains that this template should handle < /p>
                </div > </div> < div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700" > <Button
                                      variant="outline"
                                      onClick={() => {
                                        setIsFormOpen(false)
                                        setSelectedTemplate(null)
                                        reset()
                                      }} > Cancel < /Button>
                                      <Button
                                        type="submit"
                                        loading={createTemplateMutation.isPending || updateTemplateMutation.isPending}
                                      >
                                        {selectedTemplate ? 'Update Template' : 'Create Template'}
                                      </Button > </div> < /form>
                                  </Modal >
        )} < /div>
                                </Modal >
)}export default RPZRuleTemplates
