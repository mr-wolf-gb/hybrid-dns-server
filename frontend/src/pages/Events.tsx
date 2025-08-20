/**
 * Events page for event monitoring and replay functionality
 */

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import EventMonitor from '../components/events/EventMonitor';
import EventReplay from '../components/events/EventReplay';
import { useWebSocketContext } from '../contexts/WebSocketContext';
import { useAuth } from '../contexts/AuthContext';
import { 
  Activity, 
  RotateCcw, 
  Wifi, 
  WifiOff, 
  Settings,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

const Events: React.FC = () => {
  const { user } = useAuth();
  const { getConnectionStats } = useWebSocketContext();
  const [activeTab, setActiveTab] = useState('monitor');

  const connectionStats = getConnectionStats();

  // Calculate overall connection status
  const connectedCount = Object.values(connectionStats).filter(
    (conn: any) => conn && conn.connected
  ).length;
  const totalConnections = Object.values(connectionStats).filter(
    (conn: any) => conn !== null
  ).length;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Event Broadcasting</h1>
        <p className="text-gray-600">
          Monitor real-time events and replay historical data for analysis and debugging.
        </p>
      </div>

      {/* Connection Status */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Connection Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(connectionStats).map(([type, stats]: [string, any]) => {
              if (!stats) return null;
              
              return (
                <div key={type} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <div className="font-medium capitalize">{type}</div>
                    <div className="text-sm text-gray-500">
                      {stats.error ? 'Error' : stats.connected ? 'Connected' : 'Disconnected'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {stats.connected ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : stats.error ? (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    ) : (
                      <WifiOff className="h-5 w-5 text-gray-400" />
                    )}
                    {stats.reconnectAttempts > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {stats.reconnectAttempts} retries
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Overall Status:</span>
              <div className="flex items-center gap-2">
                {connectedCount === totalConnections ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : connectedCount > 0 ? (
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-500" />
                )}
                <span className="text-sm">
                  {connectedCount} / {totalConnections} connections active
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="monitor" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Real-time Monitor
          </TabsTrigger>
          <TabsTrigger value="replay" className="flex items-center gap-2">
            <RotateCcw className="h-4 w-4" />
            Event Replay
          </TabsTrigger>
        </TabsList>

        <TabsContent value="monitor" className="mt-6">
          <EventMonitor />
        </TabsContent>

        <TabsContent value="replay" className="mt-6">
          <EventReplay />
        </TabsContent>
      </Tabs>

      {/* Help Section */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>About Event Broadcasting</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-2">Real-time Monitor</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• View live events as they occur</li>
                <li>• Filter by category, severity, source, and type</li>
                <li>• Search through event data</li>
                <li>• Export events for analysis</li>
                <li>• Pause/resume monitoring</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Event Replay</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Replay historical events</li>
                <li>• Configurable time ranges and filters</li>
                <li>• Variable replay speeds (1x to 10x)</li>
                <li>• Debug issues and analyze patterns</li>
                <li>• Multiple concurrent replays</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Event Categories</h4>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              <Badge variant="outline">Health</Badge>
              <Badge variant="outline">DNS Management</Badge>
              <Badge variant="outline">Security</Badge>
              <Badge variant="outline">System</Badge>
              <Badge variant="outline">User Actions</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Events;