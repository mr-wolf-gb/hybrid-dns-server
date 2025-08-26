import React from 'react'
import { HeartIcon } from '@heroicons/react/24/solid'

const Footer: React.FC = () => {
    const currentYear = new Date().getFullYear()

    return (
        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-4">
                <div className="flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0">
                    <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                        <span>© {currentYear} Hybrid DNS Server</span>
                        <span className="hidden sm:inline">•</span>
                        <span className="hidden sm:inline">Enterprise DNS Management</span>
                    </div>

                    <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                        <span>Made with</span>
                        <HeartIcon className="h-4 w-4 text-red-500" />
                        <span>for secure DNS</span>
                    </div>
                </div>
            </div>
        </footer>
    )
}

export default Footer