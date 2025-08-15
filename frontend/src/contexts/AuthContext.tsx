import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { User, LoginRequest, LoginResponse } from '@/types'
import { authApi } from '@/services/api'
import { toast } from 'react-toastify'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  accessToken: string | null
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    accessToken: null,
  })

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token')
        const refreshTokenValue = localStorage.getItem('refresh_token')
        
        if (token && refreshTokenValue) {
          // Set token in axios headers
          authApi.defaults.headers.common['Authorization'] = `Bearer ${token}`
          
          // Try to get current user
          const response = await authApi.get('/auth/me')
          setAuthState({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
            accessToken: token,
          })
        } else {
          setAuthState(prev => ({ ...prev, isLoading: false }))
        }
      } catch (error) {
        // Token might be invalid, try to refresh
        try {
          await refreshToken()
        } catch (refreshError) {
          // Refresh failed, clear everything
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          delete authApi.defaults.headers.common['Authorization']
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            accessToken: null,
          })
        }
      }
    }

    initializeAuth()
  }, [])

  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      const response = await authApi.post<LoginResponse>('/auth/login', credentials)
      const { access_token, refresh_token, user } = response.data

      // Store tokens
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      
      // Set authorization header
      authApi.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        accessToken: access_token,
      })

      toast.success('Login successful!')
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed'
      toast.error(message)
      throw error
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await authApi.post('/auth/logout')
    } catch (error) {
      // Even if logout fails on server, clear local state
      console.error('Logout error:', error)
    } finally {
      // Clear local storage and state
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      delete authApi.defaults.headers.common['Authorization']
      
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        accessToken: null,
      })

      toast.success('Logged out successfully')
    }
  }

  const refreshToken = async (): Promise<void> => {
    try {
      const refreshTokenValue = localStorage.getItem('refresh_token')
      if (!refreshTokenValue) {
        throw new Error('No refresh token available')
      }

      const response = await authApi.post<LoginResponse>('/auth/refresh', {
        refresh_token: refreshTokenValue,
      })

      const { access_token, refresh_token: newRefreshToken, user } = response.data

      // Store new tokens
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', newRefreshToken)
      
      // Set authorization header
      authApi.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        accessToken: access_token,
      })
    } catch (error) {
      // Refresh failed, logout user
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      delete authApi.defaults.headers.common['Authorization']
      
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        accessToken: null,
      })
      
      throw error
    }
  }

  const updateUser = (user: User): void => {
    setAuthState(prev => ({ ...prev, user }))
  }

  const value: AuthContextType = {
    ...authState,
    login,
    logout,
    refreshToken,
    updateUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}