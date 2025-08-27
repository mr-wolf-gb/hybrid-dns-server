import React, { SelectHTMLAttributes, forwardRef, createContext, useContext, useState } from 'react'
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

// Context for the new Select components
interface SelectContextType {
  value: string
  onValueChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
}

const SelectContext = createContext<SelectContextType | undefined>(undefined)

// New Select component for shadcn-style usage
interface NewSelectProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
}

const NewSelect: React.FC<NewSelectProps> = ({ value, defaultValue, onValueChange, children }) => {
  const [internalValue, setInternalValue] = useState(defaultValue || '')
  const [open, setOpen] = useState(false)
  const currentValue = value !== undefined ? value : internalValue

  const handleValueChange = (newValue: string) => {
    if (value === undefined) {
      setInternalValue(newValue)
    }
    onValueChange?.(newValue)
    setOpen(false)
  }

  return (
    <SelectContext.Provider value={{ value: currentValue, onValueChange: handleValueChange, open, setOpen }}>
      <div className="relative">
        {children}
      </div>
    </SelectContext.Provider>
  )
}

interface SelectTriggerProps {
  children: React.ReactNode
  className?: string
}

const SelectTrigger: React.FC<SelectTriggerProps> = ({ children, className }) => {
  const context = useContext(SelectContext)
  if (!context) throw new Error('SelectTrigger must be used within Select')

  const { open, setOpen } = context

  return (
    <button
      type="button"
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:ring-offset-gray-950 dark:placeholder:text-gray-400 dark:focus:ring-blue-400',
        className
      )}
      onClick={() => setOpen(!open)}
    >
      {children}
      <ChevronDownIcon className="h-4 w-4 opacity-50" />
    </button>
  )
}

const SelectValue: React.FC<{ placeholder?: string }> = ({ placeholder }) => {
  const context = useContext(SelectContext)
  if (!context) throw new Error('SelectValue must be used within Select')

  const { value } = context
  return <span>{value || placeholder}</span>
}

interface SelectContentProps {
  children: React.ReactNode
  className?: string
}

const SelectContent: React.FC<SelectContentProps> = ({ children, className }) => {
  const context = useContext(SelectContext)
  if (!context) throw new Error('SelectContent must be used within Select')

  const { open } = context

  if (!open) return null

  return (
    <div
      className={cn(
        'absolute top-full z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none dark:border-gray-600 dark:bg-gray-700 sm:text-sm',
        className
      )}
    >
      {children}
    </div>
  )
}

interface SelectItemProps {
  value: string
  children: React.ReactNode
  className?: string
}

const SelectItem: React.FC<SelectItemProps> = ({ value, children, className }) => {
  const context = useContext(SelectContext)
  if (!context) throw new Error('SelectItem must be used within Select')

  const { onValueChange, value: selectedValue } = context
  const isSelected = selectedValue === value

  return (
    <div
      className={cn(
        'relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-600',
        isSelected && 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100',
        className
      )}
      onClick={() => onValueChange(value)}
    >
      {children}
    </div>
  )
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

// Export both old and new Select components
export { NewSelect as Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
export default Select