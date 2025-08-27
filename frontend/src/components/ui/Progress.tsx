import React from 'react'
import { cn } from '@/utils'

interface ProgressProps {
  value: number
  max?: number
  className?: string
}

const Progress: React.FC<ProgressProps> = ({ value, max = 100, className }) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div
      className={cn(
        'relative h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700',
        className
      )}
    >
      <div
        className="h-full bg-blue-600 transition-all duration-300 ease-in-out dark:bg-blue-400"
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

export default Progress