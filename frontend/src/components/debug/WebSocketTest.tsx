import React, { useState, useEffect } from 'react'
import { useRealTimeEvents } from '@/contexts/RealTimeEventContext'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { Card } from '@/components/ui'
import { testWebSocketConnection, testAllWebSocketConnections, checkWebSocketHealth } from '@/utils/websocketTest'

export const WebSocketTest: React.FC = () => {
  const [testMessage, setTestMessage] = useState('')
  const [receivedMessages, setReceivedMessages] = useState<any[]>([])
  const [debugResults, setDebugResults] = useState<any>(null)
  const [healthStatus, setHealthStatus] = useState<any>(null)
  const [debugLoading, setDebugLoading] = useState(false)

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

  const handleTestConnection = async (connectionType: string) => {
    setDebugLoading(true)
    try {
      const result = await testWebSocketConnection(connectionType)
      setDebugResults({ [connectionType]: result })
    } catch (error) {
      setDebugResults({ [connectionType]: { success: false, error: String(error) } })
    } finally {
      setDebugLoading(false)
    }
  }

  const handleTestAllConnections = async () => {
    setDebugLoading(true)
    try {
      const results = await testAllWebSocketConnections()
      setDebugResults(results)
    } catch (error) {
      setDebugResults({ error: String(error) })
    } finally {
      setDebugLoading(false)
    }
  }

  const handleHealthCheck = async () => {
    setDebugLoading(true)
    try {
      const health = await checkWebSocketHealth()
      setHealthStatus(health)
    } catch (error) {
      setHealthStatus({ error: String(error) })
    } finally {
      setDebugLoading(false)
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

          <div className="flex flex-wrap gap-2">
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

          {/* Debug Tools */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Debug Tools</h3>
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                onClick={() => handleTestConnection('health')}
                disabled={debugLoading}
                className="px-3 py-1 bg-blue-500 text-white rounded text-sm disabled:opacity-50"
              >
                Test Health
              </button>
              <button
                onClick={() => handleTestConnection('system')}
                disabled={debugLoading}
                className="px-3 py-1 bg-green-500 text-white rounded text-sm disabled:opacity-50"
              >
                Test System
              </button>
              <button
                onClick={() => handleTestConnection('dns_management')}
                disabled={debugLoading}
                className="px-3 py-1 bg-purple-500 text-white rounded text-sm disabled:opacity-50"
              >
                Test DNS
              </button>
              <button
                onClick={() => handleTestConnection('security')}
                disabled={debugLoading}
                className="px-3 py-1 bg-red-500 text-white rounded text-sm disabled:opacity-50"
              >
                Test Security
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleTestAllConnections}
                disabled={debugLoading}
                className="px-4 py-2 bg-indigo-500 text-white rounded text-sm disabled:opacity-50"
              >
                Test All Connections
              </button>
              <button
                onClick={handleHealthCheck}
                disabled={debugLoading}
                className="px-4 py-2 bg-orange-500 text-white rounded text-sm disabled:opacity-50"
              >
                Check Service Health
              </button>
            </div>
            {debugLoading && (
              <div className="text-blue-600 text-sm mt-2">Running diagnostics...</div>
            )}
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

        {/* Debug Results */}
        {debugResults && (
          <div className="mt-6 p-4 bg-gray-50 rounded-md">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Debug Results</h3>
            <pre className="text-xs overflow-auto max-h-32 bg-white p-2 rounded border">
              {JSON.stringify(debugResults, null, 2)}
            </pre>
          </div>
        )}

        {/* Health Status */}
        {healthStatus && (
          <div className="mt-6 p-4 bg-gray-50 rounded-md">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Service Health</h3>
            <pre className="text-xs overflow-auto max-h-32 bg-white p-2 rounded border">
              {JSON.stringify(healthStatus, null, 2)}
            </pre>
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