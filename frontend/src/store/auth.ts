import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../services/api'

interface User {
  id: string
  email: string
  callsign: string | null
  display_name: string | null
  role: string
  is_email_verified: boolean
  totp_enabled: boolean
  share_location_with: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string, totpCode?: string) => Promise<void>
  register: (email: string, password: string, callsign?: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
  fetchUser: () => Promise<void>
  updateUser: (data: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password, totpCode) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post('/auth/login', {
            email,
            password,
            totp_code: totpCode,
          })

          const { access_token, refresh_token } = response.data

          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })

          // Fetch user profile
          await get().fetchUser()
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || 'Login failed',
          })
          throw error
        }
      },

      register: async (email, password, callsign) => {
        set({ isLoading: true, error: null })
        try {
          await api.post('/auth/register', {
            email,
            password,
            callsign,
          })

          // Auto-login after registration
          await get().login(email, password)
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || 'Registration failed',
          })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          get().logout()
          return
        }

        try {
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken,
          })

          set({
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
          })
        } catch {
          get().logout()
        }
      },

      fetchUser: async () => {
        try {
          const response = await api.get('/users/me')
          set({ user: response.data })
        } catch {
          // Token might be invalid
          get().logout()
        }
      },

      updateUser: (data) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...data } : null,
        }))
      },
    }),
    {
      name: 'openspotter-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        user: state.user,
      }),
    }
  )
)
