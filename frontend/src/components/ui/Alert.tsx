import React from 'react'
import { cn } from '@/utils'

interface AlertProps {
  children: React.ReactNode
  className?: string
  variant?: 'default' | 'destructive' | 'warning' | 'success'
}

interface AlertDescriptionProps {
  children: React.ReactNode
  className?: string
}

const Alert: React.FC<AlertProps> = ({ children, className, variant = 'default' }) => {
  const variantClasses = {
    default: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-400',
    destructive: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-400',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:border-yellow-800 dark:text-yellow-400',
    success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-400'
  }

  return (
    <div
      className={cn(
        'relative w-full rounded-lg border p-4',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </div>
  )
}

const AlertDescription: React.FC<AlertDescriptionProps> = ({ children, className }) => {
  return (
    <div className={cn('text-sm', className)}>
      {children}
    </div>
  )
}

export { Alert, AlertDescription }
export default Alert