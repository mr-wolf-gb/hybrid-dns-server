/**
 * WebSocket Status Debug Component
 * Shows the current WebSocket connection status for debugging
 */

import React from 'react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketStatusProps {
  showDetails?: boolean;
}

export const WebSocketStatus: React.FC<WebSocketStatusProps> = ({ showDetails = false }) => {
  const { user, accessToken, isLoading } = useAuth();
  const { 
    isConnected, 
    isConnecting, 
    error, 
    lastMessage,
    getConnectionStats 
  } = useWebSocketContext();

  const stats = getConnectionStats();

  const getStatusColor = () => {
    if (isConnected) return 'text-green-600';
    if (isConnecting) return 'text-yellow-600';
    if (error) return 'text-red-600';
    return 'text-gray-600';
  };

  const getStatusText = () => {
    if (isLoading) return 'Auth Loading...';
    if (!user) return 'Not Authenticated';
    if (isConnected) return 'Connected';
    if (isConnecting) return 'Connecting...';
    if (error) return `Error: ${error}`;
    return 'Disconnected';
  };

  if (!showDetails) {
    return (
      <div className="flex items-center space-x-2 text-sm">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500' : 'bg-red-500'}`} />
        <span className={getStatusColor()}>{getStatusText()}</span>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow border">
      <h3 className="text-lg font-semibold mb-3">WebSocket Status</h3>
      
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span>Status:</span>
          <span className={getStatusColor()}>{getStatusText()}</span>
        </div>
        
        <div className="flex justify-between">
          <span>User:</span>
          <span>{user ? user.username : 'None'}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Has Token:</span>
          <span>{accessToken ? 'Yes' : 'No'}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Auth Loading:</span>
          <span>{isLoading ? 'Yes' : 'No'}</span>
        </div>
        
        {error && (
          <div className="flex justify-between">
            <span>Error:</span>
            <span className="text-red-600">{error}</span>
          </div>
        )}
        
        {lastMessage && (
          <div className="flex justify-between">
            <span>Last Message:</span>
            <span className="text-xs">{lastMessage.type}</span>
          </div>
        )}
        
        {stats && (
          <div className="mt-3 pt-3 border-t">
            <h4 className="font-medium mb-2">Connection Stats</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span>Global Connections:</span>
                <span>{stats.global?.totalConnections || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Pending:</span>
                <span>{stats.global?.pendingConnections || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WebSocketStatus;