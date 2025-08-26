import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import {
  CloudArrowDownIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlayIcon,
  PauseIcon,
  BeakerIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { Modal, Button, Input, Select, Card, Badge, Table } from '@/components/ui'
import { formatDateTime, formatRelativeTime } from '@/utils'
import { ThreatFeed, ThreatFeedFormData } from '@/types'
import { toast } from 'react-toastify'

interface ThreatFeedManagerProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

interface FeedFormData {
  name: string
  url: string
  feed_type: string
  format_type: string
  update_frequency: number
  description?: string
  is_active: boolean
}

interface CustomListFormData {
  name: string
  category: string
  description: string
  domains: string
}

interface ThreatFeedStatistics {
  total_feeds: number
  active_feeds: number
  inactive_feeds: number
  total_rules: number
  rules_by_category: Record<string, number>
  feeds_by_status: Record<string, number>
  update_statistics: {
    successful_updates_24h: number
    failed_updates_24h: number
    pending_updates: number
    never_updated: number
  }
  health_metrics: {
    overall_health_score: number
    feeds_needing_attention: Array<{
      feed_id: number
      feed_name: string
      issues: string[]
    }>
    recommendations: string[]
  }
}

const ThreatFeedManager: React.FC<ThreatFeedManagerProps> = ({ isOpen, onClose, onSuccess }) => {
  const [selectedFeed, setSelectedFeed] = useState<ThreatFeed | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [importResults, setImportResults] = useState<string | null>(null)
  const [isCustomListOpen, setIsCustomListOpen] = useState(false)
  const [isStatisticsOpen, setIsStatisticsOpen] = useState(false)
  const [isScheduleOpen, setIsScheduleOpen] = useState(false)

  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<FeedFormData>({
    defaultValues: {
      name: '',
      url: '',
      feed_type: 'malware',
      format_type: 'domains',
      update_frequency: 86400, // 24 hours in seconds
      description: '',
      is_active: true,
    },
  })

  const {
    register: registerCustom,
    handleSubmit: handleSubmitCustom,
    formState: { errors: customErrors },
    reset: resetCustom,
  } = useForm<CustomListFormData>({
    defaultValues: {
      name: '',
      category: 'custom',
      description: '',
      domains: '',
    },
  })

  // Fetch threat feeds
  const { data: feeds, isLoading } = useQuery({
    queryKey: ['threat-feeds'],
    queryFn: () => rpzService.getThreatFeeds(),
    enabled: isOpen,
  })

  // Fetch threat feed statistics
  const { data: statistics } = useQuery({
    queryKey: ['threat-feed-statistics'],
    queryFn: () => rpzService.getThreatFeedStatistics(),
    enabled: isStatisticsOpen,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch threat feed schedule
  const { data: schedule } = useQuery({
    queryKey: ['threat-feed-schedule'],
    queryFn: () => rpzService.getThreatFeedSchedule(),
    enabled: isScheduleOpen,
    refetchInterval: 60000, // Refresh every minute
  })

  // Create feed mutation
  const createFeedMutation = useMutation({
    mutationFn: rpzService.createThreatFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success('Threat feed created successfully')
      setIsFormOpen(false)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create threat feed')
    },
  })

  // Update feed mutation
  const updateFeedMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FeedFormData> }) =>
      rpzService.updateThreatFeed(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success('Threat feed updated successfully')
      setIsFormOpen(false)
      setSelectedFeed(null)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update threat feed')
    },
  })

  // Delete feed mutation
  const deleteFeedMutation = useMutation({
    mutationFn: rpzService.deleteThreatFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success('Threat feed deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete threat feed')
    },
  })

  // Update single feed mutation
  const updateSingleFeedMutation = useMutation({
    mutationFn: rpzService.updateSingleThreatFeed,
    onSuccess: (response, feedId) => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      const feed = feeds?.data?.find((f: ThreatFeed) => f.id === feedId)
      toast.success(`Updated ${feed?.name}: ${response.data.data.imported} rules imported`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update threat feed')
    },
  })

  // Toggle feed mutation
  const toggleFeedMutation = useMutation({
    mutationFn: (id: number) => rpzService.toggleThreatFeed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success('Threat feed status updated')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update threat feed status')
    },
  })

  // Test feed mutation
  const testFeedMutation = useMutation({
    mutationFn: rpzService.testThreatFeed,
    onSuccess: (response) => {
      toast.success('Feed test successful')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Feed test failed')
    },
  })

  // Create custom threat list mutation
  const createCustomListMutation = useMutation({
    mutationFn: rpzService.createCustomThreatList,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success('Custom threat list created successfully')
      setIsCustomListOpen(false)
      resetCustom()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create custom threat list')
    },
  })

  // Schedule updates mutation
  const scheduleUpdatesMutation = useMutation({
    mutationFn: rpzService.scheduleThreatFeedUpdates,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['threat-feeds'] })
      toast.success(`Updates completed: ${response.data.successful_updates} successful, ${response.data.failed_updates} failed`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to schedule updates')
    },
  })

  const handleCreateFeed = () => {
    setSelectedFeed(null)
    reset()
    setIsFormOpen(true)
  }

  const handleEditFeed = (feed: ThreatFeed) => {
    setSelectedFeed(feed)
    setValue('name', feed.name)
    setValue('url', feed.url)
    setValue('feed_type', feed.feed_type)
    setValue('format_type', feed.format_type)
    setValue('update_frequency', feed.update_frequency)
    setValue('description', feed.description || '')
    setValue('is_active', feed.is_active)
    setIsFormOpen(true)
  }

  const handleDeleteFeed = (feed: ThreatFeed) => {
    if (window.confirm(`Are you sure you want to delete the threat feed "${feed.name}"? This will also remove all associated rules.`)) {
      deleteFeedMutation.mutate(feed.id)
    }
  }

  const handleUpdateFeed = (feedId: number) => {
    updateSingleFeedMutation.mutate(feedId)
  }

  const handleToggleFeed = (feed: ThreatFeed) => {
    toggleFeedMutation.mutate(feed.id)
  }

  const onSubmit = (data: FeedFormData) => {
    if (selectedFeed) {
      updateFeedMutation.mutate({ id: selectedFeed.id, data })
    } else {
      createFeedMutation.mutate(data)
    }
  }

  const onSubmitCustomList = (data: CustomListFormData) => {
    const domains = data.domains
      .split('\n')
      .map(d => d.trim())
      .filter(d => d.length > 0)

    createCustomListMutation.mutate({
      name: data.name,
      domains,
      category: data.category,
      description: data.description,
    })
  }

  const handleScheduleUpdates = () => {
    if (window.confirm('This will update all threat feeds that are due for updates. Continue?')) {
      scheduleUpdatesMutation.mutate()
    }
  }

  const loadPresetFeed = (preset: string) => {
    const presets: Record<string, Partial<FeedFormData>> = {
      'malware-domains': {
        name: 'Malware Domains List',
        url: 'https://mirror1.malwaredomains.com/files/domains.txt',
        category: 'malware',
      },
      'phishing-army': {
        name: 'Phishing Army',
        url: 'https://phishing.army/download/phishing_army_blocklist_extended.txt',
        category: 'phishing',
      },
      'abuse-ch': {
        name: 'Abuse.ch URLhaus',
        url: 'https://urlhaus.abuse.ch/downloads/hostfile/',
        category: 'malware',
      },
      'someonewhocares': {
        name: 'SomeoneWhoCares Hosts',
        url: 'https://someonewhocares.org/hosts/zero/hosts',
        category: 'malware',
      },
    }

    const preset_data = presets[preset]
    if (preset_data) {
      Object.entries(preset_data).forEach(([key, value]) => {
        setValue(key as keyof FeedFormData, value as any)
      })
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'error':
        return 'danger'
      case 'updating':
        return 'warning'
      case 'disabled':
        return 'default'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="h-4 w-4" />
      case 'error':
        return <XCircleIcon className="h-4 w-4" />
      case 'updating':
        return <ArrowPathIcon className="h-4 w-4 animate-spin" />
      case 'disabled':
        return <XCircleIcon className="h-4 w-4" />
      default:
        return null
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Feed Name',
      render: (feed: ThreatFeed) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {feed.name}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
            {feed.url.length > 50 ? `${feed.url.substring(0, 50)}...` : feed.url}
          </div>
        </div>
      ),
    },
    {
      key: 'feed_type',
      header: 'Type',
      render: (feed: ThreatFeed) => (
        <Badge variant="info">
          {feed.feed_type.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (feed: ThreatFeed) => (
        <div className="flex items-center space-x-2">
          <Badge variant={getStatusColor(feed.last_update_status || 'never')}>
            <div className="flex items-center space-x-1">
              {getStatusIcon(feed.last_update_status || 'never')}
              <span>{feed.last_update_status || 'never'}</span>
            </div>
          </Badge>
          {feed.is_active && (
            <Badge variant="success" size="sm">
              Active
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'rules',
      header: 'Rules',
      render: (feed: ThreatFeed) => (
        <div className="text-center">
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {feed.rule_count.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            rules
          </div>
        </div>
      ),
    },
    {
      key: 'last_update',
      header: 'Last Update',
      render: (feed: ThreatFeed) => (
        <div>
          {feed.last_update ? (
            <>
              <div className="text-sm text-gray-900 dark:text-gray-100">
                {formatRelativeTime(feed.last_update)}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {formatDateTime(feed.last_update)}
              </div>
            </>
          ) : (
            <span className="text-sm text-gray-500 dark:text-gray-400">Never</span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (feed: ThreatFeed) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleUpdateFeed(feed.id)}
            loading={updateSingleFeedMutation.isPending}
            title="Update feed"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleToggleFeed(feed)}
            loading={toggleFeedMutation.isPending}
            title={feed.enabled ? 'Disable feed' : 'Enable feed'}
          >
            {feed.enabled ? (
              <XCircleIcon className="h-4 w-4 text-red-600" />
            ) : (
              <CheckCircleIcon className="h-4 w-4 text-green-600" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditFeed(feed)}
            title="Edit feed"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteFeed(feed)}
            title="Delete feed"
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  const feedsData = feeds?.data || []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Threat Feed Management"
      size="xl"
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
              Configured Threat Feeds
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage external threat intelligence feeds for automatic rule updates
            </p>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => setIsStatisticsOpen(true)}
            >
              Statistics
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsScheduleOpen(true)}
            >
              <ClockIcon className="h-4 w-4 mr-2" />
              Schedule
            </Button>
            <Button
              variant="outline"
              onClick={handleScheduleUpdates}
              loading={scheduleUpdatesMutation.isPending}
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Update All
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsCustomListOpen(true)}
            >
              Custom List
            </Button>
            <Button onClick={handleCreateFeed}>
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Feed
            </Button>
          </div>
        </div>

        {/* Feeds Table */}
        <Card>
          <Table
            data={feedsData}
            columns={columns}
            loading={isLoading}
            emptyMessage="No threat feeds configured. Add your first feed to start importing threat intelligence."
          />
        </Card>

        {/* Feed Form Modal */}
        {isFormOpen && (
          <Modal
            isOpen={isFormOpen}
            onClose={() => {
              setIsFormOpen(false)
              setSelectedFeed(null)
              reset()
            }}
            title={selectedFeed ? 'Edit Threat Feed' : 'Add Threat Feed'}
            size="lg"
          >
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Input
                    label="Feed Name"
                    placeholder="Malware Domains List"
                    {...register('name', { required: 'Feed name is required' })}
                    error={errors.name?.message}
                  />
                </div>

                <div className="sm:col-span-2">
                  <Input
                    label="Feed URL"
                    type="url"
                    placeholder="https://example.com/threat-feed.txt"
                    {...register('url', {
                      required: 'Feed URL is required',
                      pattern: {
                        value: /^https?:\/\/.+/,
                        message: 'Must be a valid HTTP/HTTPS URL',
                      },
                    })}
                    error={errors.url?.message}
                  />
                </div>

                <Select
                  label="Category"
                  {...register('category', { required: 'Category is required' })}
                  error={errors.category?.message}
                  options={[
                    { value: 'malware', label: 'Malware' },
                    { value: 'phishing', label: 'Phishing' },
                    { value: 'social_media', label: 'Social Media' },
                    { value: 'adult', label: 'Adult Content' },
                    { value: 'gambling', label: 'Gambling' },
                    { value: 'custom', label: 'Custom' }
                  ]}
                />

                <Input
                  label="Update Interval (hours)"
                  type="number"
                  min="1"
                  max="168"
                  {...register('update_interval', {
                    required: 'Update interval is required',
                    min: { value: 1, message: 'Minimum interval is 1 hour' },
                    max: { value: 168, message: 'Maximum interval is 168 hours (1 week)' },
                  })}
                  error={errors.update_interval?.message}
                />

                <div className="sm:col-span-2 space-y-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('enabled')}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Enable this feed
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('auto_update')}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Enable automatic updates
                    </span>
                  </label>
                </div>
              </div>

              {/* Preset feeds */}
              {!selectedFeed && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                    Quick Setup - Popular Feeds:
                  </h4>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 p-2 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      onClick={() => loadPresetFeed('malware-domains')}
                    >
                      Malware Domains List
                    </button>
                    <button
                      type="button"
                      className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 p-2 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      onClick={() => loadPresetFeed('phishing-army')}
                    >
                      Phishing Army
                    </button>
                    <button
                      type="button"
                      className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 p-2 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      onClick={() => loadPresetFeed('abuse-ch')}
                    >
                      Abuse.ch URLhaus
                    </button>
                    <button
                      type="button"
                      className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 p-2 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      onClick={() => loadPresetFeed('someonewhocares')}
                    >
                      SomeoneWhoCares
                    </button>
                  </div>
                </div>
              )}

              {/* Warning */}
              <div className="bg-yellow-50 dark:bg-yellow-900/50 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                      Important Notes:
                    </h4>
                    <ul className="text-sm text-yellow-700 dark:text-yellow-300 mt-1 space-y-1">
                      <li>• Large feeds may take several minutes to process</li>
                      <li>• Automatic updates will run based on the specified interval</li>
                      <li>• Duplicate domains will be automatically filtered</li>
                      <li>• BIND configuration will be reloaded after updates</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsFormOpen(false)
                    setSelectedFeed(null)
                    reset()
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={createFeedMutation.isPending || updateFeedMutation.isPending}
                >
                  {selectedFeed ? 'Update Feed' : 'Add Feed'}
                </Button>
              </div>
            </form>
          </Modal>
        )}

        {/* Custom Threat List Modal */}
        {isCustomListOpen && (
          <Modal
            isOpen={isCustomListOpen}
            onClose={() => {
              setIsCustomListOpen(false)
              resetCustom()
            }}
            title="Create Custom Threat List"
            size="lg"
          >
            <form onSubmit={handleSubmitCustom(onSubmitCustomList)} className="space-y-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Input
                    label="List Name"
                    placeholder="My Custom Block List"
                    {...registerCustom('name', { required: 'List name is required' })}
                    error={customErrors.name?.message}
                  />
                </div>

                <Select
                  label="Category"
                  {...registerCustom('category', { required: 'Category is required' })}
                  error={customErrors.category?.message}
                  options={[
                    { value: 'custom', label: 'Custom' },
                    { value: 'malware', label: 'Malware' },
                    { value: 'phishing', label: 'Phishing' },
                    { value: 'social_media', label: 'Social Media' },
                    { value: 'adult', label: 'Adult Content' },
                    { value: 'gambling', label: 'Gambling' }
                  ]}
                />

                <div className="sm:col-span-2">
                  <Input
                    label="Description"
                    placeholder="Description of this threat list"
                    {...registerCustom('description')}
                    error={customErrors.description?.message}
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Domains to Block
                  </label>
                  <textarea
                    {...registerCustom('domains', { required: 'At least one domain is required' })}
                    rows={10}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                    placeholder="Enter one domain per line:&#10;example.com&#10;malicious-site.net&#10;phishing-domain.org"
                  />
                  {customErrors.domains && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                      {customErrors.domains.message}
                    </p>
                  )}
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Enter one domain per line. Invalid domains will be automatically filtered out.
                  </p>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsCustomListOpen(false)
                    resetCustom()
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={createCustomListMutation.isPending}
                >
                  Create Custom List
                </Button>
              </div>
            </form>
          </Modal>
        )}

        {/* Statistics Modal */}
        {isStatisticsOpen && (
          <Modal
            isOpen={isStatisticsOpen}
            onClose={() => setIsStatisticsOpen(false)}
            title="Threat Feed Statistics"
            size="xl"
          >
            <div className="space-y-6">
              {statistics?.data && (
                <>
                  {/* Overview Cards */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Card className="p-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                          {statistics.data.total_feeds}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Total Feeds
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                          {statistics.data.active_feeds}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Active Feeds
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                          {statistics.data.total_rules.toLocaleString()}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Total Rules
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                          {statistics.data.health_metrics.overall_health_score}%
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Health Score
                        </div>
                      </div>
                    </Card>
                  </div>

                  {/* Rules by Category */}
                  <Card className="p-4">
                    <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                      Rules by Category
                    </h4>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                      {Object.entries(statistics.data.rules_by_category).map(([category, count]) => (
                        <div key={category} className="text-center">
                          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                            {count.toLocaleString()}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                            {category.replace('_', ' ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Health Issues */}
                  {statistics.data.health_metrics.feeds_needing_attention.length > 0 && (
                    <Card className="p-4">
                      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        Feeds Needing Attention
                      </h4>
                      <div className="space-y-2">
                        {statistics.data.health_metrics.feeds_needing_attention.map((feed) => (
                          <div key={feed.feed_id} className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                            <div>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {feed.feed_name}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {feed.issues.join(', ')}
                              </div>
                            </div>
                            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}

                  {/* Recommendations */}
                  {statistics.data.health_metrics.recommendations.length > 0 && (
                    <Card className="p-4">
                      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        Recommendations
                      </h4>
                      <ul className="space-y-2">
                        {statistics.data.health_metrics.recommendations.map((recommendation, index) => (
                          <li key={index} className="flex items-start space-x-2">
                            <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                              {recommendation}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}
                </>
              )}
            </div>
          </Modal>
        )}

        {/* Schedule Modal */}
        {isScheduleOpen && (
          <Modal
            isOpen={isScheduleOpen}
            onClose={() => setIsScheduleOpen(false)}
            title="Update Schedule"
            size="lg"
          >
            <div className="space-y-6">
              {schedule?.data && (
                <>
                  {/* Schedule Summary */}
                  <Card className="p-4">
                    <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                      Schedule Summary
                    </h4>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                      <div className="text-center">
                        <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                          {schedule.data.schedule_summary.total_active_feeds}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Active Feeds
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xl font-bold text-red-600 dark:text-red-400">
                          {schedule.data.schedule_summary.feeds_overdue}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Overdue
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xl font-bold text-yellow-600 dark:text-yellow-400">
                          {schedule.data.schedule_summary.feeds_due_now}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Due Now
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xl font-bold text-green-600 dark:text-green-400">
                          {schedule.data.schedule_summary.next_update_in_minutes || 'N/A'}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Next (min)
                        </div>
                      </div>
                    </div>
                  </Card>

                  {/* Overdue Feeds */}
                  {schedule.data.overdue_feeds.length > 0 && (
                    <Card className="p-4">
                      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        Overdue Feeds
                      </h4>
                      <div className="space-y-2">
                        {schedule.data.overdue_feeds.map((feed) => (
                          <div key={feed.feed_id} className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                            <div>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {feed.feed_name}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {feed.minutes_overdue} minutes overdue
                              </div>
                            </div>
                            <Badge variant={feed.priority === 'high' ? 'danger' : 'warning'}>
                              {feed.priority}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}

                  {/* Upcoming Updates */}
                  {schedule.data.upcoming_updates.length > 0 && (
                    <Card className="p-4">
                      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        Upcoming Updates
                      </h4>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {schedule.data.upcoming_updates.slice(0, 10).map((feed) => (
                          <div key={feed.feed_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <div>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {feed.feed_name}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                Updates every {feed.update_frequency_hours}h
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                {feed.minutes_until}m
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                until update
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}
                </>
              )}
            </div>
          </Modal>
        )}
      </div>
    </Modal>
  )
}

export default ThreatFeedManager