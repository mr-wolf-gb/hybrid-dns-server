import React, { ReactNode } from 'react'
import { cn } from '@/utils'

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
  description?: string
  action?: ReactNode
}

interface CardHeaderProps {
  children: ReactNode
  className?: string
}

interface CardContentProps {
  children: ReactNode
  className?: string
}

interface CardTitleProps {
  children: ReactNode
  className?: string
}

const Card: React.FC<CardProps> = ({ children, className, title, description, action }) => {
  return (
    <div className={cn(
      'bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700',
      className
    )}>
      {(title || description || action) && (
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && <CardTitle>{title}</CardTitle>}
              {description && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
              )}
            </div>
            {action && <div>{action}</div>}
          </div>
        </CardHeader>
      )}
      <CardContent>
        {children}
      </CardContent>
    </div>
  )
}

const CardHeader: React.FC<CardHeaderProps> = ({ children, className }) => {
  return (
    <div className={cn(
      'px-6 py-4 border-b border-gray-200 dark:border-gray-700',
      className
    )}>
      {children}
    </div>
  )
}

const CardContent: React.FC<CardContentProps> = ({ children, className }) => {
  return (
    <div className={cn('p-6', className)}>
      {children}
    </div>
  )
}

const CardTitle: React.FC<CardTitleProps> = ({ children, className }) => {
  return (
    <h3 className={cn(
      'text-lg font-medium text-gray-900 dark:text-gray-100',
      className
    )}>
      {children}
    </h3>
  )
}

export { Card, CardHeader, CardContent, CardTitle }
export default Card