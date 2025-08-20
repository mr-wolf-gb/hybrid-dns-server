/**
 * Event Replay component for replaying historical events
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import { Play, Square, RotateCcw, Clock, Filter, Settings } from 'lucide-react';
import { format } from 'date-fns';

interface EventReplayConfig {
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  filter_config: {
    event_types?: string[];
    event_categories?: string[];
    event_sources?: string[];
    severity_levels?: string[];
    user_ids?: string[];
  };
  replay_speed: number;
}

interface ActiveReplay {
  replay_id: string;
  name: string;
  status: string;
  progress: number;
  total_events: number;
  processed_events: number;
  start_time: string;
  end_time: string;
  replay_speed: number;
}

const EventReplay: React.FC = () => {
  const { user } = useAuth();
  const { registerEventHandler, unregisterEventHandler, startEventReplay, stopEventReplay } = useWebSocketContext();
  
  const [isConfiguring, setIsConfiguring] = useState(false);
  const [activeReplays, setActiveReplays] = useState<ActiveReplay[]>([]);
  const [replayConfig, setReplayConfig] = useState<EventReplayConfig>({
    name: '',
    description: '',
    start_time: '',
    end_time: '',
    filter_config: {},
    replay_speed: 1
  });

  // Available filter options
  const eventCategories = ['health', 'dns', 'security', 'system', 'user'];
  const severityLevels = ['debug', 'info', 'warning', 'error', 'critical'];
  const replaySpeeds = [
    { value: 1, label: '1x (Real-time)' },
    { value: 2, label: '2x (2x Speed)' },
    { value: 5, label: '5x (5x Speed)' },
    { value: 10, label: '10x (10x Speed)' }
  ];

  // Handle replay events
  const handleReplayEvent = useCallback((message: any) => {
    if (message.type === 'replay_started') {
      const newReplay: ActiveReplay = {
        replay_id: message.data.replay_id,
        name: message.data.name,
        status: message.data.status,
        progress: 0,
        total_events: 0,
        processed_events: 0,
        start_time: replayConfig.start_time,
        end_time: replayConfig.end_time,
        replay_speed: replayConfig.replay_speed
      };
      setActiveReplays(prev => [...prev, newReplay]);
      toast.success(`Event replay "${message.data.name}" started`);
      setIsConfiguring(false);
    } else if (message.type === 'replay_status') {
      setActiveReplays(prev => prev.map(replay => 
        replay.replay_id === message.data.replay_id
          ? { ...replay, ...message.data }
          : replay
      ));
    } else if (message.type === 'replay_stopped') {
      if (message.data.success) {
        setActiveReplays(prev => prev.filter(replay => replay.replay_id !== message.data.replay_id));
        toast.success('Event replay stopped');
      }
    } else if (message.type === 'event_replay') {
      // Handle replayed events - you can display them in a separate component
      console.log('Replayed event:', message.original_event);
    }
  }, [replayConfig]);

  // Register event handler
  useEffect(() => {
    registerEventHandler('event-replay', [
      'replay_started',
      'replay_status',
      'replay_stopped',
      'event_replay'
    ], handleReplayEvent);

    return () => {
      unregisterEventHandler('event-replay');
    };
  }, [registerEventHandler, unregisterEventHandler, handleReplayEvent]);

  // Handle form input changes
  const handleInputChange = (field: keyof EventReplayConfig, value: any) => {
    setReplayConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFilterChange = (filterType: string, values: string[]) => {
    setReplayConfig(prev => ({
      ...prev,
      filter_config: {
        ...prev.filter_config,
        [filterType]: values.length > 0 ? values : undefined
      }
    }));
  };

  // Start replay
  const handleStartReplay = () => {
    if (!replayConfig.name || !replayConfig.start_time || !replayConfig.end_time) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (new Date(replayConfig.end_time) <= new Date(replayConfig.start_time)) {
      toast.error('End time must be after start time');
      return;
    }

    startEventReplay(replayConfig);
  };

  // Stop replay
  const handleStopReplay = (replayId: string) => {
    stopEventReplay(replayId);
  };

  // Set default time range (last 24 hours)
  const setDefaultTimeRange = () => {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    setReplayConfig(prev => ({
      ...prev,
      start_time: yesterday.toISOString().slice(0, 16),
      end_time: now.toISOString().slice(0, 16)
    }));
  };

  // Set time range for last week
  const setLastWeekRange = () => {
    const now = new Date();
    const lastWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    setReplayConfig(prev => ({
      ...prev,
      start_time: lastWeek.toISOString().slice(0, 16),
      end_time: now.toISOString().slice(0, 16)
    }));
  };

  return (
    <div className="space-y-6">
      {/* Active Replays */}
      {activeReplays.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              Active Replays
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activeReplays.map((replay) => (
                <div key={replay.replay_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h4 className="font-medium">{replay.name}</h4>
                      <p className="text-sm text-gray-500">
                        {format(new Date(replay.start_time), 'MMM dd, yyyy HH:mm')} - {format(new Date(replay.end_time), 'MMM dd, yyyy HH:mm')}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={replay.status === 'running' ? 'default' : 'secondary'}>
                        {replay.status}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStopReplay(replay.replay_id)}
                        disabled={replay.status !== 'running'}
                      >
                        <Square className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress: {replay.processed_events} / {replay.total_events} events</span>
                      <span>{replay.progress}%</span>
                    </div>
                    <Progress value={replay.progress} className="h-2" />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Speed: {replay.replay_speed}x</span>
                      <span>ID: {replay.replay_id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Replay Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5" />
              Event Replay
            </div>
            <Button
              variant="outline"
              onClick={() => setIsConfiguring(!isConfiguring)}
            >
              <Settings className="h-4 w-4 mr-2" />
              {isConfiguring ? 'Cancel' : 'Configure'}
            </Button>
          </CardTitle>
        </CardHeader>
        
        {isConfiguring && (
          <CardContent className="space-y-6">
            {/* Basic Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="replay-name">Replay Name *</Label>
                <Input
                  id="replay-name"
                  value={replayConfig.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Enter replay name"
                />
              </div>
              
              <div>
                <Label htmlFor="replay-speed">Replay Speed</Label>
                <Select
                  value={replayConfig.replay_speed.toString()}
                  onValueChange={(value) => handleInputChange('replay_speed', parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {replaySpeeds.map((speed) => (
                      <SelectItem key={speed.value} value={speed.value.toString()}>
                        {speed.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="replay-description">Description</Label>
              <Textarea
                id="replay-description"
                value={replayConfig.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </div>

            {/* Time Range */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Time Range *
                </Label>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={setDefaultTimeRange}>
                    Last 24h
                  </Button>
                  <Button size="sm" variant="outline" onClick={setLastWeekRange}>
                    Last Week
                  </Button>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="start-time">Start Time</Label>
                  <Input
                    id="start-time"
                    type="datetime-local"
                    value={replayConfig.start_time}
                    onChange={(e) => handleInputChange('start_time', e.target.value)}
                  />
                </div>
                
                <div>
                  <Label htmlFor="end-time">End Time</Label>
                  <Input
                    id="end-time"
                    type="datetime-local"
                    value={replayConfig.end_time}
                    onChange={(e) => handleInputChange('end_time', e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Event Filters */}
            <div className="space-y-4">
              <Label className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Event Filters (Optional)
              </Label>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Event Categories</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {eventCategories.map((category) => (
                      <Badge
                        key={category}
                        variant={replayConfig.filter_config.event_categories?.includes(category) ? 'default' : 'outline'}
                        className="cursor-pointer"
                        onClick={() => {
                          const current = replayConfig.filter_config.event_categories || [];
                          const updated = current.includes(category)
                            ? current.filter(c => c !== category)
                            : [...current, category];
                          handleFilterChange('event_categories', updated);
                        }}
                      >
                        {category}
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <div>
                  <Label>Severity Levels</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {severityLevels.map((severity) => (
                      <Badge
                        key={severity}
                        variant={replayConfig.filter_config.severity_levels?.includes(severity) ? 'default' : 'outline'}
                        className="cursor-pointer"
                        onClick={() => {
                          const current = replayConfig.filter_config.severity_levels || [];
                          const updated = current.includes(severity)
                            ? current.filter(s => s !== severity)
                            : [...current, severity];
                          handleFilterChange('severity_levels', updated);
                        }}
                      >
                        {severity}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsConfiguring(false)}>
                Cancel
              </Button>
              <Button onClick={handleStartReplay}>
                <Play className="h-4 w-4 mr-2" />
                Start Replay
              </Button>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Help Text */}
      <Card>
        <CardContent className="pt-6">
          <div className="text-sm text-gray-600 space-y-2">
            <p><strong>Event Replay</strong> allows you to replay historical events in real-time or at accelerated speeds.</p>
            <p>Use this feature to:</p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Debug issues by replaying events from a specific time period</li>
              <li>Analyze system behavior during incidents</li>
              <li>Test event handling and monitoring systems</li>
              <li>Review security events and alerts</li>
            </ul>
            <p className="text-amber-600">
              <strong>Note:</strong> Event replay is limited to 7 days maximum duration to prevent system overload.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EventReplay;