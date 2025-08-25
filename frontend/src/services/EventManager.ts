/**
 * Event Manager for handling incoming WebSocket events
 * Provides event buffering, batch processing, and handler routing
 */

import { EventType, EventPriority, WebSocketMessage } from './UnifiedWebSocketService'

export interface EventBuffer {
  events: WebSocketMessage[]
  lastProcessed: Date
  maxSize: number
  batchTimeout: number
}

export interface EventProcessingOptions {
  batchSize?: number
  batchTimeout?: number
  maxBufferSize?: number
  enableBatching?: boolean
  priorityProcessing?: boolean
}

export interface EventHandlerRegistration {
  id: string
  eventTypes: EventType[]
  handler: (event: WebSocketMessage) => void | Promise<void>
  priority?: number
  errorHandler?: (error: Error, event: WebSocketMessage) => void
}

export interface EventStats {
  totalProcessed: number
  totalErrors: number
  averageProcessingTime: number
  eventsByType: Record<string, number>
  errorsByType: Record<string, number>
  lastProcessedAt?: Date
}

export class EventManager {
  private eventBuffer: EventBuffer
  private eventHandlers: Map<string, EventHandlerRegistration> = new Map()
  private processingQueue: WebSocketMessage[] = []
  private batchTimeoutId: NodeJS.Timeout | null = null
  private isProcessing = false
  private options: Required<EventProcessingOptions>
  private stats: EventStats = {
    totalProcessed: 0,
    totalErrors: 0,
    averageProcessingTime: 0,
    eventsByType: {},
    errorsByType: {}
  }

  constructor(options: EventProcessingOptions = {}) {
    this.options = {
      batchSize: options.batchSize || 10,
      batchTimeout: options.batchTimeout || 1000, // 1 second
      maxBufferSize: options.maxBufferSize || 1000,
      enableBatching: options.enableBatching !== false,
      priorityProcessing: options.priorityProcessing !== false
    }

    this.eventBuffer = {
      events: [],
      lastProcessed: new Date(),
      maxSize: this.options.maxBufferSize,
      batchTimeout: this.options.batchTimeout
    }
  }

  /**
   * Register an event handler for specific event types
   */
  registerHandler(registration: EventHandlerRegistration): void {
    this.eventHandlers.set(registration.id, registration)
  }

  /**
   * Unregister an event handler
   */
  unregisterHandler(id: string): void {
    this.eventHandlers.delete(id)
  }

  /**
   * Process incoming event
   */
  async handleEvent(event: WebSocketMessage): Promise<void> {
    // Add to buffer
    this.addToBuffer(event)

    // Process immediately if critical priority or batching disabled
    if (!this.options.enableBatching || event.priority === EventPriority.CRITICAL) {
      await this.processEvent(event)
    } else {
      // Schedule batch processing
      this.scheduleBatchProcessing()
    }
  }

  /**
   * Process multiple events in batch
   */
  async batchProcessEvents(): Promise<void> {
    if (this.isProcessing || this.eventBuffer.events.length === 0) {
      return
    }

    this.isProcessing = true
    const startTime = Date.now()

    try {
      // Get events to process
      const eventsToProcess = this.getEventsForProcessing()
      
      if (eventsToProcess.length === 0) {
        return
      }

      // Sort by priority if enabled
      if (this.options.priorityProcessing) {
        eventsToProcess.sort(this.priorityComparator)
      }

      // Process events
      await Promise.all(eventsToProcess.map(event => this.processEvent(event)))

      // Update stats
      this.updateProcessingStats(eventsToProcess.length, Date.now() - startTime)

    } catch (error) {
      console.error('Error in batch processing:', error)
      this.stats.totalErrors++
    } finally {
      this.isProcessing = false
      this.eventBuffer.lastProcessed = new Date()
    }
  }

  /**
   * Get event processing statistics
   */
  getStats(): EventStats {
    return { ...this.stats }
  }

  /**
   * Clear event buffer
   */
  clearBuffer(): void {
    this.eventBuffer.events = []
  }

  /**
   * Get current buffer size
   */
  getBufferSize(): number {
    return this.eventBuffer.events.length
  }

  /**
   * Get registered handlers count
   */
  getHandlerCount(): number {
    return this.eventHandlers.size
  }

  /**
   * Force process all buffered events
   */
  async flushBuffer(): Promise<void> {
    if (this.batchTimeoutId) {
      clearTimeout(this.batchTimeoutId)
      this.batchTimeoutId = null
    }
    await this.batchProcessEvents()
  }

  // Private methods

  private addToBuffer(event: WebSocketMessage): void {
    // Check buffer size limit
    if (this.eventBuffer.events.length >= this.eventBuffer.maxSize) {
      // Remove oldest events to make room
      const removeCount = Math.floor(this.eventBuffer.maxSize * 0.1) // Remove 10%
      this.eventBuffer.events.splice(0, removeCount)
      console.warn(`Event buffer overflow, removed ${removeCount} oldest events`)
    }

    this.eventBuffer.events.push(event)
  }

  private getEventsForProcessing(): WebSocketMessage[] {
    const batchSize = this.options.batchSize
    const events = this.eventBuffer.events.splice(0, batchSize)
    return events
  }

  private scheduleBatchProcessing(): void {
    if (this.batchTimeoutId) {
      return // Already scheduled
    }

    this.batchTimeoutId = setTimeout(() => {
      this.batchTimeoutId = null
      this.batchProcessEvents()
    }, this.options.batchTimeout)
  }

  private async processEvent(event: WebSocketMessage): Promise<void> {
    const startTime = Date.now()

    try {
      // Find matching handlers
      const matchingHandlers = Array.from(this.eventHandlers.values())
        .filter(handler => 
          handler.eventTypes.includes(event.type) || 
          handler.eventTypes.includes('*' as EventType)
        )
        .sort((a, b) => (b.priority || 0) - (a.priority || 0)) // Higher priority first

      // Execute handlers
      await Promise.all(matchingHandlers.map(async handler => {
        try {
          await handler.handler(event)
        } catch (error) {
          console.error(`Error in event handler ${handler.id}:`, error)
          
          // Call error handler if provided
          if (handler.errorHandler) {
            try {
              handler.errorHandler(error as Error, event)
            } catch (errorHandlerError) {
              console.error(`Error in error handler for ${handler.id}:`, errorHandlerError)
            }
          }

          // Update error stats
          this.stats.totalErrors++
          this.stats.errorsByType[event.type] = (this.stats.errorsByType[event.type] || 0) + 1
        }
      }))

      // Update stats
      this.stats.totalProcessed++
      this.stats.eventsByType[event.type] = (this.stats.eventsByType[event.type] || 0) + 1
      this.stats.lastProcessedAt = new Date()

      // Update average processing time
      const processingTime = Date.now() - startTime
      this.stats.averageProcessingTime = 
        (this.stats.averageProcessingTime * (this.stats.totalProcessed - 1) + processingTime) / 
        this.stats.totalProcessed

    } catch (error) {
      console.error('Error processing event:', error)
      this.stats.totalErrors++
      this.stats.errorsByType[event.type] = (this.stats.errorsByType[event.type] || 0) + 1
    }
  }

  private priorityComparator(a: WebSocketMessage, b: WebSocketMessage): number {
    const priorityOrder = {
      [EventPriority.CRITICAL]: 4,
      [EventPriority.HIGH]: 3,
      [EventPriority.NORMAL]: 2,
      [EventPriority.LOW]: 1
    }

    const aPriority = priorityOrder[a.priority] || 2
    const bPriority = priorityOrder[b.priority] || 2

    return bPriority - aPriority // Higher priority first
  }

  private updateProcessingStats(eventCount: number, processingTime: number): void {
    this.stats.totalProcessed += eventCount
    
    // Update average processing time
    if (eventCount > 0) {
      const avgTimePerEvent = processingTime / eventCount
      this.stats.averageProcessingTime = 
        (this.stats.averageProcessingTime * (this.stats.totalProcessed - eventCount) + 
         avgTimePerEvent * eventCount) / this.stats.totalProcessed
    }
  }
}

// Event handler utilities

export class EventHandlerBuilder {
  private registration: Partial<EventHandlerRegistration> = {}

  static create(id: string): EventHandlerBuilder {
    const builder = new EventHandlerBuilder()
    builder.registration.id = id
    return builder
  }

  forEvents(...eventTypes: EventType[]): EventHandlerBuilder {
    this.registration.eventTypes = eventTypes
    return this
  }

  withHandler(handler: (event: WebSocketMessage) => void | Promise<void>): EventHandlerBuilder {
    this.registration.handler = handler
    return this
  }

  withPriority(priority: number): EventHandlerBuilder {
    this.registration.priority = priority
    return this
  }

  withErrorHandler(errorHandler: (error: Error, event: WebSocketMessage) => void): EventHandlerBuilder {
    this.registration.errorHandler = errorHandler
    return this
  }

  build(): EventHandlerRegistration {
    if (!this.registration.id || !this.registration.eventTypes || !this.registration.handler) {
      throw new Error('Event handler registration requires id, eventTypes, and handler')
    }
    return this.registration as EventHandlerRegistration
  }
}

// Specialized event handlers

export class HealthEventHandler {
  static create(id: string, onHealthUpdate: (data: any) => void, onHealthAlert: (data: any) => void) {
    return EventHandlerBuilder.create(id)
      .forEvents(EventType.HEALTH_UPDATE, EventType.HEALTH_ALERT, EventType.FORWARDER_STATUS_CHANGE)
      .withHandler((event) => {
        switch (event.type) {
          case EventType.HEALTH_UPDATE:
          case EventType.FORWARDER_STATUS_CHANGE:
            onHealthUpdate(event.data)
            break
          case EventType.HEALTH_ALERT:
            onHealthAlert(event.data)
            break
        }
      })
      .withPriority(10)
      .build()
  }
}

export class DNSEventHandler {
  static create(id: string, onDNSChange: (data: any) => void) {
    return EventHandlerBuilder.create(id)
      .forEvents(
        EventType.ZONE_CREATED,
        EventType.ZONE_UPDATED,
        EventType.ZONE_DELETED,
        EventType.RECORD_CREATED,
        EventType.RECORD_UPDATED,
        EventType.RECORD_DELETED
      )
      .withHandler((event) => onDNSChange(event.data))
      .withPriority(5)
      .build()
  }
}

export class SecurityEventHandler {
  static create(id: string, onSecurityEvent: (data: any) => void) {
    return EventHandlerBuilder.create(id)
      .forEvents(EventType.SECURITY_ALERT, EventType.RPZ_UPDATE, EventType.THREAT_DETECTED)
      .withHandler((event) => onSecurityEvent(event.data))
      .withPriority(15) // High priority for security events
      .build()
  }
}

export class SystemEventHandler {
  static create(id: string, onSystemEvent: (data: any) => void) {
    return EventHandlerBuilder.create(id)
      .forEvents(EventType.SYSTEM_STATUS, EventType.BIND_RELOAD, EventType.CONFIG_CHANGE)
      .withHandler((event) => onSystemEvent(event.data))
      .withPriority(8)
      .build()
  }
}

// Default event manager instance
let defaultEventManager: EventManager | null = null

export function getDefaultEventManager(options?: EventProcessingOptions): EventManager {
  if (!defaultEventManager) {
    defaultEventManager = new EventManager(options)
  }
  return defaultEventManager
}

export function resetDefaultEventManager(): void {
  if (defaultEventManager) {
    defaultEventManager.clearBuffer()
    defaultEventManager = null
  }
}