import React, { ReactNode } from 'react'
import { cn } from '@/utils'

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
  description?: string
  action?: ReactNode
}

const Card: React.FC<CardProps> = ({ 
  children, 
  className, 
  title, 
  description, 
  action 
}) => {
  return (
    <div className={cn(
      'bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700',
      className
    )}>
      {(title || description || action) && (
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {title}
                </h3>
              )}
              {description && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {description}
                </p>
              )}
            </div>
            {action && (
              <div className="flex-shrink-0">
                {action}
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="p-6">
        {children}
      </div>
    </div>
  )
}

export default Card