/**
 * Unified WebSocket Service for single connection per user
 * Replaces multiple connection types with dynamic subscription management
 */

import { 
  ConnectionHealthManager, 
  GracefulDegradationManager, 
  NetworkStatusMonitor,
  ConnectionStatus,
  ConnectionHealth
} from './ConnectionHealthManager'

export interface WebSocketMessage {
  id: string
  type: EventType
  data: any
  timestamp: string
  priority: EventPriority
  metadata?: Record<string, any>
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
  SUBSCRIPTION_UPDATED = 'subscription_updated',

  // System messages
  PING = 'ping',
  PONG = 'pong',
  ERROR = 'error',
  STATS = 'stats'
}

export enum EventPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface SubscriptionRequest {
  type: 'subscribe' | 'unsubscribe'
  event_types: EventType[]
}

export interface EventHandler {
  id: string
  eventTypes: EventType[]
  handler: (data: any) => void
}

export class UnifiedWebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private options: WebSocketOptions
  private isConnected = false
  
  // Health and recovery management
  private healthManager: ConnectionHealthManager
  private degradationManager: GracefulDegradationManager
  private networkMonitor: NetworkStatusMonitor
  
  // Event management
  private eventHandlers: Map<string, EventHandler> = new Map()
  private subscriptions: Set<EventType> = new Set()
  
  // Message management
  private messageQueue: WebSocketMessage[] = []
  private connectionStats = {
    messagesReceived: 0,
    messagesSent: 0,
    reconnectCount: 0,
    lastConnected: null as Date | null,
    uptime: 0
  }

  constructor(token: string, options: WebSocketOptions = {}) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//${window.location.host}/api/websocket/ws?token=${encodeURIComponent(token)}`

    this.options = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      autoReconnect: true,
      ...options
    }

    // Initialize health and recovery managers
    this.healthManager = new ConnectionHealthManager({
      reconnectInterval: this.options.reconnectInterval,
      maxReconnectAttempts: this.options.maxReconnectAttempts
    })

    this.degradationManager = new GracefulDegradationManager()
    this.networkMonitor = new NetworkStatusMonitor()

    this.setupHealthCallbacks()
    this.setupNetworkMonitoring()
  }

  /**
   * Establish WebSocket connection
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      // Connection is being established

      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.isConnected = true
          this.connectionStats.lastConnected = new Date()

          this.options.onConnect?.()
          this.healthManager.startHealthMonitoring()
          this.degradationManager.disableOfflineMode(this.processOfflineQueue.bind(this))
          this.processMessageQueue()

          // Re-subscribe to previously subscribed events
          if (this.subscriptions.size > 0) {
            this.subscribeToEvents(Array.from(this.subscriptions))
          }

          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.connectionStats.messagesReceived++
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          this.isConnected = false
          this.options.onDisconnect?.()
          this.healthManager.handleConnectionLoss()
          this.degradationManager.enableOfflineMode()

          // Check if close was due to authentication issues
          if (event.code === 1008 || event.code === 4001) {
            console.warn('WebSocket closed due to authentication issues, not reconnecting')
            this.options.autoReconnect = false
            return
          }

          // Attempt to reconnect if enabled
          if (this.options.autoReconnect) {
            this.healthManager.startReconnection(() => this.connect())
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket connection error:', error)
          this.options.onError?.(error)
          this.healthManager.handleConnectionLoss()
          reject(new Error('WebSocket connection failed'))
        }

      } catch (error) {
        // Connection error occurred
        console.error('WebSocket connection error:', error)
        reject(error)
      }
    })
  }

  /**
   * Disconnect WebSocket connection
   */
  disconnect(): void {
    this.options.autoReconnect = false
    this.healthManager.stopHealthMonitoring()
    this.healthManager.stopReconnection()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false
  }

  /**
   * Subscribe to specific event types
   */
  async subscribeToEvents(eventTypes: EventType[]): Promise<void> {
    // Add to local subscriptions
    eventTypes.forEach(eventType => this.subscriptions.add(eventType))

    // Send subscription request to server
    const subscriptionRequest: SubscriptionRequest = {
      type: 'subscribe',
      event_types: eventTypes
    }

    this.sendMessage(subscriptionRequest)
  }

  /**
   * Unsubscribe from specific event types
   */
  async unsubscribeFromEvents(eventTypes: EventType[]): Promise<void> {
    // Remove from local subscriptions
    eventTypes.forEach(eventType => this.subscriptions.delete(eventType))

    // Send unsubscription request to server
    const unsubscriptionRequest: SubscriptionRequest = {
      type: 'unsubscribe',
      event_types: eventTypes
    }

    this.sendMessage(unsubscriptionRequest)
  }

  /**
   * Register event handler for specific event types
   */
  registerEventHandler(id: string, eventTypes: EventType[], handler: (data: any) => void): void {
    this.eventHandlers.set(id, { id, eventTypes, handler })
  }

  /**
   * Unregister event handler
   */
  unregisterEventHandler(id: string): void {
    this.eventHandlers.delete(id)
  }

  /**
   * Send message to server
   */
  sendMessage(message: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      this.connectionStats.messagesSent++
      return true
    } else {
      // Try to queue in offline mode, otherwise add to message queue
      if (!this.degradationManager.queueOperation(message)) {
        this.messageQueue.push(message)
      }
      return false
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): ConnectionStatus {
    return this.healthManager.getStatus()
  }

  /**
   * Check if connection is open
   */
  isConnectionOpen(): boolean {
    return this.isConnected
  }

  /**
   * Check if connection is healthy
   */
  isConnectionHealthy(): boolean {
    return this.healthManager.isHealthy()
  }

  /**
   * Get connection health information
   */
  getConnectionHealth(): ConnectionHealth {
    return this.healthManager.getHealth()
  }

  /**
   * Get connection statistics
   */
  getConnectionStats() {
    const health = this.healthManager.getHealth()
    return {
      ...this.connectionStats,
      uptime: health.uptime,
      subscriptions: Array.from(this.subscriptions),
      eventHandlers: this.eventHandlers.size,
      queuedMessages: this.messageQueue.length,
      offlineQueueSize: this.degradationManager.getQueuedOperationsCount(),
      isOfflineMode: this.degradationManager.isInOfflineMode(),
      health
    }
  }

  /**
   * Get current subscriptions
   */
  getSubscriptions(): EventType[] {
    return Array.from(this.subscriptions)
  }

  /**
   * Send ping to server
   */
  ping(): void {
    this.sendMessage({ type: EventType.PING })
  }

  /**
   * Force health check
   */
  performHealthCheck(): void {
    this.healthManager.performHealthCheck()
  }

  // Private methods

  private handleMessage(message: WebSocketMessage): void {
    // Call global message handler
    this.options.onMessage?.(message)

    // Call specific event handlers
    this.eventHandlers.forEach(({ eventTypes, handler }) => {
      if (eventTypes.includes(message.type)) {
        try {
          handler(message.data)
        } catch (error) {
          console.error(`Error in event handler:`, error)
        }
      }
    })

    // Handle system messages
    this.handleSystemMessage(message)
  }

  private handleSystemMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case EventType.PONG:
        this.healthManager.handlePong()
        break

      case EventType.CONNECTION_ESTABLISHED:
        console.log('WebSocket connection established:', message.data)
        break

      case EventType.SUBSCRIPTION_UPDATED:
        console.log('Event subscription updated:', message.data)
        break

      case EventType.SESSION_EXPIRED:
        console.warn('Session expired, disconnecting WebSocket')
        this.disconnect()
        // Redirect to login or emit session expired event
        window.dispatchEvent(new CustomEvent('session-expired'))
        break

      case EventType.STATS:
        console.log('WebSocket stats:', message.data)
        break

      case EventType.ERROR:
        console.error('WebSocket error:', message.data)
        break
    }
  }

  private setupHealthCallbacks(): void {
    // Handle ping requests from health manager
    window.addEventListener('websocket-ping', () => {
      this.ping()
    })

    // Set up health change callback
    this.healthManager.onHealthChangeCallback((health) => {
      // Update connection stats
      this.connectionStats.reconnectCount = health.reconnectAttempts
    })

    // Set up reconnection callbacks
    this.healthManager.onReconnectAttemptCallback((attempt, delay) => {
      console.log(`Reconnection attempt ${attempt} scheduled in ${delay}ms`)
    })

    this.healthManager.onConnectionDegradedCallback(() => {
      console.warn('WebSocket connection degraded')
    })

    this.healthManager.onConnectionRecoveredCallback(() => {
      console.log('WebSocket connection recovered')
    })
  }

  private setupNetworkMonitoring(): void {
    this.networkMonitor.onStatusChangeCallback((isOnline) => {
      if (isOnline) {
        console.log('Network connection restored')
        if (!this.isConnected && this.options.autoReconnect) {
          this.connect().catch(error => {
            console.error('Failed to reconnect after network restoration:', error)
          })
        }
      } else {
        console.warn('Network connection lost')
        this.degradationManager.enableOfflineMode()
      }
    })
  }

  private async processOfflineQueue(operations: any[]): Promise<void> {
    console.log(`Processing ${operations.length} offline operations`)
    
    for (const operation of operations) {
      try {
        // Remove the queuedAt timestamp before sending
        const { queuedAt, ...cleanOperation } = operation
        this.sendMessage(cleanOperation)
      } catch (error) {
        console.error('Error processing offline operation:', error)
      }
    }
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()
      if (message) {
        this.ws.send(JSON.stringify(message))
        this.connectionStats.messagesSent++
      }
    }
  }
}

// Singleton instance management
let unifiedWebSocketInstance: UnifiedWebSocketService | null = null

export function getUnifiedWebSocketService(token: string, options?: WebSocketOptions): UnifiedWebSocketService {
  if (!unifiedWebSocketInstance) {
    unifiedWebSocketInstance = new UnifiedWebSocketService(token, options)
  }
  return unifiedWebSocketInstance
}

export function disconnectUnifiedWebSocket(): void {
  if (unifiedWebSocketInstance) {
    unifiedWebSocketInstance.disconnect()
    unifiedWebSocketInstance = null
  }
}