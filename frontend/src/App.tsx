import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import LoginForm from '@/components/auth/LoginForm'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import { Loading } from '@/components/ui'

// Lazy load other pages for better performance
const DNSZones = React.lazy(() => import('@/pages/DNSZones'))
const Forwarders = React.lazy(() => import('@/pages/Forwarders'))
const Security = React.lazy(() => import('@/pages/Security'))
const QueryLogs = React.lazy(() => import('@/pages/QueryLogs'))
const Settings = React.lazy(() => import('@/pages/Settings'))

const App: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()

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
        <Route index element={<Dashboard />} />
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App