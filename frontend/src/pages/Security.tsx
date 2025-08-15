import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { RPZRule } from '@/types'
import { Card, Button, Table, Badge } from '@/components/ui'
import { formatDateTime, getCategoryColor } from '@/utils'
import { toast } from 'react-toastify'
import RPZRuleModal from '@/components/security/RPZRuleModal'
import ThreatFeedImport from '@/components/security/ThreatFeedImport'

const Security: React.FC = () => {
  const [selectedRule, setSelectedRule] = useState<RPZRule | null>(null)
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false)
  const [isThreatFeedImportOpen, setIsThreatFeedImportOpen] = useState(false)

  const queryClient = useQueryClient()

  // Fetch RPZ rules
  const { data: rules, isLoading } = useQuery({
    queryKey: ['rpz-rules'],
    queryFn: () => rpzService.getRules(),
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
    mutationFn: rpzService.updateThreatFeeds,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
      toast.success(`Threat feeds updated successfully. ${response.data.data.updated} rules updated.`)
    },
    onError: () => {
      toast.error('Failed to update threat feeds')
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

  const columns = [
    {
      key: 'domain',
      header: 'Domain',
      render: (rule: RPZRule) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {rule.domain}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Zone: {rule.zone}
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
              onClick={() => setIsThreatFeedImportOpen(true)}
            >
              Import Threat Feed
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
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">
                  {rulesData.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
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
                <span className="text-green-600 dark:text-green-400 font-semibold">
                  {activeRules.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
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
                <span className="text-red-600 dark:text-red-400 font-semibold">
                  {blockRules.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Block Rules
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400 font-semibold">
                  {Object.keys(categoryStats).length}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Categories
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Category breakdown */}
      <Card 
        title="Category Breakdown" 
        description="Number of rules by category"
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(categoryStats).map(([category, count]) => (
            <div key={category} className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {count}
              </div>
              <div className={`text-sm px-2 py-1 rounded-full ${getCategoryColor(category)}`}>
                {category.replace('_', ' ')}
              </div>
            </div>
          ))}
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
        <Table
          data={rulesData}
          columns={columns}
          loading={isLoading}
          emptyMessage="No security rules configured. Create your first rule to start DNS-based threat protection."
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

      {/* Threat feed import modal */}
      {isThreatFeedImportOpen && (
        <ThreatFeedImport
          isOpen={isThreatFeedImportOpen}
          onClose={() => setIsThreatFeedImportOpen(false)}
          onSuccess={() => {
            setIsThreatFeedImportOpen(false)
            queryClient.invalidateQueries({ queryKey: ['rpz-rules'] })
          }}
        />
      )}
    </div>
  )
}

export default Security