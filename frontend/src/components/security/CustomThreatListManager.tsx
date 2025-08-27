import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import {
    PlusIcon,
    TrashIcon,
    PencilIcon,
    DocumentTextIcon,
    CloudArrowUpIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { Modal, Button, Input, Card, Badge, Table, Textarea, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui'
import { formatDateTime, formatNumber } from '@/utils'
import { ThreatFeed, RPZRule } from '@/types'
import { toast } from 'react-toastify'

interface CustomThreatListManagerProps {
    isOpen: boolean
    onClose: () => void
    onSuccess: () => void
}

interface CustomListFormData {
    name: string
    description?: string
    domains: string
    action: 'block' | 'redirect' | 'passthru'
    redirect_target?: string
}

const CustomThreatListManager: React.FC<CustomThreatListManagerProps> = ({
    isOpen,
    onClose,
    onSuccess,
}) => {
    const [selectedList, setSelectedList] = useState<ThreatFeed | null>(null)
    const [isFormOpen, setIsFormOpen] = useState(false)
    const [isDomainsModalOpen, setIsDomainsModalOpen] = useState(false)
    const [selectedListDomains, setSelectedListDomains] = useState<RPZRule[]>([])

    const queryClient = useQueryClient()

    const {
        register,
        handleSubmit,
        formState: { errors },
        reset,
        setValue,
        watch,
    } = useForm<CustomListFormData>({
        defaultValues: {
            name: '',
            description: '',
            domains: '',
            action: 'block',
            redirect_target: '',
        },
    })

    const watchAction = watch('action')

    // Fetch custom threat lists
    const { data: customLists, isLoading } = useQuery({
        queryKey: ['custom-threat-lists'],
        queryFn: () => rpzService.getCustomLists({ limit: 1000 }),
        enabled: isOpen,
    })

    // Create custom list mutation
    const createListMutation = useMutation({
        mutationFn: (data: { name: string; description?: string }) =>
            rpzService.createCustomList(data.name, data.description),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['custom-threat-lists'] })
            toast.success('Custom threat list created successfully')
            setIsFormOpen(false)
            reset()
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to create custom threat list')
        },
    })

    // Add domains to list mutation
    const addDomainsMutation = useMutation({
        mutationFn: ({
            listId,
            domains,
            action,
            redirectTarget,
        }: {
            listId: number
            domains: string[]
            action: string
            redirectTarget?: string
        }) => rpzService.addDomainsToCustomList(listId, domains, action, redirectTarget),
        onSuccess: (_, { domains }) => {
            queryClient.invalidateQueries({ queryKey: ['custom-threat-lists'] })
            toast.success(`Added ${domains.length} domains to custom list`)
            setIsFormOpen(false)
            reset()
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to add domains to custom list')
        },
    })

    // Remove domains from list mutation
    const removeDomainsMutation = useMutation({
        mutationFn: ({ listId, domains }: { listId: number; domains: string[] }) =>
            rpzService.removeDomainsFromCustomList(listId, domains),
        onSuccess: (_, { domains }) => {
            queryClient.invalidateQueries({ queryKey: ['custom-threat-lists'] })
            queryClient.invalidateQueries({ queryKey: ['custom-list-domains'] })
            toast.success(`Removed ${domains.length} domains from custom list`)
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to remove domains from custom list')
        },
    })

    // Delete custom list mutation
    const deleteListMutation = useMutation({
        mutationFn: (listId: number) => rpzService.deleteThreatFeed(listId, true),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['custom-threat-lists'] })
            toast.success('Custom threat list deleted successfully')
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to delete custom threat list')
        },
    })

    const handleCreateList = () => {
        setSelectedList(null)
        reset()
        setIsFormOpen(true)
    }

    const handleEditList = (list: ThreatFeed) => {
        setSelectedList(list)
        setValue('name', list.name)
        setValue('description', list.description || '')
        setIsFormOpen(true)
    }

    const handleDeleteList = (list: ThreatFeed) => {
        if (
            window.confirm(
                `Are you sure you want to delete the custom threat list "${list.name}"? This will remove all ${list.rules_count} associated rules.`
            )
        ) {
            deleteListMutation.mutate(list.id)
        }
    }

    const handleViewDomains = async (list: ThreatFeed) => {
        try {
            const response = await rpzService.getCustomListDomains(list.id, { limit: 1000 })
            setSelectedListDomains(response.data)
            setSelectedList(list)
            setIsDomainsModalOpen(true)
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to load domains')
        }
    }

    const handleRemoveSelectedDomains = (domains: string[]) => {
        if (selectedList && domains.length > 0) {
            if (window.confirm(`Remove ${domains.length} domains from "${selectedList.name}"?`)) {
                removeDomainsMutation.mutate({
                    listId: selectedList.id,
                    domains,
                })
            }
        }
    }

    const onSubmit = (data: CustomListFormData) => {
        if (selectedList) {
            // Adding domains to existing list
            const domains = data.domains
                .split('\n')
                .map(d => d.trim())
                .filter(d => d.length > 0)

            if (domains.length === 0) {
                toast.error('Please enter at least one domain')
                return
            }

            addDomainsMutation.mutate({
                listId: selectedList.id,
                domains,
                action: data.action,
                redirectTarget: data.redirect_target,
            })
        } else {
            // Creating new list
            createListMutation.mutate({
                name: data.name,
                description: data.description,
            })
        }
    }

    const columns = [
        {
            key: 'name',
            header: 'Name',
            render: (list: ThreatFeed) => (
                <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                        {list.name}
                    </div>
                    {list.description && (
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                            {list.description}
                        </div>
                    )}
                </div>
            ),
        },
        {
            key: 'rules_count',
            header: 'Domains',
            render: (list: ThreatFeed) => (
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {formatNumber(list.rules_count)}
                </span>
            ),
        },
        {
            key: 'is_active',
            header: 'Status',
            render: (list: ThreatFeed) => (
                <Badge variant={list.is_active ? 'success' : 'default'}>
                    {list.is_active ? 'Active' : 'Inactive'}
                </Badge>
            ),
        },
        {
            key: 'created_at',
            header: 'Created',
            render: (list: ThreatFeed) => (
                <span className="text-sm text-gray-600 dark:text-gray-400">
                    {formatDateTime(list.created_at)}
                </span>
            ),
        },
        {
            key: 'actions',
            header: 'Actions',
            render: (list: ThreatFeed) => (
                <div className="flex items-center space-x-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDomains(list)}
                        title="View domains"
                    >
                        <DocumentTextIcon className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditList(list)}
                        title="Add domains"
                    >
                        <PlusIcon className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteList(list)}
                        title="Delete list"
                        className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                        <TrashIcon className="h-4 w-4" />
                    </Button>
                </div>
            ),
        },
    ]

    if (!isOpen) return null

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Custom Threat Lists"
            size="xl"
        >
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Manage custom threat lists with your own domain collections
                    </p>
                    <Button onClick={handleCreateList}>
                        <PlusIcon className="h-4 w-4 mr-2" />
                        Create List
                    </Button>
                </div>

                {/* Custom Lists Table */}
                <Card>
                    <Table
                        data={customLists?.data || []}
                        columns={columns}
                        loading={isLoading}
                        emptyMessage="No custom threat lists found. Create your first list to get started."
                    />
                </Card>

                {/* Create/Edit Form Modal */}
                {isFormOpen && (
                    <Modal
                        isOpen={isFormOpen}
                        onClose={() => {
                            setIsFormOpen(false)
                            setSelectedList(null)
                            reset()
                        }}
                        title={selectedList ? `Add Domains to ${selectedList.name}` : 'Create Custom Threat List'}
                        size="lg"
                    >
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                            {!selectedList && (
                                <>
                                    <Input
                                        label="List Name"
                                        {...register('name', { required: 'List name is required' })}
                                        error={errors.name?.message}
                                        placeholder="e.g., Company Blocklist"
                                    />

                                    <Textarea
                                        label="Description (Optional)"
                                        {...register('description')}
                                        placeholder="Brief description of this threat list"
                                        rows={2}
                                    />
                                </>
                            )}

                            {selectedList && (
                                <>
                                    <div className="space-y-4">
                                        <Textarea
                                            label="Domains"
                                            {...register('domains', { required: 'At least one domain is required' })}
                                            error={errors.domains?.message}
                                            placeholder="Enter domains, one per line:&#10;example.com&#10;malicious-site.net&#10;*.bad-domain.org"
                                            rows={8}
                                            className="font-mono text-sm"
                                        />

                                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
                                                <Select {...register('action')}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select action" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="block">Block</SelectItem>
                                                        <SelectItem value="redirect">Redirect</SelectItem>
                                                        <SelectItem value="passthru">Pass Through</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            {watchAction === 'redirect' && (
                                                <Input
                                                    label="Redirect Target"
                                                    {...register('redirect_target', {
                                                        required: watchAction === 'redirect' ? 'Redirect target is required' : false,
                                                    })}
                                                    error={errors.redirect_target?.message}
                                                    placeholder="blocked.example.com"
                                                />
                                            )}
                                        </div>
                                    </div>

                                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                                        <div className="flex">
                                            <ExclamationTriangleIcon className="h-5 w-5 text-blue-400 flex-shrink-0" />
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                                                    Domain Format Tips
                                                </h3>
                                                <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                                                    <ul className="list-disc list-inside space-y-1">
                                                        <li>Enter one domain per line</li>
                                                        <li>Use wildcards: *.example.com blocks all subdomains</li>
                                                        <li>No need for http:// or https://</li>
                                                        <li>Invalid domains will be skipped with warnings</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}

                            <div className="flex justify-end space-x-3">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => {
                                        setIsFormOpen(false)
                                        setSelectedList(null)
                                        reset()
                                    }}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    loading={createListMutation.isPending || addDomainsMutation.isPending}
                                >
                                    {selectedList ? 'Add Domains' : 'Create List'}
                                </Button>
                            </div>
                        </form>
                    </Modal>
                )}

                {/* Domains Modal */}
                {isDomainsModalOpen && selectedList && (
                    <Modal
                        isOpen={isDomainsModalOpen}
                        onClose={() => {
                            setIsDomainsModalOpen(false)
                            setSelectedList(null)
                            setSelectedListDomains([])
                        }}
                        title={`Domains in ${selectedList.name}`}
                        size="xl"
                    >
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {formatNumber(selectedListDomains.length)} domains in this list
                                </p>
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        const selectedDomains = selectedListDomains
                                            .filter((_, index) => (document.getElementById(`domain-${index}`) as HTMLInputElement)?.checked)
                                            .map(rule => rule.domain)

                                        if (selectedDomains.length > 0) {
                                            handleRemoveSelectedDomains(selectedDomains)
                                        } else {
                                            toast.warning('Please select domains to remove')
                                        }
                                    }}
                                    className="text-red-600 hover:text-red-700"
                                >
                                    <TrashIcon className="h-4 w-4 mr-2" />
                                    Remove Selected
                                </Button>
                            </div>

                            <div className="max-h-96 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                    <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                                        <tr>
                                            <th className="px-4 py-3 text-left">
                                                <input
                                                    type="checkbox"
                                                    onChange={(e) => {
                                                        const checkboxes = document.querySelectorAll('input[id^="domain-"]')
                                                        checkboxes.forEach((checkbox) => {
                                                            ; (checkbox as HTMLInputElement).checked = e.target.checked
                                                        })
                                                    }}
                                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                />
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                                Domain
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                                Action
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                                Added
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                                        {selectedListDomains.map((rule, index) => (
                                            <tr key={rule.id}>
                                                <td className="px-4 py-3">
                                                    <input
                                                        id={`domain-${index}`}
                                                        type="checkbox"
                                                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-gray-100">
                                                    {rule.domain}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Badge variant={rule.action === 'block' ? 'destructive' : 'default'}>
                                                        {rule.action}
                                                    </Badge>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                                                    {formatDateTime(rule.created_at)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </Modal>
                )}
            </div>
        </Modal>
    )
}

export default CustomThreatListManager