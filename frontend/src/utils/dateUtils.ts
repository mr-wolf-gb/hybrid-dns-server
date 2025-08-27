/**
 * Safe date utilities wrapper to prevent date-fns initialization errors
 */

// Safe format function that falls back to native Intl if date-fns fails
export const safeFormat = (date: Date | string | number, formatStr: string): string => {
  try {
    // Dynamic import to avoid loading date-fns at module level
    const { format } = require('date-fns')
    return format(new Date(date), formatStr)
  } catch (error) {
    // Fallback to native Intl formatting
    const dateObj = new Date(date)
    if (isNaN(dateObj.getTime())) {
      return 'Invalid Date'
    }
    
    // Map common date-fns formats to Intl options
    const formatMap: Record<string, Intl.DateTimeFormatOptions> = {
      'PPpp': { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      },
      'PP': { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      },
      'p': { 
        hour: '2-digit', 
        minute: '2-digit' 
      },
      'HH:mm:ss': { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      },
      'yyyy-MM-dd': { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit' 
      },
      'MMM dd, yyyy': { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      }
    }
    
    const options = formatMap[formatStr] || { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    }
    
    return new Intl.DateTimeFormat('en-US', options).format(dateObj)
  }
}

// Safe subDays function
export const safeSubDays = (date: Date | string | number, amount: number): Date => {
  try {
    const { subDays } = require('date-fns')
    return subDays(new Date(date), amount)
  } catch (error) {
    // Fallback implementation
    const dateObj = new Date(date)
    dateObj.setDate(dateObj.getDate() - amount)
    return dateObj
  }
}

// Safe startOfDay function
export const safeStartOfDay = (date: Date | string | number): Date => {
  try {
    const { startOfDay } = require('date-fns')
    return startOfDay(new Date(date))
  } catch (error) {
    // Fallback implementation
    const dateObj = new Date(date)
    dateObj.setHours(0, 0, 0, 0)
    return dateObj
  }
}

// Safe endOfDay function
export const safeEndOfDay = (date: Date | string | number): Date => {
  try {
    const { endOfDay } = require('date-fns')
    return endOfDay(new Date(date))
  } catch (error) {
    // Fallback implementation
    const dateObj = new Date(date)
    dateObj.setHours(23, 59, 59, 999)
    return dateObj
  }
}

// Initialize chartjs adapter safely - only when Chart.js is actually loaded
export const initializeChartJSAdapter = async (): Promise<void> => {
  try {
    // Only load if we're in a browser environment
    if (typeof window !== 'undefined') {
      // Dynamic import to avoid loading at module level
      const { default: adapter } = await import('chartjs-adapter-date-fns')
      return adapter
    }
  } catch (error) {
    console.warn('Failed to load chartjs-adapter-date-fns:', error)
    // Chart.js will fall back to default time adapter
  }
}