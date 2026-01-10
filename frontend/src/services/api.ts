import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const authData = localStorage.getItem('openspotter-auth')
  if (authData) {
    try {
      const { state } = JSON.parse(authData)
      if (state?.accessToken) {
        config.headers.Authorization = `Bearer ${state.accessToken}`
      }
    } catch {
      // Ignore parse errors
    }
  }
  return config
})

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const authData = localStorage.getItem('openspotter-auth')
      if (authData) {
        try {
          const { state } = JSON.parse(authData)
          if (state?.refreshToken) {
            const response = await axios.post(`${API_URL}/auth/refresh`, {
              refresh_token: state.refreshToken,
            })

            const newState = {
              ...state,
              accessToken: response.data.access_token,
              refreshToken: response.data.refresh_token,
            }

            localStorage.setItem(
              'openspotter-auth',
              JSON.stringify({ state: newState })
            )

            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
            return api(originalRequest)
          }
        } catch {
          // Refresh failed, clear auth
          localStorage.removeItem('openspotter-auth')
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

// API functions
export const fetchActiveSpotters = async () => {
  const response = await api.get('/locations/active')
  return response.data
}

export const fetchReports = async (params?: {
  type?: string
  hours?: number
  verified_only?: boolean
}) => {
  const response = await api.get('/reports/geojson', { params })
  return response.data
}

export const createReport = async (data: {
  type: string
  latitude: number
  longitude: number
  description?: string
  severity?: number
  hail_size?: number
  wind_speed?: number
  media_urls?: string[]
  post_to_twitter?: boolean
}) => {
  const response = await api.post('/reports', data)
  return response.data
}

export const uploadMedia = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/reports/upload-media', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const updateLocation = async (data: {
  latitude: number
  longitude: number
  altitude?: number
  accuracy?: number
  heading?: number
  speed?: number
}) => {
  const response = await api.post('/locations/update', data)
  return response.data
}

export const fetchChannels = async () => {
  const response = await api.get('/messages/channels')
  return response.data
}

export const fetchChannelMessages = async (channelId: string) => {
  const response = await api.get(`/messages/channels/${channelId}/messages`)
  return response.data
}

export const sendMessage = async (data: {
  content: string
  channel_id?: string
  recipient_id?: string
}) => {
  const response = await api.post('/messages', data)
  return response.data
}
