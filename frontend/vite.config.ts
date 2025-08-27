import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000'
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: '0.0.0.0', // Allow external connections
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
      minify: 'esbuild',
      chunkSizeWarningLimit: 1000, // Increase warning limit to 1MB
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            // Vendor chunks
            if (id.includes('node_modules')) {
              // React ecosystem
              if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
                return 'react-vendor'
              }
              
              // UI and styling libraries
              if (id.includes('@heroicons') || id.includes('tailwind') || id.includes('clsx')) {
                return 'ui-vendor'
              }
              
              // HTTP and data fetching
              if (id.includes('axios') || id.includes('@tanstack/react-query') || id.includes('react-hook-form')) {
                return 'data-vendor'
              }
              
              // Charts and visualization - separate Chart.js to avoid initialization issues
              if (id.includes('chart.js') || id.includes('chartjs-adapter')) {
                return 'chartjs-vendor'
              }
              if (id.includes('recharts') || id.includes('d3')) {
                return 'charts-vendor'
              }
              
              // Date and utility libraries
              if (id.includes('date-fns') || id.includes('lodash') || id.includes('react-toastify')) {
                return 'utils-vendor'
              }
              
              // All other node_modules
              return 'vendor'
            }
            
            // Application chunks
            if (id.includes('/src/pages/')) {
              // Group pages by functionality
              if (id.includes('Dashboard') || id.includes('RealTime')) {
                return 'dashboard-pages'
              }
              if (id.includes('DNS') || id.includes('Zones') || id.includes('Records')) {
                return 'dns-pages'
              }
              if (id.includes('Security') || id.includes('RPZ') || id.includes('Threat')) {
                return 'security-pages'
              }
              if (id.includes('Analytics') || id.includes('Reports') || id.includes('Events')) {
                return 'analytics-pages'
              }
              if (id.includes('Settings') || id.includes('Health') || id.includes('Diagnostic')) {
                return 'admin-pages'
              }
              return 'other-pages'
            }
            
            // Component chunks
            if (id.includes('/src/components/')) {
              if (id.includes('security/') || id.includes('rpz/')) {
                return 'security-components'
              }
              if (id.includes('analytics/') || id.includes('dashboard/') || id.includes('charts/')) {
                return 'analytics-components'
              }
              if (id.includes('zones/') || id.includes('dns/') || id.includes('records/')) {
                return 'dns-components'
              }
              if (id.includes('diagnostics/')) {
                return 'diagnostic-components'
              }
              if (id.includes('ui/')) {
                return 'ui-components'
              }
              return 'components'
            }
            
            // Services and utilities
            if (id.includes('/src/services/') || id.includes('/src/hooks/') || id.includes('/src/contexts/')) {
              return 'app-services'
            }
            
            // Types and utilities
            if (id.includes('/src/types/') || id.includes('/src/utils/')) {
              return 'app-utils'
            }
          },
        },
      },
    },
  }
})