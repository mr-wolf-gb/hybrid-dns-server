/**
 * WebSocket Service for real-time communication with the backend
 * Provides connection management, event handling, and automatic reconnection
 */

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export interface WebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
  autoReconnect?: boolean
}

export enum ConnectionType {
  HEALTH = 'health',
  DNS_MANAGEMENT = 'dns_management',
  SECURITY = 'security',
  SYSTEM = 'system',
  ADMIN = 'admin'
}

export enum EventType {
  // Health monitoring events
  HEALTH_UPDATE = 'health_update',
  HEALTH_ALERT = 'health_alert',
  FORWARDER_STATUS_CHANGE = 'forwarder_status_change',
  
  // DNS zone events
  ZONE_CREATED = 'zone_created',
  ZONE_UPDATED = 'zone_updated',
  ZONE_DELETED = 'zone_deleted',
  RECORD_CREATED = 'record_created',
  RECORD_UPDATED = 'record_updated',
  RECORD_DELETED = 'record_deleted',
  
  // Security events
  SECURITY_ALERT = 'security_alert',
  RPZ_UPDATE = 'rpz_update',
  THREAT_DETECTED = 'threat_detected',
  
  // System events
  SYSTEM_STATUS = 'system_status',
  BIND_RELOAD = 'bind_reload',
  CONFIG_CHANGE = 'config_change',
  
  // User events
  USER_LOGIN = 'user_login',
  USER_LOGOUT = 'user_logout',
  SESSION_EXPIRED = 'session_expired',
  
  // Connection events
  CONNECTION_ESTABLISHED = 'connection_established',
  SUBSCRIPTION_UPDATED = 'subscription_updated'
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private options: WebSocketOptions
  private reconnectAttempts = 0
  private reconnectTimeoutId: NodeJS.Timeout | null = null
  private pingIntervalId: NodeJS.Timeout | null = null
  private isConnected = false
  private connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error' = 'disconnected'
  private eventHandlers: Map<string, Set<(data: any) => void>> = new Map()
  private messageQueue: WebSocketMessage[] = []
  private subscribedEvents: string[] = []

  constructor(
    connectionType: ConnectionType,
    userId: string,
    options: WebSocketOptions = {}
  ) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//${window.location.host}/ws/${connectionType}/${userId}`
    
    this.options = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      autoReconnect: true,
      ...options
    }
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.connectionStatus = 'connecting'
      
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.isConnected = true
          this.connectionStatus = 'connected'
          this.reconnectAttempts = 0
          this.options.onConnect?.()

          // Start ping/pong to keep connection alive
          this.startPingInterval()
          
          // Process queued messages
          this.processMessageQueue()
          
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = () => {
          this.isConnected = false
          this.connectionStatus = 'disconnected'
          this.options.onDisconnect?.()
          this.stopPingInterval()

          // Attempt to reconnect if enabled
          if (this.options.autoReconnect && this.reconnectAttempts < (this.options.maxReconnectAttempts || 5)) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          this.connectionStatus = 'error'
          this.options.onError?.(error)
          reject(error)
        }

      } catch (error) {
        this.connectionStatus = 'error'
        console.error('WebSocket connection error:', error)
        reject(error)
      }
    })
  }

  disconnect(): void {
    this.options.autoReconnect = false
    
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }

    this.stopPingInterval()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false
    this.connectionStatus = 'disconnected'
  }

  sendMessage(message: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return true
    } else {
      // Queue message for later delivery
      this.messageQueue.push(message)
      return false
    }
  }

  // Event subscription methods
  subscribe(eventType: EventType | string, handler: (data: any) => void): void {
    const eventName = typeof eventType === 'string' ? eventType : eventType
    
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, new Set())
    }
    
    this.eventHandlers.get(eventName)!.add(handler)
  }

  unsubscribe(eventType: EventType | string, handler: (data: any) => void): void {
    const eventName = typeof eventType === 'string' ? eventType : eventType
    
    if (this.eventHandlers.has(eventName)) {
      this.eventHandlers.get(eventName)!.delete(handler)
    }
  }

  subscribeToEvents(eventTypes: (EventType | string)[]): void {
    const events = eventTypes.map(e => typeof e === 'string' ? e : e)
    this.subscribedEvents = events
    
    this.sendMessage({
      type: 'subscribe',
      events: events
    })
  }

  // Utility methods
  ping(): void {
    this.sendMessage({ type: 'ping' })
  }

  getStats(): void {
    this.sendMessage({ type: 'get_stats' })
  }

  getConnectionStatus(): string {
    return this.connectionStatus
  }

  isConnectionOpen(): boolean {
    return this.isConnected
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }

  // Private methods
  private handleMessage(message: WebSocketMessage): void {
    // Call global message handler
    this.options.onMessage?.(message)
    
    // Call specific event handlers
    if (this.eventHandlers.has(message.type)) {
      this.eventHandlers.get(message.type)!.forEach(handler => {
        try {
          handler(message.data)
        } catch (error) {
          console.error(`Error in event handler for ${message.type}:`, error)
        }
      })
    }
    
    // Handle system messages
    this.handleSystemMessage(message)
  }

  private handleSystemMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'pong':
        // Handle pong response
        break
      
      case EventType.CONNECTION_ESTABLISHED:
        console.log('WebSocket connection established:', message.data)
        break
      
      case EventType.SUBSCRIPTION_UPDATED:
        console.log('Event subscription updated:', message.data)
        break
      
      case EventType.SESSION_EXPIRED:
        // Handle session expiration
        console.warn('Session expired, redirecting to login')
        window.location.href = '/login'
        break
      
      case 'stats':
        console.log('WebSocket stats:', message.data)
        break
      
      case 'error':
        console.error('WebSocket error:', message.data)
        break
    }
  }

  private startPingInterval(): void {
    this.pingIntervalId = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ping()
      }
    }, 30000) // Ping every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId)
      this.pingIntervalId = null
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++
    this.reconnectTimeoutId = setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`)
      this.connect().catch(error => {
        console.error('Reconnection failed:', error)
      })
    }, this.options.reconnectInterval)
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()
      if (message) {
        this.ws.send(JSON.stringify(message))
      }
    }
  }
}

// Singleton instances for different connection types
const connections: Map<string, WebSocketService> = new Map()

export function getWebSocketService(
  connectionType: ConnectionType,
  userId: string,
  options?: WebSocketOptions
): WebSocketService {
  const key = `${connectionType}-${userId}`
  
  if (!connections.has(key)) {
    connections.set(key, new WebSocketService(connectionType, userId, options))
  }
  
  return connections.get(key)!
}

export function disconnectAll(): void {
  connections.forEach(service => service.disconnect())
  connections.clear()
}