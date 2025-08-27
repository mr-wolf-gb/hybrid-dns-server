import React from 'react'
import { cn } from '@/utils'

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  children: React.ReactNode
  className?: string
}

const Label: React.FC<LabelProps> = ({ children, className, ...props }) => {
  return (
    <label
      className={cn(
        'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-gray-700 dark:text-gray-300',
        className
      )}
      {...props}
    >
      {children}
    </label>
  )
}

export default Label