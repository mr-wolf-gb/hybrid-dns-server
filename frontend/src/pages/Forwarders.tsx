import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  ViewColumnsIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline'
import { forwardersService } from '@/services/api'
import { Forwarder } from '@/types'
import { Card, Button, Table, Badge } from '@/components/ui'
import { formatDateTime } from '@/utils'
import { toast } from 'react-toastify'
import ForwarderModal from '@/components/forwarders/ForwarderModal'
import ForwarderTestModal from '@/components/forwarders/ForwarderTestModal'
import ForwarderHealthIndicator from '@/components/forwarders/ForwarderHealthIndicator'
import ForwarderStatistics from '@/components/forwarders/ForwarderStatistics'
import ForwarderGrouping from '@/components/forwarders/ForwarderGrouping'

const Forwarders: React.FC = () => {
  const [selectedForwarder, setSelectedForwarder] = useState<Forwarder | null>(null)
  const [isForwarderModalOpen, setIsForwarderModalOpen] = useState(false)
  const [isTestModalOpen, setIsTestModalOpen] = useState(false)
  const [testForwarder, setTestForwarder] = useState<Forwarder | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'grouped' | 'statistics'>('table')
  const [selectedForwarders, setSelectedForwarders] = useState<Set<number>>(new Set())
  const [showActiveOnly, setShowActiveOnly] = useState(false)

  const queryClient = useQueryClient()

  // Fetch forwarders
  const { data: forwarders, isLoading } = useQuery({
    queryKey: ['forwarders', showActiveOnly],
    queryFn: () => forwardersService.getForwarders(showActiveOnly),
  })

  // Delete forwarder mutation
  const deleteForwarderMutation = useMutation({
    mutationFn: forwardersService.deleteForwarder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forwarders'] })
      toast.success('Forwarder deleted successfully')
    },
    onError: () => {
      toast.error('Failed to delete forwarder')
    },
  })

  // Toggle forwarder mutation
  const toggleForwarderMutation = useMutation({
    mutationFn: forwardersService.toggleForwarder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forwarders'] })
      toast.success('Forwarder status updated')
    },
    onError: () => {
      toast.error('Failed to update forwarder status')
    },
  })

  // Test forwarder mutation
  const testForwarderMutation = useMutation({
    mutationFn: forwardersService.testForwarder,
    onSuccess: (response) => {
      const result = response.data.data
      toast.success(`Forwarder test successful - Response time: ${result.response_time}ms`)
      queryClient.invalidateQueries({ queryKey: ['forwarders'] })
    },
    onError: () => {
      toast.error('Forwarder test failed')
    },
  })

  // Bulk test forwarders mutation
  const bulkTestMutation = useMutation({
    mutationFn: forwardersService.bulkTestForwarders,
    onSuccess: (response) => {
      const results = response.data.data
      const successful = results.filter(r => r.status === 'success').length
      toast.success(`Bulk test completed: ${successful}/${results.length} forwarders healthy`)
      queryClient.invalidateQueries({ queryKey: ['forwarders'] })
    },
    onError: () => {
      toast.error('Bulk test failed')
    },
  })

  // Refresh health status mutation
  const refreshHealthMutation = useMutation({
    mutationFn: forwardersService.refreshHealthStatus,
    onSuccess: (response) => {
      const updated = response.data.data.updated
      toast.success(`Health status refreshed for ${updated} forwarders`)
      queryClient.invalidateQueries({ queryKey: ['forwarders'] })
    },
    onError: () => {
      toast.error('Failed to refresh health status')
    },
  })

  const handleCreateForwarder = () => {
    setSelectedForwarder(null)
    setIsForwarderModalOpen(true)
  }

  const handleEditForwarder = (forwarder: Forwarder) => {
    setSelectedForwarder(forwarder)
    setIsForwarderModalOpen(true)
  }

  const handleDeleteForwarder = async (forwarder: Forwarder) => {
    if (window.confirm(`Are you sure you want to delete the forwarder "${forwarder.name}"?`)) {
      deleteForwarderMutation.mutate(forwarder.id)
    }
  }

  const handleToggleForwarder = (forwarder: Forwarder) => {
    toggleForwarderMutation.mutate(forwarder.id)
  }

  const handleTestForwarder = (forwarder: Forwarder) => {
    setTestForwarder(forwarder)
    setIsTestModalOpen(true)
  }

  const handleQuickTest = (forwarder: Forwarder) => {
    testForwarderMutation.mutate(forwarder.id)
  }

  const handleBulkTest = () => {
    if (selectedForwarders.size === 0) {
      toast.error('Please select forwarders to test')
      return
    }
    bulkTestMutation.mutate(Array.from(selectedForwarders))
  }

  const handleRefreshHealth = () => {
    refreshHealthMutation.mutate()
  }

  const handleForwarderSelect = (forwarder: Forwarder) => {
    setSelectedForwarder(forwarder)
    setIsForwarderModalOpen(true)
  }

  const toggleForwarderSelection = (forwarderId: number) => {
    const newSelection = new Set(selectedForwarders)
    if (newSelection.has(forwarderId)) {
      newSelection.delete(forwarderId)
    } else {
      newSelection.add(forwarderId)
    }
    setSelectedForwarders(newSelection)
  }

  const selectAllForwarders = () => {
    if (selectedForwarders.size === forwarderData.length) {
      setSelectedForwarders(new Set())
    } else {
      setSelectedForwarders(new Set(forwarderData.map(f => f.id)))
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ad':
      case 'active_directory':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
      case 'intranet':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
      case 'public':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'ad':
      case 'active_directory':
        return 'Active Directory'
      case 'intranet':
        return 'Intranet'
      case 'public':
        return 'Public DNS'
      default:
        return type
    }
  }

  const forwarderData = forwarders?.data || []
  const activeForwarders = forwarderData.filter(f => f.is_active)
  const healthyForwarders = forwarderData.filter(f => f.health_status === 'healthy')

  const columns = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={selectedForwarders.size === forwarderData.length && forwarderData.length > 0}
          onChange={selectAllForwarders}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
      render: (forwarder: Forwarder) => (
        <input
          type="checkbox"
          checked={selectedForwarders.has(forwarder.id)}
          onChange={() => toggleForwarderSelection(forwarder.id)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (forwarder: Forwarder) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {forwarder.name}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {forwarder.domain}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (forwarder: Forwarder) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeColor(forwarder.forwarder_type || forwarder.type)}`}>
          {getTypeLabel(forwarder.forwarder_type || forwarder.type)}
        </span>
      ),
    },
    {
      key: 'servers',
      header: 'DNS Servers',
      render: (forwarder: Forwarder) => (
        <div className="space-y-1">
          {forwarder.servers.map((server, index) => (
            <div key={index} className="text-sm font-mono text-gray-900 dark:text-gray-100">
              {typeof server === 'string' ? server : `${server.ip}${server.port && server.port !== 53 ? `:${server.port}` : ''}`}
            </div>
          ))}
        </div>
      ),
    },
    {
      key: 'policy',
      header: 'Policy',
      render: (forwarder: Forwarder) => (
        <Badge variant={forwarder.forward_policy === 'first' ? 'info' : 'default'}>
          {forwarder.forward_policy}
        </Badge>
      ),
    },
    {
      key: 'health',
      header: 'Health',
      render: (forwarder: Forwarder) => (
        <ForwarderHealthIndicator forwarder={forwarder} showDetails />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (forwarder: Forwarder) => (
        <Badge variant={forwarder.is_active ? 'success' : 'default'}>
          {forwarder.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'last_check',
      header: 'Last Check',
      render: (forwarder: Forwarder) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {forwarder.last_health_check 
            ? formatDateTime(forwarder.last_health_check)
            : 'Never'
          }
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (forwarder: Forwarder) => (
        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleTestForwarder(forwarder)}
            title="Detailed test"
          >
            <Cog6ToothIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleQuickTest(forwarder)}
            title="Quick test"
            loading={testForwarderMutation.isPending}
          >
            <CheckCircleIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditForwarder(forwarder)}
            title="Edit forwarder"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleToggleForwarder(forwarder)}
            title={forwarder.is_active ? 'Deactivate' : 'Activate'}
            loading={toggleForwarderMutation.isPending}
          >
            {forwarder.is_active ? (
              <PauseIcon className="h-4 w-4" />
            ) : (
              <PlayIcon className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteForwarder(forwarder)}
            title="Delete forwarder"
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              DNS Forwarders
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Manage conditional DNS forwarding rules for different domains
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {/* View Mode Toggle */}
            <div className="flex items-center space-x-1 border border-gray-300 dark:border-gray-600 rounded-lg p-1">
              <Button
                variant={viewMode === 'table' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('table')}
              >
                <ViewColumnsIcon className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'grouped' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grouped')}
              >
                <Squares2X2Icon className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'statistics' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('statistics')}
              >
                <ChartBarIcon className="h-4 w-4" />
              </Button>
            </div>

            {/* Active/All Filter Toggle */}
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={showActiveOnly}
                  onChange={(e) => setShowActiveOnly(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Active only</span>
              </label>
            </div>

            {/* Bulk Actions */}
            {selectedForwarders.size > 0 && (
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkTest}
                  loading={bulkTestMutation.isPending}
                >
                  <CheckCircleIcon className="h-4 w-4 mr-1" />
                  Test Selected ({selectedForwarders.size})
                </Button>
              </div>
            )}

            {/* Refresh Health */}
            <Button
              variant="outline"
              onClick={handleRefreshHealth}
              loading={refreshHealthMutation.isPending}
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Refresh Health
            </Button>

            <Button onClick={handleCreateForwarder}>
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Forwarder
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
                  {forwarderData.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Forwarders
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <span className="text-green-600 dark:text-green-400 font-semibold">
                  {activeForwarders.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                  {healthyForwarders.length}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Healthy
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400 font-semibold">
                  {new Set(forwarderData.map(f => f.type)).size}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Types
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      {viewMode === 'statistics' ? (
        <ForwarderStatistics forwarders={forwarderData} />
      ) : viewMode === 'grouped' ? (
        <ForwarderGrouping
          forwarders={forwarderData}
          onForwarderSelect={handleForwarderSelect}
          onForwarderEdit={handleEditForwarder}
          onForwarderTest={handleTestForwarder}
          onForwarderToggle={handleToggleForwarder}
          onForwarderDelete={handleDeleteForwarder}
        />
      ) : (
        <Card>
          <Table
            data={forwarderData}
            columns={columns}
            loading={isLoading}
            emptyMessage="No forwarders configured. Create your first forwarder to get started."
          />
        </Card>
      )}

      {/* Forwarder modal */}
      {isForwarderModalOpen && (
        <ForwarderModal
          forwarder={selectedForwarder}
          isOpen={isForwarderModalOpen}
          onClose={() => setIsForwarderModalOpen(false)}
          onSuccess={() => {
            setIsForwarderModalOpen(false)
            queryClient.invalidateQueries({ queryKey: ['forwarders'] })
          }}
        />
      )}

      {/* Test modal */}
      {isTestModalOpen && testForwarder && (
        <ForwarderTestModal
          forwarder={testForwarder}
          isOpen={isTestModalOpen}
          onClose={() => {
            setIsTestModalOpen(false)
            setTestForwarder(null)
          }}
        />
      )}
    </div>
  )
}

export default Forwarders