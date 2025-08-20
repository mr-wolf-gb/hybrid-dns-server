import React, { useState, useMemo } from 'react'
import {
  FolderIcon,
  FolderOpenIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Squares2X2Icon,
  ListBulletIcon,
} from '@heroicons/react/24/outline'
import { Forwarder } from '@/types'
import { Button, Badge } from '@/components/ui'
import ForwarderHealthIndicator from './ForwarderHealthIndicator'

interface ForwarderGroupingProps {
  forwarders: Forwarder[]
  onForwarderSelect?: (forwarder: Forwarder) => void
  onForwarderEdit?: (forwarder: Forwarder) => void
  onForwarderTest?: (forwarder: Forwarder) => void
  onForwarderToggle?: (forwarder: Forwarder) => void
  onForwarderDelete?: (forwarder: Forwarder) => void
}

type GroupBy = 'type' | 'status' | 'health' | 'none'
type ViewMode = 'grid' | 'list'

interface ForwarderGroup {
  key: string
  label: string
  count: number
  forwarders: Forwarder[]
  color: string
}

const ForwarderGrouping: React.FC<ForwarderGroupingProps> = ({
  forwarders,
  onForwarderSelect,
  onForwarderEdit: _onForwarderEdit,
  onForwarderTest: _onForwarderTest,
  onForwarderToggle: _onForwarderToggle,
  onForwarderDelete: _onForwarderDelete,
}) => {
  const [groupBy, setGroupBy] = useState<GroupBy>('type')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['all']))

  const groups = useMemo(() => {
    if (groupBy === 'none') {
      return [{
        key: 'all',
        label: 'All Forwarders',
        count: forwarders.length,
        forwarders,
        color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
      }]
    }

    const groupMap = new Map<string, Forwarder[]>()

    forwarders.forEach(forwarder => {
      let groupKey: string
      
      switch (groupBy) {
        case 'type':
          groupKey = forwarder.type
          break
        case 'status':
          groupKey = forwarder.is_active ? 'active' : 'inactive'
          break
        case 'health':
          groupKey = forwarder.health_status
          break
        default:
          groupKey = 'all'
      }

      if (!groupMap.has(groupKey)) {
        groupMap.set(groupKey, [])
      }
      groupMap.get(groupKey)!.push(forwarder)
    })

    const result: ForwarderGroup[] = []
    
    groupMap.forEach((groupForwarders, key) => {
      let label: string
      let color: string

      switch (groupBy) {
        case 'type':
          switch (key) {
            case 'ad':
              label = 'Active Directory'
              color = 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
              break
            case 'intranet':
              label = 'Intranet'
              color = 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
              break
            case 'public':
              label = 'Public DNS'
              color = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
              break
            default:
              label = key
              color = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          }
          break
        case 'status':
          label = key === 'active' ? 'Active' : 'Inactive'
          color = key === 'active' 
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          break
        case 'health':
          switch (key) {
            case 'healthy':
              label = 'Healthy'
              color = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
              break
            case 'unhealthy':
              label = 'Unhealthy'
              color = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
              break
            case 'unknown':
              label = 'Unknown'
              color = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
              break
            default:
              label = key
              color = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          }
          break
        default:
          label = key
          color = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
      }

      result.push({
        key,
        label,
        count: groupForwarders.length,
        forwarders: groupForwarders.sort((a, b) => a.name.localeCompare(b.name)),
        color,
      })
    })

    return result.sort((a, b) => a.label.localeCompare(b.label))
  }, [forwarders, groupBy])

  const toggleGroup = (groupKey: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey)
    } else {
      newExpanded.add(groupKey)
    }
    setExpandedGroups(newExpanded)
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'ad':
        return 'AD'
      case 'intranet':
        return 'Intranet'
      case 'public':
        return 'Public'
      default:
        return type
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
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Group by:
            </label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="type">Type</option>
              <option value="status">Status</option>
              <option value="health">Health</option>
              <option value="none">None</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'grid' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Squares2X2Icon className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <ListBulletIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Groups */}
      <div className="space-y-4">
        {groups.map((group) => (
          <div key={group.key} className="border border-gray-200 dark:border-gray-700 rounded-lg">
            {/* Group Header */}
            <div
              className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
              onClick={() => toggleGroup(group.key)}
            >
              <div className="flex items-center space-x-3">
                {expandedGroups.has(group.key) ? (
                  <>
                    <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                    <FolderOpenIcon className="h-5 w-5 text-gray-500" />
                  </>
                ) : (
                  <>
                    <ChevronRightIcon className="h-4 w-4 text-gray-500" />
                    <FolderIcon className="h-5 w-5 text-gray-500" />
                  </>
                )}
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {group.label}
                </span>
                <Badge className={group.color}>
                  {group.count}
                </Badge>
              </div>
            </div>

            {/* Group Content */}
            {expandedGroups.has(group.key) && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                {viewMode === 'grid' ? (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {group.forwarders.map((forwarder) => (
                      <div
                        key={forwarder.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => onForwarderSelect?.(forwarder)}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                              {forwarder.name}
                            </h4>
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                              {forwarder.domain}
                            </p>
                          </div>
                          <Badge className={getTypeColor(forwarder.type)} size="sm">
                            {getTypeLabel(forwarder.type)}
                          </Badge>
                        </div>
                        
                        <div className="space-y-2">
                          <ForwarderHealthIndicator forwarder={forwarder} />
                          
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            Servers: {forwarder.servers.length}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {group.forwarders.map((forwarder) => (
                      <div
                        key={forwarder.id}
                        className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
                        onClick={() => onForwarderSelect?.(forwarder)}
                      >
                        <div className="flex items-center space-x-4 flex-1 min-w-0">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                {forwarder.name}
                              </h4>
                              <Badge className={getTypeColor(forwarder.type)} size="sm">
                                {getTypeLabel(forwarder.type)}
                              </Badge>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                              {forwarder.domain} • {forwarder.servers.length} servers
                            </p>
                          </div>
                          
                          <ForwarderHealthIndicator forwarder={forwarder} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default ForwarderGrouping