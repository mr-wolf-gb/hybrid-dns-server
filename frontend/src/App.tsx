import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import LoginForm from '@/components/auth/LoginForm'
import Layout from '@/components/layout/Layout'
import { Loading } from '@/components/ui'
import { preloadCriticalPages } from '@/utils/preload'

// Lazy load all pages for better performance
const Dashboard = React.lazy(() => import('@/pages/Dashboard'))
const DNSZones = React.lazy(() => import('@/pages/DNSZones'))
const Forwarders = React.lazy(() => import('@/pages/Forwarders'))
const Security = React.lazy(() => import('@/pages/Security'))
const DiagnosticTools = React.lazy(() => import('@/pages/DiagnosticTools'))
const QueryLogs = React.lazy(() => import('@/pages/QueryLogs'))
const Settings = React.lazy(() => import('@/pages/Settings'))
const HealthMonitoring = React.lazy(() => import('@/pages/HealthMonitoring'))
const RealTimeDashboard = React.lazy(() => import('@/pages/RealTimeDashboard'))
const Events = React.lazy(() => import('@/pages/Events'))
const Reports = React.lazy(() => import('@/pages/Reports'))
const Analytics = React.lazy(() => import('@/pages/Analytics'))

const App: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()

  // Preload critical pages after authentication
  useEffect(() => {
    if (isAuthenticated) {
      preloadCriticalPages()
    }
  }, [isAuthenticated])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loading size="lg" text="Initializing..." />
      </div>
    )
  }

  return (
    <Routes>
      {/* Login route */}
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to="/" replace />
          ) : (
            <LoginForm onSuccess={() => window.location.href = '/'} />
          )
        }
      />

      {/* Protected routes */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route 
          index 
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading dashboard..." />}>
              <Dashboard />
            </React.Suspense>
          } 
        />
        <Route
          path="zones"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading zones..." />}>
              <DNSZones />
            </React.Suspense>
          }
        />
        <Route
          path="forwarders"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading forwarders..." />}>
              <Forwarders />
            </React.Suspense>
          }
        />
        <Route
          path="security"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading security..." />}>
              <Security />
            </React.Suspense>
          }
        />
        <Route
          path="diagnostics"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading diagnostic tools..." />}>
              <DiagnosticTools />
            </React.Suspense>
          }
        />
        <Route
          path="logs"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading logs..." />}>
              <QueryLogs />
            </React.Suspense>
          }
        />
        <Route
          path="settings"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading settings..." />}>
              <Settings />
            </React.Suspense>
          }
        />
        <Route
          path="health"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading health monitoring..." />}>
              <HealthMonitoring />
            </React.Suspense>
          }
        />
        <Route
          path="realtime"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading real-time dashboard..." />}>
              <RealTimeDashboard />
            </React.Suspense>
          }
        />
        <Route
          path="events"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading events..." />}>
              <Events />
            </React.Suspense>
          }
        />
        <Route
          path="reports"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading reports..." />}>
              <Reports />
            </React.Suspense>
          }
        />
        <Route
          path="analytics"
          element={
            <React.Suspense fallback={<Loading size="lg" text="Loading analytics..." />}>
              <Analytics />
            </React.Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App