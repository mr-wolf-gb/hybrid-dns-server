import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utility function to combine class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format date utilities
export const formatDateTime = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(date))
}

export const formatDate = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date))
}

export const formatTime = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(date))
}

export const formatRelativeTime = (date: string | Date): string => {
  const now = new Date()
  const past = new Date(date)
  const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return 'just now'
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  } else {
    const days = Math.floor(diffInSeconds / 86400)
    return `${days} day${days > 1 ? 's' : ''} ago`
  }
}

// Format bytes
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

// Format numbers
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('en-US').format(num)
}

export const formatPercentage = (value: number, total: number): string => {
  if (total === 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

// Validation utilities
export const isValidDomain = (domain: string): boolean => {
  const domainRegex = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i
  return domainRegex.test(domain)
}

export const isValidIP = (ip: string): boolean => {
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
  const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/
  return ipv4Regex.test(ip) || ipv6Regex.test(ip)
}

export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export const isValidPort = (port: string | number): boolean => {
  const portNum = typeof port === 'string' ? parseInt(port, 10) : port
  return !isNaN(portNum) && portNum >= 1 && portNum <= 65535
}

// DNS record validation
export const validateDNSRecord = (type: string, value: string): boolean => {
  switch (type) {
    case 'A':
      return isValidIP(value) && value.includes('.')
    case 'AAAA':
      return isValidIP(value) && value.includes(':')
    case 'CNAME':
    case 'PTR':
    case 'NS':
      return isValidDomain(value)
    case 'MX':
      // Format: "priority domain"
      const mxParts = value.split(' ')
      return mxParts.length === 2 && !isNaN(parseInt(mxParts[0], 10)) && isValidDomain(mxParts[1])
    case 'TXT':
      return value.length > 0
    case 'SRV':
      // Format: "priority weight port target"
      const srvParts = value.split(' ')
      return (
        srvParts.length === 4 &&
        !isNaN(parseInt(srvParts[0], 10)) &&
        !isNaN(parseInt(srvParts[1], 10)) &&
        isValidPort(srvParts[2]) &&
        isValidDomain(srvParts[3])
      )
    default:
      return true
  }
}

// Status color utilities
export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'active':
    case 'online':
    case 'running':
      return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30'
    case 'unhealthy':
    case 'inactive':
    case 'offline':
    case 'stopped':
      return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
    case 'warning':
    case 'degraded':
      return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30'
    case 'unknown':
    case 'pending':
      return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30'
    default:
      return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30'
  }
}

export const getCategoryColor = (category: string): string => {
  switch (category.toLowerCase()) {
    case 'malware':
    case 'phishing':
      return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
    case 'social_media':
    case 'social-media':
      return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30'
    case 'adult':
    case 'gambling':
      return 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30'
    case 'custom':
      return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30'
    default:
      return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30'
  }
}

// Debounce utility
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Copy to clipboard
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    try {
      document.execCommand('copy')
      document.body.removeChild(textArea)
      return true
    } catch (err) {
      document.body.removeChild(textArea)
      return false
    }
  }
}

// Generate random string
export const generateRandomString = (length: number): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// Download file
export const downloadFile = (content: string, filename: string, contentType = 'text/plain'): void => {
  const blob = new Blob([content], { type: contentType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}