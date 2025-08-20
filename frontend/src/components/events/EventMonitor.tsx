/**
 * Real-time Event Monitor component for displaying live events
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useWebSocketContext, WebSocketMessage } from '../../contexts/WebSocketContext';
import { ScrollArea } from '../ui/scroll-area';
import { 
  Activity, 
  Filter, 
  Pause, 
  Play, 
  Trash2, 
  Download,
  Search,
  Clock,
  AlertTriangle,
  Info,
  AlertCircle,
  XCircle
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '../../lib/utils';

interface EventEntry extends WebSocketMessage {
  id: string;
  receivedAt: Date;
}

interface EventFilter {
  search: string;
  category: string;
  severity: string;
  source: string;
  eventType: string;
}

const EventMonitor: React.FC = () => {
  const { registerEventHandler, unregisterEventHandler } = useWebSocketContext();
  const [events, setEvents] = useState<EventEntry[]>([]);
  const [filteredEvents, setFilteredEvents] = useState<EventEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState<EventFilter>({
    search: '',
    category: '',
    severity: '',
    source: '',
    eventType: ''
  });
  const [maxEvents, setMaxEvents] = useState(1000);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Handle incoming events
  const handleEvent = useCallback((message: WebSocketMessage) => {
    if (isPaused) return;

    const eventEntry: EventEntry = {
      ...message,
      id: `${Date.now()}-${Math.random()}`,
      receivedAt: new Date()
    };

    setEvents(prev => {
      const updated = [eventEntry, ...prev];
      return updated.slice(0, maxEvents);
    });
  }, [isPaused, maxEvents]);

  // Register event handler for all events
  useEffect(() => {
    registerEventHandler('event-monitor', ['*'], handleEvent);

    return () => {
      unregisterEventHandler('event-monitor');
    };
  }, [registerEventHandler, unregisterEventHandler, handleEvent]);

  // Filter events
  useEffect(() => {
    let filtered = events;

    if (filter.search) {
      const searchLower = filter.search.toLowerCase();
      filtered = filtered.filter(event => 
        event.type.toLowerCase().includes(searchLower) ||
        JSON.stringify(event.data).toLowerCase().includes(searchLower) ||
        (event.source && event.source.toLowerCase().includes(searchLower))
      );
    }

    if (filter.category) {
      filtered = filtered.filter(event => event.category === filter.category);
    }

    if (filter.severity) {
      filtered = filtered.filter(event => event.severity === filter.severity);
    }

    if (filter.source) {
      filtered = filtered.filter(event => event.source === filter.source);
    }

    if (filter.eventType) {
      filtered = filtered.filter(event => event.type === filter.eventType);
    }

    setFilteredEvents(filtered);
  }, [events, filter]);

  // Auto-scroll to top when new events arrive
  useEffect(() => {
    if (autoScroll && scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = 0;
    }
  }, [filteredEvents, autoScroll]);

  // Get unique values for filter dropdowns
  const getUniqueValues = (field: keyof EventEntry) => {
    const values = events
      .map(event => event[field])
      .filter((value, index, array) => value && array.indexOf(value) === index)
      .sort();
    return values as string[];
  };

  // Get severity icon and color
  const getSeverityDisplay = (severity?: string) => {
    switch (severity) {
      case 'critical':
        return { icon: XCircle, color: 'text-red-500', bgColor: 'bg-red-50' };
      case 'error':
        return { icon: AlertCircle, color: 'text-red-400', bgColor: 'bg-red-50' };
      case 'warning':
        return { icon: AlertTriangle, color: 'text-yellow-500', bgColor: 'bg-yellow-50' };
      case 'info':
        return { icon: Info, color: 'text-blue-500', bgColor: 'bg-blue-50' };
      default:
        return { icon: Activity, color: 'text-gray-500', bgColor: 'bg-gray-50' };
    }
  };

  // Clear all events
  const clearEvents = () => {
    setEvents([]);
  };

  // Export events to JSON
  const exportEvents = () => {
    const dataStr = JSON.stringify(filteredEvents, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `events-${format(new Date(), 'yyyy-MM-dd-HH-mm-ss')}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  // Toggle pause/resume
  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Real-time Event Monitor
              <Badge variant="outline">
                {filteredEvents.length} / {events.length} events
              </Badge>
              {isPaused && (
                <Badge variant="secondary">Paused</Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={togglePause}
              >
                {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={exportEvents}
                disabled={filteredEvents.length === 0}
              >
                <Download className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={clearEvents}
                disabled={events.length === 0}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search events..."
                value={filter.search}
                onChange={(e) => setFilter(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            
            <Select
              value={filter.category}
              onValueChange={(value) => setFilter(prev => ({ ...prev, category: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Categories</SelectItem>
                {getUniqueValues('category').map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select
              value={filter.severity}
              onValueChange={(value) => setFilter(prev => ({ ...prev, severity: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Severities</SelectItem>
                {getUniqueValues('severity').map((severity) => (
                  <SelectItem key={severity} value={severity}>
                    {severity}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select
              value={filter.source}
              onValueChange={(value) => setFilter(prev => ({ ...prev, source: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Sources</SelectItem>
                {getUniqueValues('source').map((source) => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select
              value={filter.eventType}
              onValueChange={(value) => setFilter(prev => ({ ...prev, eventType: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Event Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                {getUniqueValues('type').map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setFilter({
                  search: '',
                  category: '',
                  severity: '',
                  source: '',
                  eventType: ''
                })}
              >
                <Filter className="h-4 w-4 mr-1" />
                Clear
              </Button>
            </div>
          </div>
          
          {/* Settings */}
          <div className="flex items-center gap-4 mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Max Events:</label>
              <Select
                value={maxEvents.toString()}
                onValueChange={(value) => setMaxEvents(parseInt(value))}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="500">500</SelectItem>
                  <SelectItem value="1000">1000</SelectItem>
                  <SelectItem value="2000">2000</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto-scroll"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded"
              />
              <label htmlFor="auto-scroll" className="text-sm font-medium">
                Auto-scroll
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Event List */}
      <Card>
        <CardContent className="p-0">
          <ScrollArea className="h-[600px]" ref={scrollAreaRef}>
            <div className="p-4 space-y-2">
              {filteredEvents.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {events.length === 0 ? (
                    <div>
                      <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No events received yet</p>
                      <p className="text-sm">Events will appear here in real-time</p>
                    </div>
                  ) : (
                    <div>
                      <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No events match the current filters</p>
                      <p className="text-sm">Try adjusting your filter criteria</p>
                    </div>
                  )}
                </div>
              ) : (
                filteredEvents.map((event) => {
                  const severityDisplay = getSeverityDisplay(event.severity);
                  const SeverityIcon = severityDisplay.icon;
                  
                  return (
                    <div
                      key={event.id}
                      className={cn(
                        "border rounded-lg p-3 transition-colors",
                        severityDisplay.bgColor
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <SeverityIcon className={cn("h-5 w-5 mt-0.5 flex-shrink-0", severityDisplay.color)} />
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="text-xs">
                                {event.type}
                              </Badge>
                              {event.category && (
                                <Badge variant="secondary" className="text-xs">
                                  {event.category}
                                </Badge>
                              )}
                              {event.source && (
                                <Badge variant="outline" className="text-xs">
                                  {event.source}
                                </Badge>
                              )}
                            </div>
                            
                            <div className="text-sm text-gray-900 mb-2">
                              {event.data && typeof event.data === 'object' ? (
                                <pre className="whitespace-pre-wrap font-mono text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(event.data, null, 2)}
                                </pre>
                              ) : (
                                <span>{event.data?.toString() || 'No data'}</span>
                              )}
                            </div>
                            
                            {event.tags && event.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mb-2">
                                {event.tags.map((tag, index) => (
                                  <Badge key={index} variant="outline" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="text-right text-xs text-gray-500 flex-shrink-0">
                          <div className="flex items-center gap-1 mb-1">
                            <Clock className="h-3 w-3" />
                            {format(event.receivedAt, 'HH:mm:ss')}
                          </div>
                          <div>
                            {format(event.receivedAt, 'MMM dd')}
                          </div>
                          {event.event_id && (
                            <div className="text-xs text-gray-400 mt-1">
                              {event.event_id.slice(0, 8)}...
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};

export default EventMonitor;