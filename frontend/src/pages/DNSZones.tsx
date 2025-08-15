import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  PlusIcon, 
  PencilIcon, 
  TrashIcon, 
  EyeIcon,
  ArrowPathIcon,
  PlayIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { zonesService, recordsService } from '@/services/api'
import { Zone, DNSRecord } from '@/types'
import { Card, Button, Table, Badge, Loading } from '@/components/ui'
import { formatDateTime, formatNumber, getStatusColor } from '@/utils'
import { toast } from 'react-toastify'
import ZoneModal from '@/components/zones/ZoneModal'
import RecordModal from '@/components/zones/RecordModal'
import RecordsView from '@/components/zones/RecordsView'

const DNSZones: React.FC = () => {
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null)
  const [isZoneModalOpen, setIsZoneModalOpen] = useState(false)
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<DNSRecord | null>(null)
  const [viewingZoneRecords, setViewingZoneRecords] = useState<Zone | null>(null)
  
  const queryClient = useQueryClient()

  // Fetch zones
  const { data: zones, isLoading } = useQuery({
    queryKey: ['zones'],
    queryFn: () => zonesService.getZones(),
  })

  // Delete zone mutation
  const deleteZoneMutation = useMutation({
    mutationFn: zonesService.deleteZone,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      toast.success('Zone deleted successfully')
    },
    onError: () => {
      toast.error('Failed to delete zone')
    },
  })

  // Toggle zone mutation
  const toggleZoneMutation = useMutation({
    mutationFn: zonesService.toggleZone,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      toast.success('Zone status updated')
    },
    onError: () => {
      toast.error('Failed to update zone status')
    },
  })

  // Reload zone mutation
  const reloadZoneMutation = useMutation({
    mutationFn: zonesService.reloadZone,
    onSuccess: () => {
      toast.success('Zone reloaded successfully')
    },
    onError: () => {
      toast.error('Failed to reload zone')
    },
  })

  const handleCreateZone = () => {
    setSelectedZone(null)
    setIsZoneModalOpen(true)
  }

  const handleEditZone = (zone: Zone) => {
    setSelectedZone(zone)
    setIsZoneModalOpen(true)
  }

  const handleDeleteZone = async (zone: Zone) => {
    if (window.confirm(`Are you sure you want to delete the zone "${zone.name}"?`)) {
      deleteZoneMutation.mutate(zone.id)
    }
  }

  const handleToggleZone = (zone: Zone) => {
    toggleZoneMutation.mutate(zone.id)
  }

  const handleReloadZone = (zone: Zone) => {
    reloadZoneMutation.mutate(zone.id)
  }

  const handleViewRecords = (zone: Zone) => {
    setViewingZoneRecords(zone)
  }

  const handleCreateRecord = () => {
    setSelectedRecord(null)
    setIsRecordModalOpen(true)
  }

  const columns = [
    {
      key: 'name',
      header: 'Zone Name',
      render: (zone: Zone) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {zone.name}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {zone.type} zone
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (zone: Zone) => (
        <Badge 
          variant={zone.type === 'master' ? 'success' : zone.type === 'slave' ? 'info' : 'default'}
        >
          {zone.type}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (zone: Zone) => (
        <Badge variant={zone.is_active ? 'success' : 'default'}>
          {zone.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'serial',
      header: 'Serial',
      render: (zone: Zone) => (
        <span className="font-mono text-sm">
          {formatNumber(zone.serial)}
        </span>
      ),
    },
    {
      key: 'ttl',
      header: 'TTL',
      render: (zone: Zone) => (
        <span className="font-mono text-sm">
          {formatNumber(zone.ttl)}s
        </span>
      ),
    },
    {
      key: 'updated_at',
      header: 'Last Updated',
      render: (zone: Zone) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatDateTime(zone.updated_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (zone: Zone) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleViewRecords(zone)}
            title="View records"
          >
            <EyeIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditZone(zone)}
            title="Edit zone"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleToggleZone(zone)}
            title={zone.is_active ? 'Deactivate' : 'Activate'}
            loading={toggleZoneMutation.isPending}
          >
            {zone.is_active ? (
              <PauseIcon className="h-4 w-4" />
            ) : (
              <PlayIcon className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleReloadZone(zone)}
            title="Reload zone"
            loading={reloadZoneMutation.isPending}
          >
            <ArrowPathIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteZone(zone)}
            title="Delete zone"
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  if (viewingZoneRecords) {
    return (
      <RecordsView
        zone={viewingZoneRecords}
        onBack={() => setViewingZoneRecords(null)}
        onCreateRecord={handleCreateRecord}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              DNS Zones
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Manage authoritative DNS zones and records
            </p>
          </div>
          <Button onClick={handleCreateZone}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Zone
          </Button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">
                  {zones?.data?.length || 0}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Zones
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <span className="text-green-600 dark:text-green-400 font-semibold">
                  {zones?.data?.filter(zone => zone.is_active).length || 0}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active Zones
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400 font-semibold">
                  {zones?.data?.filter(zone => zone.type === 'master').length || 0}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Master Zones
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Zones table */}
      <Card>
        <Table
          data={zones?.data || []}
          columns={columns}
          loading={isLoading}
          emptyMessage="No DNS zones found. Create your first zone to get started."
        />
      </Card>

      {/* Zone modal */}
      {isZoneModalOpen && (
        <ZoneModal
          zone={selectedZone}
          isOpen={isZoneModalOpen}
          onClose={() => setIsZoneModalOpen(false)}
          onSuccess={() => {
            setIsZoneModalOpen(false)
            queryClient.invalidateQueries({ queryKey: ['zones'] })
          }}
        />
      )}

      {/* Record modal */}
      {isRecordModalOpen && viewingZoneRecords && (
        <RecordModal
          zoneId={viewingZoneRecords.id}
          record={selectedRecord}
          isOpen={isRecordModalOpen}
          onClose={() => setIsRecordModalOpen(false)}
          onSuccess={() => {
            setIsRecordModalOpen(false)
            queryClient.invalidateQueries({ 
              queryKey: ['records', viewingZoneRecords.id] 
            })
          }}
        />
      )}
    </div>
  )
}

export default DNSZones