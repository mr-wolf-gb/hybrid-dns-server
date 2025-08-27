import { SelectHTMLAttributes, forwardRef } from 'react'
import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils'

interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string
  error?: string
  helperText?: string
  options?: SelectOption[]
  placeholder?: string
  children?: React.ReactNode
  onValueChange?: (value: string) => void
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, helperText, options, placeholder, children, onValueChange, onChange, ...props }, ref) => {
    const baseClasses = 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm bg-white text-gray-900 dark:bg-gray-700 dark:border-gray-500 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400 appearance-none pr-10 p-2.5'
    const errorClasses = 'border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-400 dark:focus:border-red-400 dark:focus:ring-red-400'

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {label}
          </label>
        )}

        <div className="relative">
          <select
            className={cn(
              baseClasses,
              error ? errorClasses : '',
              className
            )}
            ref={ref}
            onChange={(e) => {
              onValueChange?.(e.target.value)
              onChange?.(e)
            }}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {children || options?.map((option) => (
              <option
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))}
          </select>

          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <ChevronDownIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
          </div>
        </div>

        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        {helperText && !error && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'

export default Select