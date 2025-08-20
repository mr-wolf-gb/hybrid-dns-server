import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export const useWebSocket = (url: string, options: UseWebSocketOptions = {}) => {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null)
  const pingIntervalId = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionStatus('connecting')
    
    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
        onConnect?.()

        // Start ping/pong to keep connection alive
        pingIntervalId.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send('ping')
          }
        }, 30000) // Ping every 30 seconds
      }

      ws.current.onmessage = (event) => {
        if (event.data === 'pong') {
          return // Handle pong response
        }

        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        setConnectionStatus('disconnected')
        onDisconnect?.()

        // Clear ping interval
        if (pingIntervalId.current) {
          clearInterval(pingIntervalId.current)
          pingIntervalId.current = null
        }

        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          reconnectTimeoutId.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.current.onerror = (error) => {
        setConnectionStatus('error')
        onError?.(error)
      }

    } catch (error) {
      setConnectionStatus('error')
      console.error('WebSocket connection error:', error)
    }
  }, [url, onMessage, onConnect, onDisconnect, onError, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current)
      reconnectTimeoutId.current = null
    }

    if (pingIntervalId.current) {
      clearInterval(pingIntervalId.current)
      pingIntervalId.current = null
    }

    if (ws.current) {
      ws.current.close()
      ws.current = null
    }

    setIsConnected(false)
    setConnectionStatus('disconnected')
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
      return true
    }
    return false
  }, [])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    reconnectAttempts: reconnectAttempts.current
  }
}