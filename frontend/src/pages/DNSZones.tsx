import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  ArrowPathIcon,
  PlayIcon,
  PauseIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  EllipsisVerticalIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone, DNSRecord } from '@/types'
import { Card, Button, Table, Badge, Input, Select } from '@/components/ui'
import { formatDateTime, formatNumber, debounce } from '@/utils'
import { toast } from 'react-toastify'
import ZoneModal from '@/components/zones/ZoneModal'
import RecordModal from '@/components/zones/RecordModal'
import RecordsView from '@/components/zones/RecordsView'
import ZoneValidationModal from '@/components/zones/ZoneValidationModal'
import ZoneImportExportModal from '@/components/zones/ZoneImportExportModal'
import ZoneStatistics from '@/components/zones/ZoneStatistics'


const DNSZones: React.FC = () => {
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null)
  const [isZoneModalOpen, setIsZoneModalOpen] = useState(false)
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<DNSRecord | null>(null)
  const [viewingZoneRecords, setViewingZoneRecords] = useState<Zone | null>(null)
  const [isValidationModalOpen, setIsValidationModalOpen] = useState(false)
  const [isImportExportModalOpen, setIsImportExportModalOpen] = useState(false)
  const [importExportMode, setImportExportMode] = useState<'import' | 'export'>('export')
  const [isStatisticsModalOpen, setIsStatisticsModalOpen] = useState(false)

  // Filtering and pagination state
  const [searchTerm, setSearchTerm] = useState('')
  const [zoneTypeFilter, setZoneTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(10)
  const [sortField, setSortField] = useState<keyof Zone>('name')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  const queryClient = useQueryClient()

  // Fetch zones
  const { data: zonesResponse, isLoading, error } = useQuery({
    queryKey: ['zones', statusFilter],
    queryFn: () => zonesService.getZones({
      active_only: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : false
    }),
    retry: (failureCount, error: any) => {
      // Don't retry on authentication errors
      if (error?.response?.status === 401) {
        return false
      }
      return failureCount < 3
    },
  })

  // Extract zones from paginated response
  const zones: Zone[] = useMemo(() => {
    if (!zonesResponse?.data) return []
    // Ensure we have the expected structure
    const data = zonesResponse.data
    if (Array.isArray(data)) {
      // Handle legacy array response
      return data
    }
    // Handle paginated response
    return data.items || []
  }, [zonesResponse])

  // Debounced search function
  const debouncedSearch = useMemo(
    () => debounce((term: string) => {
      setSearchTerm(term)
      setCurrentPage(1) // Reset to first page when searching
    }, 300),
    []
  )

  // Filter and sort zones
  const filteredAndSortedZones = useMemo(() => {
    // Ensure zones is always an array
    const safeZones = Array.isArray(zones) ? zones : []
    let filtered = safeZones.filter((zone) => {
      const matchesSearch = zone.name.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesType = zoneTypeFilter === 'all' || zone.zone_type === zoneTypeFilter
      // Status filtering is now handled by the API call
      return matchesSearch && matchesType
    })

    // Sort zones
    filtered.sort((a, b) => {
      const aValue = a[sortField]
      const bValue = b[sortField]

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue)
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue
      }

      return 0
    })

    return filtered
  }, [zones, searchTerm, zoneTypeFilter, sortField, sortDirection])

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedZones.length / itemsPerPage)
  const paginatedZones = filteredAndSortedZones.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  // Zone statistics
  const zoneStats = useMemo(() => {
    // Ensure zones is always an array
    const safeZones = Array.isArray(zones) ? zones : []
    return {
      total: safeZones.length,
      active: safeZones.filter(zone => zone.is_active).length,
      master: safeZones.filter(zone => zone.zone_type === 'master').length,
      slave: safeZones.filter(zone => zone.zone_type === 'slave').length,
      forward: safeZones.filter(zone => zone.zone_type === 'forward').length,
    }
  }, [zones])

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



  const handleValidateZone = (zone: Zone) => {
    setSelectedZone(zone)
    setIsValidationModalOpen(true)
  }

  const handleExportZone = (zone: Zone) => {
    setSelectedZone(zone)
    setImportExportMode('export')
    setIsImportExportModalOpen(true)
  }

  const handleImportZone = () => {
    setSelectedZone(null)
    setImportExportMode('import')
    setIsImportExportModalOpen(true)
  }

  const handleViewStatistics = (zone: Zone) => {
    setSelectedZone(zone)
    setIsStatisticsModalOpen(true)
  }

  const handleSort = (key: string) => {
    const field = key as keyof Zone
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (items: number) => {
    setItemsPerPage(items)
    setCurrentPage(1)
  }

  const getZoneStatusIndicator = (zone: Zone) => {
    if (!zone.is_active) {
      return (
        <div className="flex items-center">
          <ExclamationCircleIcon className="h-4 w-4 text-gray-400 mr-1" />
          <span className="text-gray-500">Inactive</span>
        </div>
      )
    }

    // For active zones, we could add more sophisticated health checking
    return (
      <div className="flex items-center">
        <CheckCircleIcon className="h-4 w-4 text-green-500 mr-1" />
        <span className="text-green-600">Active</span>
      </div>
    )
  }

  const ZoneActionsMenu: React.FC<{ zone: Zone }> = ({ zone }) => {
    const [isOpen, setIsOpen] = useState(false)
    const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0, placement: 'bottom-right' })
    const buttonRef = React.useRef<HTMLButtonElement>(null)

    const handleToggleMenu = () => {
      if (!isOpen && buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect()
        const viewportHeight = window.innerHeight
        const viewportWidth = window.innerWidth
        const menuWidth = 192 // 48 * 4 = 192px (w-48)
        const menuHeight = 320 // Approximate menu height

        let top = rect.bottom + 4 // 4px gap
        let left = rect.right - menuWidth
        let placement = 'bottom-right'

        // Check if menu would go below viewport
        if (top + menuHeight > viewportHeight && rect.top > menuHeight) {
          top = rect.top - menuHeight - 4
          placement = 'top-right'
        }

        // Check if menu would go outside left edge
        if (left < 8) {
          left = rect.left
          placement = placement.replace('right', 'left') as any
        }

        // Check if menu would go outside right edge
        if (left + menuWidth > viewportWidth - 8) {
          left = viewportWidth - menuWidth - 8
        }

        setMenuPosition({ top, left, placement })
      }
      setIsOpen(!isOpen)
    }

    React.useEffect(() => {
      const handleScroll = () => {
        if (isOpen) {
          setIsOpen(false)
        }
      }

      const handleResize = () => {
        if (isOpen) {
          setIsOpen(false)
        }
      }

      if (isOpen) {
        window.addEventListener('scroll', handleScroll, true)
        window.addEventListener('resize', handleResize)
        return () => {
          window.removeEventListener('scroll', handleScroll, true)
          window.removeEventListener('resize', handleResize)
        }
      }
    }, [isOpen])

    return (
      <>
        <div className="relative">
          <Button
            ref={buttonRef}
            variant="ghost"
            size="sm"
            onClick={handleToggleMenu}
            className="p-1"
          >
            <EllipsisVerticalIcon className="h-4 w-4" />
          </Button>
        </div>

        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            <div
              className="fixed w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg z-50 border border-gray-200 dark:border-gray-700"
              style={{
                top: menuPosition.top,
                left: menuPosition.left,
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
              }}
            >
              <div className="py-1">
                <button
                  onClick={() => {
                    handleViewRecords(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <EyeIcon className="h-4 w-4 mr-2" />
                  View Records
                </button>
                <button
                  onClick={() => {
                    setSelectedZone(zone)
                    setSelectedRecord(null)
                    setIsRecordModalOpen(true)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Add Record
                </button>
                <button
                  onClick={() => {
                    handleEditZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <PencilIcon className="h-4 w-4 mr-2" />
                  Edit Zone
                </button>
                <button
                  onClick={() => {
                    handleToggleZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {zone.is_active ? (
                    <>
                      <PauseIcon className="h-4 w-4 mr-2" />
                      Deactivate
                    </>
                  ) : (
                    <>
                      <PlayIcon className="h-4 w-4 mr-2" />
                      Activate
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    handleReloadZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={reloadZoneMutation.isPending}
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  Reload Zone
                </button>
                <button
                  onClick={() => {
                    handleValidateZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <ShieldCheckIcon className="h-4 w-4 mr-2" />
                  Validate Zone
                </button>
                <button
                  onClick={() => {
                    handleExportZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                  Export Zone
                </button>
                <button
                  onClick={() => {
                    handleViewStatistics(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <ChartBarIcon className="h-4 w-4 mr-2" />
                  View Statistics
                </button>
                <div className="border-t border-gray-200 dark:border-gray-600 my-1" />
                <button
                  onClick={() => {
                    handleDeleteZone(zone)
                    setIsOpen(false)
                  }}
                  className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <TrashIcon className="h-4 w-4 mr-2" />
                  Delete Zone
                </button>
              </div>
            </div>
          </>
        )}
      </>
    )
  }

  const columns = [
    {
      key: 'name',
      header: 'Zone Name',
      sortable: true,
      render: (zone: Zone) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {zone.name}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {zone.zone_type} zone
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      render: (zone: Zone) => (
        <Badge
          variant={zone.zone_type === 'master' ? 'success' : zone.zone_type === 'slave' ? 'info' : 'default'}
        >
          {zone.zone_type}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (zone: Zone) => getZoneStatusIndicator(zone),
    },
    {
      key: 'serial',
      header: 'Serial',
      sortable: true,
      render: (zone: Zone) => (
        <span className="font-mono text-sm">
          {formatNumber(zone.serial || 0)}
        </span>
      ),
    },
    {
      key: 'minimum',
      header: 'TTL',
      sortable: true,
      render: (zone: Zone) => (
        <span className="font-mono text-sm">
          {formatNumber(zone.minimum)}s
        </span>
      ),
    },
    {
      key: 'updated_at',
      header: 'Last Updated',
      sortable: true,
      render: (zone: Zone) => (
        <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
          <ClockIcon className="h-4 w-4 mr-1" />
          {formatDateTime(zone.updated_at)}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'relative',
      render: (zone: Zone) => <ZoneActionsMenu zone={zone} />,
    },
  ]

  if (viewingZoneRecords) {
    return (
      <RecordsView
        zone={viewingZoneRecords}
        onBack={() => setViewingZoneRecords(null)}
      />
    )
  }

  // Handle error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            DNS Zones
          </h1>
        </div>
        <Card className="p-6">
          <div className="text-center">
            <ExclamationCircleIcon className="mx-auto h-12 w-12 text-red-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              Failed to load zones
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {(error as any)?.response?.status === 401
                ? 'Please log in to access DNS zones.'
                : 'There was an error loading the DNS zones. Please try again.'}
            </p>
            <div className="mt-6">
              <Button
                onClick={() => {
                  if ((error as any)?.response?.status === 401) {
                    window.location.href = '/login'
                  } else {
                    queryClient.invalidateQueries({ queryKey: ['zones'] })
                  }
                }}
              >
                {(error as any)?.response?.status === 401 ? 'Go to Login' : 'Retry'}
              </Button>
            </div>
          </div>
        </Card>
      </div>
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
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={handleImportZone}>
              <ArrowUpTrayIcon className="h-4 w-4 mr-2" />
              Import Zone
            </Button>
            <Button onClick={handleCreateZone}>
              <PlusIcon className="h-4 w-4 mr-2" />
              Create Zone
            </Button>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-semibold">
                  {zoneStats.total}
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
                  {zoneStats.active}
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
                  {zoneStats.master}
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

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
                <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                  {zoneStats.slave}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Slave Zones
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                <span className="text-orange-600 dark:text-orange-400 font-semibold">
                  {zoneStats.forward}
                </span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Forward Zones
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters and search */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search zones..."
                className="pl-10"
                onChange={(e) => debouncedSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Select
              value={zoneTypeFilter}
              onChange={(e) => {
                setZoneTypeFilter(e.target.value)
                setCurrentPage(1)
              }}
              options={[
                { value: 'all', label: 'All Types' },
                { value: 'master', label: 'Master' },
                { value: 'slave', label: 'Slave' },
                { value: 'forward', label: 'Forward' },
              ]}
            />
            <Select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setCurrentPage(1)
              }}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'active', label: 'Active' },
                { value: 'inactive', label: 'Inactive' },
              ]}
            />
            <Select
              value={itemsPerPage.toString()}
              onChange={(e) => handleItemsPerPageChange(parseInt(e.target.value))}
              options={[
                { value: '10', label: '10 per page' },
                { value: '25', label: '25 per page' },
                { value: '50', label: '50 per page' },
                { value: '100', label: '100 per page' },
              ]}
            />
          </div>
        </div>

        {/* Results summary */}
        <div className="mt-4 flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <div>
            Showing {paginatedZones.length} of {filteredAndSortedZones.length} zones
            {searchTerm && ` matching "${searchTerm}"`}
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-4 w-4" />
            <span>
              {zoneTypeFilter !== 'all' && `Type: ${zoneTypeFilter}`}
              {zoneTypeFilter !== 'all' && statusFilter !== 'all' && ', '}
              {statusFilter !== 'all' && `Status: ${statusFilter}`}
            </span>
          </div>
        </div>
      </Card>

      {/* Zones table */}
      <Card>
        <Table
          data={paginatedZones}
          columns={columns}
          loading={isLoading}
          emptyMessage={
            searchTerm || zoneTypeFilter !== 'all' || statusFilter !== 'all'
              ? "No zones match your current filters."
              : "No DNS zones found. Create your first zone to get started."
          }
          sortKey={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>

                {/* Page numbers */}
                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? "primary" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className="w-8 h-8 p-0"
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
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
      {isRecordModalOpen && (selectedZone || viewingZoneRecords) && (() => {
        const currentZone = viewingZoneRecords || selectedZone
        if (!currentZone) return null

        return (
          <RecordModal
            zoneId={currentZone.id}
            record={selectedRecord}
            isOpen={isRecordModalOpen}
            onClose={() => setIsRecordModalOpen(false)}
            onSuccess={() => {
              setIsRecordModalOpen(false)
              queryClient.invalidateQueries({
                queryKey: ['records', currentZone.id]
              })
            }}
          />
        )
      })()}

      {/* Zone validation modal */}
      {isValidationModalOpen && selectedZone && (
        <ZoneValidationModal
          zone={selectedZone}
          isOpen={isValidationModalOpen}
          onClose={() => setIsValidationModalOpen(false)}
        />
      )}

      {/* Zone import/export modal */}
      {isImportExportModalOpen && (
        <ZoneImportExportModal
          zone={selectedZone || undefined}
          isOpen={isImportExportModalOpen}
          onClose={() => setIsImportExportModalOpen(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['zones'] })
          }}
          mode={importExportMode}
        />
      )}

      {/* Zone statistics modal */}
      {isStatisticsModalOpen && selectedZone && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setIsStatisticsModalOpen(false)} />

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                    Zone Statistics: {selectedZone.name}
                  </h3>
                  <button
                    onClick={() => setIsStatisticsModalOpen(false)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <span className="sr-only">Close</span>
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <ZoneStatistics zone={selectedZone} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DNSZones