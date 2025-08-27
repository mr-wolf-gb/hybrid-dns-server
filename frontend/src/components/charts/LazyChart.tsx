import React, { useState, useEffect } from 'react'
import { Loading } from '@/components/ui'

interface LazyChartProps {
    children: (chartComponents: any) => React.ReactNode
}

const LazyChart: React.FC<LazyChartProps> = ({ children }) => {
    const [chartComponents, setChartComponents] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const loadCharts = async () => {
            try {
                const [
                    chartModule,
                    reactChartModule
                ] = await Promise.all([
                    import('chart.js'),
                    import('react-chartjs-2')
                ])

                const { Chart: ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, TimeScale, Filler } = chartModule
                const { Line, Bar, Doughnut } = reactChartModule

                ChartJS.register(
                    CategoryScale,
                    LinearScale,
                    PointElement,
                    LineElement,
                    BarElement,
                    Title,
                    Tooltip,
                    Legend,
                    ArcElement,
                    TimeScale,
                    Filler
                )

                setChartComponents({ Line, Bar, Doughnut, ChartJS })
                setLoading(false)
            } catch (err) {
                console.error('Failed to load Chart.js:', err)
                setError('Failed to load charts')
                setLoading(false)
            }
        }

        loadCharts()
    }, [])

    if (loading) {
        return <Loading text="Loading charts..." />
    }

    if (error) {
        return (
            <div className="flex items-center justify-center p-8 text-gray-500">
                <p>{error}</p>
            </div>
        )
    }

    return <>{children(chartComponents)}</>
}

export default LazyChart