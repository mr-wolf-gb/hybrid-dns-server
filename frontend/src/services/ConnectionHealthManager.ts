/**
 * Connection Health Manager for WebSocket connections
 * Provides automatic reconnection, health monitoring, and graceful degradation
 */

export interface ConnectionHealthOptions {
  pingInterval?: number
  pongTimeout?: number
  reconnectInterval?: number
  maxReconnectAttempts?: number
  exponentialBackoff?: boolean
  maxBackoffDelay?: number
  healthCheckInterval?: number
  degradationThreshold?: number
}

export interface ConnectionHealth {
  isHealthy: boolean
  lastPing: Date | null
  lastPong: Date | null
  latency: number
  consecutiveFailures: number
  uptime: number
  reconnectAttempts: number
  status: ConnectionStatus
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  DEGRADED = 'degraded',
  FAILED = 'failed'
}

export interface ReconnectionStrategy {
  attempt: number
  delay: number
  maxAttempts: number
  exponentialBackoff: boolean
}

export class ConnectionHealthManager {
  private options: Required<ConnectionHealthOptions>
  private health: ConnectionHealth
  private pingIntervalId: NodeJS.Timeout | null = null
  private pongTimeoutId: NodeJS.Timeout | null = null
  private healthCheckIntervalId: NodeJS.Timeout | null = null
  private reconnectTimeoutId: NodeJS.Timeout | null = null
  private connectionStartTime: Date | null = null
  private reconnectionStrategy: ReconnectionStrategy
  private onHealthChange?: (health: ConnectionHealth) => void
  private onReconnectAttempt?: (attempt: number, delay: number) => void
  private onConnectionDegraded?: () => void
  private onConnectionRecovered?: () => void

  constructor(options: ConnectionHealthOptions = {}) {
    this.options = {
      pingInterval: options.pingInterval || 30000, // 30 seconds
      pongTimeout: options.pongTimeout || 10000, // 10 seconds
      reconnectInterval: options.reconnectInterval || 5000, // 5 seconds
      maxReconnectAttempts: options.maxReconnectAttempts || 5,
      exponentialBackoff: options.exponentialBackoff !== false,
      maxBackoffDelay: options.maxBackoffDelay || 60000, // 1 minute
      healthCheckInterval: options.healthCheckInterval || 60000, // 1 minute
      degradationThreshold: options.degradationThreshold || 3
    }

    this.health = {
      isHealthy: false,
      lastPing: null,
      lastPong: null,
      latency: 0,
      consecutiveFailures: 0,
      uptime: 0,
      reconnectAttempts: 0,
      status: ConnectionStatus.DISCONNECTED
    }

    this.reconnectionStrategy = {
      attempt: 0,
      delay: this.options.reconnectInterval,
      maxAttempts: this.options.maxReconnectAttempts,
      exponentialBackoff: this.options.exponentialBackoff
    }
  }

  /**
   * Start health monitoring
   */
  startHealthMonitoring(): void {
    this.connectionStartTime = new Date()
    this.health.status = ConnectionStatus.CONNECTED
    this.health.isHealthy = true
    this.health.reconnectAttempts = 0
    this.reconnectionStrategy.attempt = 0

    this.startPingInterval()
    this.startHealthCheckInterval()
    this.notifyHealthChange()
  }

  /**
   * Stop health monitoring
   */
  stopHealthMonitoring(): void {
    this.stopPingInterval()
    this.stopHealthCheckInterval()
    this.stopReconnectTimeout()
    
    this.health.status = ConnectionStatus.DISCONNECTED
    this.health.isHealthy = false
    this.connectionStartTime = null
    this.notifyHealthChange()
  }

  /**
   * Handle successful pong response
   */
  handlePong(): void {
    const now = new Date()
    this.health.lastPong = now
    
    if (this.health.lastPing) {
      this.health.latency = now.getTime() - this.health.lastPing.getTime()
    }

    // Reset consecutive failures on successful pong
    if (this.health.consecutiveFailures > 0) {
      this.health.consecutiveFailures = 0
      
      // Check if connection recovered from degraded state
      if (this.health.status === ConnectionStatus.DEGRADED) {
        this.health.status = ConnectionStatus.CONNECTED
        this.health.isHealthy = true
        this.onConnectionRecovered?.()
      }
    }

    this.stopPongTimeout()
    this.notifyHealthChange()
  }

  /**
   * Handle ping timeout (no pong received)
   */
  handlePingTimeout(): void {
    this.health.consecutiveFailures++
    
    // Check if connection should be marked as degraded
    if (this.health.consecutiveFailures >= this.options.degradationThreshold) {
      if (this.health.status === ConnectionStatus.CONNECTED) {
        this.health.status = ConnectionStatus.DEGRADED
        this.health.isHealthy = false
        this.onConnectionDegraded?.()
      }
    }

    this.notifyHealthChange()
  }

  /**
   * Handle connection loss
   */
  handleConnectionLoss(): void {
    this.stopPingInterval()
    this.stopHealthCheckInterval()
    
    this.health.status = ConnectionStatus.DISCONNECTED
    this.health.isHealthy = false
    this.health.consecutiveFailures++
    this.connectionStartTime = null
    
    this.notifyHealthChange()
  }

  /**
   * Start reconnection process
   */
  startReconnection(reconnectCallback: () => Promise<void>): void {
    if (this.health.status === ConnectionStatus.RECONNECTING) {
      return // Already reconnecting
    }

    this.health.status = ConnectionStatus.RECONNECTING
    this.reconnectionStrategy.attempt++
    this.health.reconnectAttempts = this.reconnectionStrategy.attempt

    // Calculate delay with exponential backoff
    let delay = this.options.reconnectInterval
    if (this.reconnectionStrategy.exponentialBackoff) {
      delay = Math.min(
        this.options.reconnectInterval * Math.pow(2, this.reconnectionStrategy.attempt - 1),
        this.options.maxBackoffDelay
      )
    }

    this.reconnectionStrategy.delay = delay
    this.onReconnectAttempt?.(this.reconnectionStrategy.attempt, delay)

    this.reconnectTimeoutId = setTimeout(async () => {
      try {
        await reconnectCallback()
        // If successful, reset reconnection strategy
        this.reconnectionStrategy.attempt = 0
        this.health.reconnectAttempts = 0
      } catch (error) {
        console.error('Reconnection attempt failed:', error)
        
        // Check if max attempts reached
        if (this.reconnectionStrategy.attempt >= this.reconnectionStrategy.maxAttempts) {
          this.health.status = ConnectionStatus.FAILED
          this.health.isHealthy = false
          this.notifyHealthChange()
        } else {
          // Schedule next reconnection attempt
          this.startReconnection(reconnectCallback)
        }
      }
    }, delay)

    this.notifyHealthChange()
  }

  /**
   * Stop reconnection process
   */
  stopReconnection(): void {
    this.stopReconnectTimeout()
    this.reconnectionStrategy.attempt = 0
    this.health.reconnectAttempts = 0
  }

  /**
   * Get current health status
   */
  getHealth(): ConnectionHealth {
    // Update uptime
    if (this.connectionStartTime) {
      this.health.uptime = Date.now() - this.connectionStartTime.getTime()
    }
    
    return { ...this.health }
  }

  /**
   * Check if connection is healthy
   */
  isHealthy(): boolean {
    return this.health.isHealthy
  }

  /**
   * Get connection status
   */
  getStatus(): ConnectionStatus {
    return this.health.status
  }

  /**
   * Set health change callback
   */
  onHealthChangeCallback(callback: (health: ConnectionHealth) => void): void {
    this.onHealthChange = callback
  }

  /**
   * Set reconnect attempt callback
   */
  onReconnectAttemptCallback(callback: (attempt: number, delay: number) => void): void {
    this.onReconnectAttempt = callback
  }

  /**
   * Set connection degraded callback
   */
  onConnectionDegradedCallback(callback: () => void): void {
    this.onConnectionDegraded = callback
  }

  /**
   * Set connection recovered callback
   */
  onConnectionRecoveredCallback(callback: () => void): void {
    this.onConnectionRecovered = callback
  }

  /**
   * Force health check
   */
  performHealthCheck(): void {
    this.sendPing()
  }

  /**
   * Reset health statistics
   */
  resetHealth(): void {
    this.health.consecutiveFailures = 0
    this.health.reconnectAttempts = 0
    this.health.latency = 0
    this.reconnectionStrategy.attempt = 0
  }

  // Private methods

  private startPingInterval(): void {
    this.pingIntervalId = setInterval(() => {
      this.sendPing()
    }, this.options.pingInterval)
  }

  private stopPingInterval(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId)
      this.pingIntervalId = null
    }
  }

  private startHealthCheckInterval(): void {
    this.healthCheckIntervalId = setInterval(() => {
      this.performHealthCheck()
    }, this.options.healthCheckInterval)
  }

  private stopHealthCheckInterval(): void {
    if (this.healthCheckIntervalId) {
      clearInterval(this.healthCheckIntervalId)
      this.healthCheckIntervalId = null
    }
  }

  private stopReconnectTimeout(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }
  }

  private sendPing(): void {
    this.health.lastPing = new Date()
    
    // Start pong timeout
    this.pongTimeoutId = setTimeout(() => {
      this.handlePingTimeout()
    }, this.options.pongTimeout)

    // Emit ping event for WebSocket to handle
    window.dispatchEvent(new CustomEvent('websocket-ping'))
  }

  private stopPongTimeout(): void {
    if (this.pongTimeoutId) {
      clearTimeout(this.pongTimeoutId)
      this.pongTimeoutId = null
    }
  }

  private notifyHealthChange(): void {
    this.onHealthChange?.(this.getHealth())
  }
}

/**
 * Graceful degradation manager for handling connection failures
 */
export class GracefulDegradationManager {
  private isOfflineMode = false
  private offlineQueue: any[] = []
  private maxOfflineQueueSize = 100
  private onOfflineModeChange?: (isOffline: boolean) => void

  /**
   * Enable offline mode
   */
  enableOfflineMode(): void {
    if (!this.isOfflineMode) {
      this.isOfflineMode = true
      this.onOfflineModeChange?.(true)
      console.log('Entering offline mode - queuing operations')
    }
  }

  /**
   * Disable offline mode and process queued operations
   */
  async disableOfflineMode(processCallback: (operations: any[]) => Promise<void>): Promise<void> {
    if (this.isOfflineMode) {
      this.isOfflineMode = false
      
      try {
        if (this.offlineQueue.length > 0) {
          console.log(`Processing ${this.offlineQueue.length} queued operations`)
          await processCallback([...this.offlineQueue])
          this.offlineQueue = []
        }
      } catch (error) {
        console.error('Error processing offline queue:', error)
      }
      
      this.onOfflineModeChange?.(false)
    }
  }

  /**
   * Queue operation for offline processing
   */
  queueOperation(operation: any): boolean {
    if (!this.isOfflineMode) {
      return false
    }

    if (this.offlineQueue.length >= this.maxOfflineQueueSize) {
      // Remove oldest operation
      this.offlineQueue.shift()
    }

    this.offlineQueue.push({
      ...operation,
      queuedAt: new Date().toISOString()
    })

    return true
  }

  /**
   * Check if in offline mode
   */
  isInOfflineMode(): boolean {
    return this.isOfflineMode
  }

  /**
   * Get queued operations count
   */
  getQueuedOperationsCount(): number {
    return this.offlineQueue.length
  }

  /**
   * Clear offline queue
   */
  clearQueue(): void {
    this.offlineQueue = []
  }

  /**
   * Set offline mode change callback
   */
  onOfflineModeChangeCallback(callback: (isOffline: boolean) => void): void {
    this.onOfflineModeChange = callback
  }
}

/**
 * Network status monitor
 */
export class NetworkStatusMonitor {
  private isOnline = navigator.onLine
  private onStatusChange?: (isOnline: boolean) => void

  constructor() {
    this.setupEventListeners()
  }

  /**
   * Check if network is online
   */
  isNetworkOnline(): boolean {
    return this.isOnline
  }

  /**
   * Set status change callback
   */
  onStatusChangeCallback(callback: (isOnline: boolean) => void): void {
    this.onStatusChange = callback
  }

  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true
      this.onStatusChange?.(true)
    })

    window.addEventListener('offline', () => {
      this.isOnline = false
      this.onStatusChange?.(false)
    })
  }
}

// Utility functions

export function createExponentialBackoffDelay(
  attempt: number, 
  baseDelay: number, 
  maxDelay: number = 60000
): number {
  return Math.min(baseDelay * Math.pow(2, attempt), maxDelay)
}

export function createJitteredDelay(delay: number, jitterFactor: number = 0.1): number {
  const jitter = delay * jitterFactor * (Math.random() - 0.5)
  return Math.max(0, delay + jitter)
}