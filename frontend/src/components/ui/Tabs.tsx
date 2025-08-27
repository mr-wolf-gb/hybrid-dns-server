import React, { ReactNode, createContext, useContext, useState } from 'react'
import { cn } from '@/utils'

interface TabsContextType {
    value: string
    onValueChange: (value: string) => void
}

const TabsContext = createContext<TabsContextType | undefined>(undefined)

interface TabsProps {
    value?: string
    defaultValue?: string
    onValueChange?: (value: string) => void
    children: ReactNode
    className?: string
}

export const Tabs: React.FC<TabsProps> = ({ value, defaultValue, onValueChange, children, className }) => {
    const [internalValue, setInternalValue] = useState(defaultValue || '')
    const currentValue = value !== undefined ? value : internalValue

    const handleValueChange = (newValue: string) => {
        if (value === undefined) {
            setInternalValue(newValue)
        }
        onValueChange?.(newValue)
    }

    return (
        <TabsContext.Provider value={{ value: currentValue, onValueChange: handleValueChange }}>
            <div className={cn('w-full', className)}>
                {children}
            </div>
        </TabsContext.Provider>
    )
}

interface TabsListProps {
    children: ReactNode
    className?: string
}

export const TabsList: React.FC<TabsListProps> = ({ children, className }) => {
    return (
        <div className={cn(
            'inline-flex h-10 items-center justify-center rounded-md bg-gray-100 dark:bg-gray-800 p-1 text-gray-500 dark:text-gray-400',
            className
        )}>
            {children}
        </div>
    )
}

interface TabsTriggerProps {
    value: string
    children: ReactNode
    className?: string
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ value, children, className }) => {
    const context = useContext(TabsContext)
    if (!context) throw new Error('TabsTrigger must be used within Tabs')

    const { value: selectedValue, onValueChange } = context
    const isSelected = selectedValue === value

    return (
        <button
            className={cn(
                'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
                isSelected
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-700',
                className
            )}
            onClick={() => onValueChange(value)}
        >
            {children}
        </button>
    )
}

interface TabsContentProps {
    value: string
    children: ReactNode
    className?: string
}

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className }) => {
    const context = useContext(TabsContext)
    if (!context) throw new Error('TabsContent must be used within Tabs')

    const { value: selectedValue } = context

    if (selectedValue !== value) return null

    return (
        <div className={cn('mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2', className)}>
            {children}
        </div>
    )
}