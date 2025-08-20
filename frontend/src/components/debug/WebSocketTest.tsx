import React, { useState, useEffect } from 'react'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { Card } from '@/components/ui'

export const WebSocketTest: React.FC = () => {
  const [testMessage, setTestMessage] = useState('')
  const [receivedMessages, setReceivedMessages] = useState<any[]>([])
  
  const {
    isConnected,
    connectionStatus,
    events,
    sendMessage,
    getConnectionStats,
    connectionStats
  } = useRealTimeEvents()

  // Listen for new events
  useEffect(() => {
    if (events.length > 0) {
      setReceivedMessages(prev => [...events.slice(0, 10)]) // Keep last 10 events
    }
  }, [events])

  const sendTestMessage = () => {
    if (testMessage.trim()) {
      sendMessage({
        type: 'test_message',
        data: { message: testMessage, timestamp: new Date().toISOString() }
      })
      setTestMessage('')
    }
  }

  const triggerTestEvent = async () => {
    try {
      const response = await fetch('/api/websocket-demo/emit-dns-event', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          event_type: 'zone_created',
          data: {
            name: `test-zone-${Date.now()}.local`,
            type: 'master',
            records_count: 1
          }
        })
      })
      
      if (response.ok) {
        console.log('Test event triggered successfully')
      }
    } catch (error) {
      console.error('Failed to trigger test event:', error)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">WebSocket Connection Test</h2>
        
        {/* Connection Status */}
        <div className="mb-6">
          <ConnectionStatus showDetails={true} />
        </div>

        {/* Test Controls */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Send Test Message
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="Enter test message..."
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
                onKeyPress={(e) => e.key === 'Enter' && sendTestMessage()}
              />
              <button
                onClick={sendTestMessage}
                disabled={!isConnected || !testMessage.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>

          <div className="flex space-x-2">
            <button
              onClick={triggerTestEvent}
              disabled={!isConnected}
              className="px-4 py-2 bg-green-600 text-white rounded-md text-sm disabled:opacity-50"
            >
              Trigger Test Event
            </button>
            <button
              onClick={getConnectionStats}
              className="px-4 py-2 bg-gray-600 text-white rounded-md text-sm"
            >
              Refresh Stats
            </button>
          </div>
        </div>

        {/* Connection Statistics */}
        {connectionStats && (
          <div className="mt-6 p-4 bg-gray-50 rounded-md">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Connection Statistics</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>Total Users: {connectionStats.total_users}</div>
              <div>Total Connections: {connectionStats.total_connections}</div>
              <div>Messages Sent: {connectionStats.total_messages_sent}</div>
              <div>Queue Size: {connectionStats.queue_size}</div>
              <div>Broadcasting: {connectionStats.broadcasting ? 'Yes' : 'No'}</div>
              <div>Active Tasks: {connectionStats.active_tasks}</div>
            </div>
          </div>
        )}

        {/* Recent Events */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Recent Events ({receivedMessages.length})
          </h3>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {receivedMessages.length === 0 ? (
              <p className="text-sm text-gray-500">No events received yet</p>
            ) : (
              receivedMessages.map((event, index) => (
                <div key={index} className="p-2 bg-white border rounded text-xs">
                  <div className="font-medium">{event.type}</div>
                  <div className="text-gray-600 mt-1">
                    {JSON.stringify(event.data, null, 2)}
                  </div>
                  <div className="text-gray-400 mt-1">{event.timestamp}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

export default WebSocketTest