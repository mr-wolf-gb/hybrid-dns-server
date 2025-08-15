import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useTheme } from '@/contexts/ThemeContext'

interface ChartData {
  hour: string
  queries: number
}

interface DashboardChartProps {
  data: ChartData[]
}

const DashboardChart: React.FC<DashboardChartProps> = ({ data }) => {
  const { theme } = useTheme()
  
  const isDark = theme === 'dark'
  
  // Transform data to ensure proper time formatting
  const chartData = data.map(item => ({
    ...item,
    time: new Date(item.hour).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }),
  }))

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
        No query data available
      </div>
    )
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke={isDark ? '#374151' : '#e5e7eb'}
          />
          <XAxis
            dataKey="time"
            stroke={isDark ? '#9ca3af' : '#6b7280'}
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke={isDark ? '#9ca3af' : '#6b7280'}
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDark ? '#1f2937' : '#ffffff',
              border: isDark ? '1px solid #374151' : '1px solid #e5e7eb',
              borderRadius: '8px',
              color: isDark ? '#f3f4f6' : '#1f2937',
            }}
            labelStyle={{
              color: isDark ? '#d1d5db' : '#4b5563',
            }}
          />
          <Line
            type="monotone"
            dataKey="queries"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default DashboardChart