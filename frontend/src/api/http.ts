import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'

export const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1', timeout: 10_000 })
http.interceptors.request.use((config) => {
  const storage = localStorage.getItem('remember_login') === 'true' ? localStorage : sessionStorage
  const token = storage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing = false
let refreshPromise: Promise<boolean> | null = null
http.interceptors.response.use((response) => response, async (error: AxiosError) => {
  const config = error.config as (InternalAxiosRequestConfig & { _authRetry?: boolean }) | undefined
  const url = config?.url ?? ''
  if (error.response?.status !== 401 || !config || config._authRetry || url.includes('/auth/')) throw error
  config._authRetry = true
  const auth = useAuthStore()
  if (!refreshing) { refreshing = true; refreshPromise = auth.refresh().finally(() => { refreshing = false; refreshPromise = null }) }
  const refreshed = await refreshPromise
  if (!refreshed) { const { default: router } = await import('@/router'); await router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } }); throw error }
  config.headers.Authorization = `Bearer ${auth.accessToken}`
  return http.request(config)
})

