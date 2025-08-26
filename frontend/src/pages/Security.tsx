import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  ShieldExclamationIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { rpzService, dashboardService } from '@/services/api'
import { RPZRule } from '@/types'
import { Card, Button, Table, Badge, Input, Select } from '@/components/ui'
import { formatDateTime, getCategoryColor, formatNumber, formatRelativeTime } from '@/utils'
import { toast } from 'react-toastify'
import RPZRuleModal from '@/components/security/RPZRuleModal'
import ThreatFeedManager from '@/components/security/ThreatFeedManager'
import SecurityStats from '@/components/security/SecurityStats'
import BulkRuleActions from '@/components/security/BulkRuleActions'
import ThreatIntelligenceDashboard from '@/components/security/ThreatIntelligenceDashboard'
import CustomThreatListManager from '@/components/security/CustomThreatListManager'
import SecurityAnalytics from '@/components/security/SecurityAnalytics'
import SecurityTestPanel from '@/components/security/SecurityTestPanel'

const Security: React.FC = () => {
  const [selectedRule, setSelectedRule] = useState<RPZRule | null>(null)
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false)
  const [isThreatFeedManagerOpen, setIsThreatFeedManagerOpen] = useState(false)
  const [isThreatIntelDashboardOpen, setIsThreatIntelDashboardOpen] = useState(false)
  const [isCustomListManagerOpen, setIsCustomListManagerOpen] = useState(false)
  const [isSecurityAnalyticsOpen, setIsSecurityAnalyticsOpen] = useState(false)
  const [isTestPanelOpen, setIsTestPanelOpen] = useState(false)
  const [selectedRules, setSelectedRules] = useState<number[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [actionFilter, setActionFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showBulkActions, setShowBulkActions] = useState(false)

  const queryClient = useQueryClient()

  // Fetch RPZ rules
  const { data: rules, isLoading } = useQuery({
    queryKey: ['rpz-rules', categoryFilter, actionFilter, statusFilter, searchTerm],
    queryFn: () => rpzService.getRules({
      category: categoryFilter !== 'all' ? categoryFilter : undefined,
      action: actionFilter !== 'all' ? actionFilter : undefined,
      search: searchTerm || undefined,
      active_only: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
      limit: 1000
    }),
  })

  // Fetch security statistics
  const { data: securityStats } = useQuery({
    queryKey: ['security-stats'],
    queryFn: () => rpzService.getStatistics({ include_trends: true }),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch threat intelligence statistics
  const { data: threatIntelStats } = useQuery({
    queryKey: ['threat-intel-stats'],
    queryFn: () => rpzService.getThreatIntelligenceStatistics(),
    refetchInterval: 60000, // Refresh every minute
  })

  // Fetch blocked queries for the last 24 hours
  const { data: blockedQueries } = useQuery({
    queryKey: ['blocked-queries'],
    queryFn: () => rpzService.getBlockedQueries({ hours: 24, limit: 100 }),
    refetchInterval: 60000, // Refresh every minute
  })

  // Delete rule mutation
  const deleteRuleMutation = useMutation({
    mutationFn: rpzService.deleteRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      toast.success('Rule deleted successfully')
    },
    onError: () => {
      toast.error('Failed to delete rule')
    },
  })

  // Toggle rule mutation
  const toggleRuleMutation = useMutation({
    mutationFn: rpzService.toggleRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      toast.success('Rule status updated')
    },
    onError: () => {
      toast.error('Failed to update rule status')
    },
  })

  // Update threat feeds mutation
  const updateThreatFeedsMutation = useMutation({
    mutationFn: () => rpzService.updateAllThreatFeeds(false),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      queryClient.invalidateQueries({ queryKey: ['security-stats'] })
      queryClient.invalidateQueries({ queryKey: ['threat-intel-stats'] })
      toast.success(`Threat feeds updated successfully. ${response.data.successful_updates} feeds updated.`)
    },
    onError: () => {
      toast.error('Failed to update threat feeds')
    },
  })

  // Bulk operations mutations
  const bulkDeleteMutation = useMutation({
    mutationFn: (ruleIds: number[]) => rpzService.bulkDeleteRules({ rule_ids: ruleIds }),
    onSuccess: (response, ruleIds) => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      queryClient.invalidateQueries({ queryKey: ['security-stats'] })
      setSelectedRules([])
      toast.success(`Successfully deleted ${response.data.deleted_count} rules`)
      if (response.data.error_count > 0) {
        toast.warning(`${response.data.error_count} rules failed to delete`)
      }
    },
    onError: () => {
      toast.error('Failed to delete selected rules')
    },
  })

  const bulkToggleMutation = useMutation({
    mutationFn: ({ ruleIds, isActive }: { ruleIds: number[]; isActive: boolean }) =>
      rpzService.bulkToggleRules(ruleIds, isActive),
    onSuccess: (_, { ruleIds, isActive }) => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      queryClient.invalidateQueries({ queryKey: ['security-stats'] })
      setSelectedRules([])
      toast.success(`Successfully ${isActive ? 'activated' : 'deactivated'} ${ruleIds.length} rules`)
    },
    onError: () => {
      toast.error('Failed to update selected rules')
    },
  })

  const handleCreateRule = () => {
    setSelectedRule(null)
    setIsRuleModalOpen(true)
  }

  const handleEditRule = (rule: RPZRule) => {
    setSelectedRule(rule)
    setIsRuleModalOpen(true)
  }

  const handleDeleteRule = async (rule: RPZRule) => {
    if (window.confirm(`Are you sure you want to delete the rule for "${rule.domain}"?`)) {
      deleteRuleMutation.mutate(rule.id)
    }
  }

  const handleToggleRule = (rule: RPZRule) => {
    toggleRuleMutation.mutate(rule.id)
  }

  const handleUpdateThreatFeeds = () => {
    updateThreatFeedsMutation.mutate()
  }

  const handleBulkDelete = () => {
    if (selectedRules.length === 0) return

    if (window.confirm(`Are you sure you want to delete ${selectedRules.length} selected rules?`)) {
      bulkDeleteMutation.mutate(selectedRules)
    }
  }

  const handleBulkToggle = (isActive: boolean) => {
    if (selectedRules.length === 0) return

    bulkToggleMutation.mutate({ ruleIds: selectedRules, isActive })
  }

  const handleSelectRule = (ruleId: number, selected: boolean) => {
    if (selected) {
      setSelectedRules(prev => [...prev, ruleId])
    } else {
      setSelectedRules(prev => prev.filter(id => id !== ruleId))
    }
  }

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedRules(filteredRules.map(rule => rule.id))
    } else {
      setSelectedRules([])
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'block':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
      case 'redirect':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
      case 'passthru':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  // Filter and search rules
  const filteredRules = useMemo(() => {
    if (!rules?.data) return []

    return rules.data.filter(rule => {
      const matchesSearch = searchTerm === '' ||
        rule.domain.toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.rpz_zone.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesCategory = categoryFilter === 'all' || rule.category === categoryFilter
      const matchesAction = actionFilter === 'all' || rule.action === actionFilter
      const matchesStatus = statusFilter === 'all' ||
        (statusFilter === 'active' && rule.is_active) ||
        (statusFilter === 'inactive' && !rule.is_active)

      return matchesSearch && matchesCategory && matchesAction && matchesStatus
    })
  }, [rules?.data, searchTerm, categoryFilter, actionFilter, statusFilter])

  const columns = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={selectedRules.length === filteredRules.length && filteredRules.length > 0}
          onChange={(e) => handleSelectAll(e.target.checked)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
      render: (rule: RPZRule) => (
        <input
          type="checkbox"
          checked={selectedRules.includes(rule.id)}
          onChange={(e) => handleSelectRule(rule.id, e.target.checked)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
    },
    {
      key: 'domain',
      header: 'Domain',
      render: (rule: RPZRule) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {rule.domain}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Zone: {rule.rpz_zone}
          </div>
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (rule: RPZRule) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(rule.category)}`}>
          {rule.category.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (rule: RPZRule) => (
        <div>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getActionColor(rule.action)}`}>
            {rule.action}
          </span>
          {rule.redirect_target && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">
              → {rule.redirect_target}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (rule: RPZRule) => (
        <Badge variant={rule.is_active ? 'success' : 'default'}>
          {rule.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (rule: RPZRule) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatDateTime(rule.created_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (rule: RPZRule) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditRule(rule)}
            title="Edit rule"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleToggleRule(rule)}
            title={rule.is_active ? 'Deactivate' : 'Activate'}
            loading={toggleRuleMutation.isPending}
          >
            {rule.is_active ? (
              <PauseIcon className="h-4 w-4" />
            ) : (
              <PlayIcon className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteRule(rule)}
            title="Delete rule"
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  const rulesData = rules?.data || []
  const activeRules = rulesData.filter(r => r.is_active)
  const blockRules = rulesData.filter(r => r.action === 'block')
  const categoryStats = rulesData.reduce((acc, rule) => {
    acc[rule.category] = (acc[rule.category] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Get unique values for filters
  const categories = [...new Set(rulesData.map(r => r.category))]
  const actions = [...new Set(rulesData.map(r => r.action))]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Security & RPZ Management
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Manage Response Policy Zones for DNS-based threat protection
            </p>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => setIsSecurityAnalyticsOpen(true)}
            >
              <ChartBarIcon className="h-4 w-4 mr-2" />
              Analytics
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsThreatIntelDashboardOpen(true)}
            >
              <ShieldCheckIcon className="h-4 w-4 mr-2" />
              Intelligence
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsCustomListManagerOpen(true)}
            >
              <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
              Custom Lists
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsThreatFeedManagerOpen(true)}
            >
              <Cog6ToothIcon className="h-4 w-4 mr-2" />
              Manage Feeds
            </Button>
            <Button
              variant="outline"
              onClick={handleUpdateThreatFeeds}
              loading={updateThreatFeedsMutation.isPending}
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Update Feeds
            </Button>
            <Button onClick={handleCreateRule}>
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Rule
            </Button>
            {process.env.NODE_ENV === 'development' && (
              <Button
                variant="outline"
                onClick={() => setIsTestPanelOpen(true)}
                className="border-dashed"
              >
                🧪 Test Panel
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Enhanced Stats cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <ShieldCheckIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {formatNumber(rulesData.length)}
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Rules
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <PlayIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {formatNumber(activeRules.length)}
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active Rules
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                <ShieldExclamationIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {formatNumber(blockedQueries?.data?.summary?.total_blocked || 0)}
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Blocked Today
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <ChartBarIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {Object.keys(categoryStats).length}
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Categories
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                <ClockIcon className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {threatIntelStats?.data?.update_health?.feeds_up_to_date || 0}
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Feeds Updated
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Security Statistics */}
      <SecurityStats
        categoryStats={categoryStats}
        securityStats={securityStats?.data}
        blockedQueries={blockedQueries?.data?.query_results || []}
        threatIntelStats={threatIntelStats?.data}
      />

      {/* Filters and Search */}
      <Card>
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-col space-y-4 sm:flex-row sm:space-y-0 sm:space-x-4">
            <div className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search rules by domain or zone..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex space-x-2">
              <Select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="min-w-[120px]"
                options={[
                  { value: 'all', label: 'All Categories' },
                  ...categories.map(category => ({
                    value: category,
                    label: category.replace('_', ' ')
                  }))
                ]}
              />

              <Select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="min-w-[100px]"
                options={[
                  { value: 'all', label: 'All Actions' },
                  ...actions.map(action => ({
                    value: action,
                    label: action
                  }))
                ]}
              />

              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="min-w-[100px]"
                options={[
                  { value: 'all', label: 'All Status' },
                  { value: 'active', label: 'Active' },
                  { value: 'inactive', label: 'Inactive' }
                ]}
              />

              <Button
                variant="outline"
                onClick={() => setShowBulkActions(!showBulkActions)}
                className={selectedRules.length > 0 ? 'bg-blue-50 dark:bg-blue-900/20' : ''}
              >
                <FunnelIcon className="h-4 w-4 mr-2" />
                Bulk Actions {selectedRules.length > 0 && `(${selectedRules.length})`}
              </Button>
            </div>
          </div>

          {/* Bulk Actions */}
          {showBulkActions && selectedRules.length > 0 && (
            <BulkRuleActions
              selectedCount={selectedRules.length}
              onBulkDelete={handleBulkDelete}
              onBulkActivate={() => handleBulkToggle(true)}
              onBulkDeactivate={() => handleBulkToggle(false)}
              onExport={() => {
                // Export selected rules
                const selectedRuleData = filteredRules.filter(rule => selectedRules.includes(rule.id))
                const exportData = JSON.stringify(selectedRuleData, null, 2)
                const blob = new Blob([exportData], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `rpz-rules-${new Date().toISOString().split('T')[0]}.json`
                a.click()
                URL.revokeObjectURL(url)
                toast.success(`Exported ${selectedRules.length} rules`)
              }}
              loading={bulkDeleteMutation.isPending || bulkToggleMutation.isPending}
            />
          )}
        </div>
      </Card>

      {/* Security alert */}
      <Card className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
        <div className="flex items-start space-x-3">
          <ExclamationTriangleIcon className="h-6 w-6 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-1" />
          <div>
            <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Security Information
            </h3>
            <div className="mt-1 text-sm text-amber-700 dark:text-amber-300">
              <ul className="list-disc list-inside space-y-1">
                <li>RPZ rules are processed in order of priority</li>
                <li>Threat feeds are automatically updated daily</li>
                <li>Custom rules take precedence over imported rules</li>
                <li>Changes to RPZ rules require BIND reload to take effect</li>
              </ul>
            </div>
          </div>
        </div>
      </Card>

      {/* Rules table */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                Security Rules
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Showing {filteredRules.length} of {rulesData.length} rules
              </p>
            </div>
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const exportData = JSON.stringify(filteredRules, null, 2)
                  const blob = new Blob([exportData], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `rpz-rules-${new Date().toISOString().split('T')[0]}.json`
                  a.click()
                  URL.revokeObjectURL(url)
                  toast.success('Rules exported successfully')
                }}
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </div>

        <Table
          data={filteredRules}
          columns={columns}
          loading={isLoading}
          emptyMessage={
            searchTerm || categoryFilter !== 'all' || actionFilter !== 'all' || statusFilter !== 'all'
              ? "No rules match the current filters. Try adjusting your search criteria."
              : "No security rules configured. Create your first rule to start DNS-based threat protection."
          }
        />
      </Card>

      {/* Rule modal */}
      {isRuleModalOpen && (
        <RPZRuleModal
          rule={selectedRule}
          isOpen={isRuleModalOpen}
          onClose={() => setIsRuleModalOpen(false)}
          onSuccess={() => {
            setIsRuleModalOpen(false)
            queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
          }}
        />
      )}

      {/* Threat feed manager modal */}
      {isThreatFeedManagerOpen && (
        <ThreatFeedManager
          isOpen={isThreatFeedManagerOpen}
          onClose={() => setIsThreatFeedManagerOpen(false)}
          onSuccess={() => {
            setIsThreatFeedManagerOpen(false)
            queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
            queryClient.invalidateQueries({ queryKey: ['security-stats'] })
            queryClient.invalidateQueries({ queryKey: ['threat-intel-stats'] })
          }}
        />
      )}

      {/* Threat intelligence dashboard */}
      {isThreatIntelDashboardOpen && (
        <ThreatIntelligenceDashboard
          isOpen={isThreatIntelDashboardOpen}
          onClose={() => setIsThreatIntelDashboardOpen(false)}
        />
      )}

      {/* Custom threat list manager */}
      {isCustomListManagerOpen && (
        <CustomThreatListManager
          isOpen={isCustomListManagerOpen}
          onClose={() => setIsCustomListManagerOpen(false)}
          onSuccess={() => {
            setIsCustomListManagerOpen(false)
            queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
            queryClient.invalidateQueries({ queryKey: ['security-stats'] })
            queryClient.invalidateQueries({ queryKey: ['threat-intel-stats'] })
          }}
        />
      )}

      {/* Security analytics */}
      {isSecurityAnalyticsOpen && (
        <SecurityAnalytics
          isOpen={isSecurityAnalyticsOpen}
          onClose={() => setIsSecurityAnalyticsOpen(false)}
        />
      )}

      {/* Test panel (development only) */}
      {process.env.NODE_ENV === 'development' && isTestPanelOpen && (
        <SecurityTestPanel
          isOpen={isTestPanelOpen}
          onClose={() => setIsTestPanelOpen(false)}
        />
      )}
    </div>
  )
}

export default Security