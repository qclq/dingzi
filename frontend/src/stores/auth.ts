import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/api/http'
import type { AuthResponse, MenuItem, UserInfo } from '@/types/auth'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'
const USER_KEY = 'user_info'
const REMEMBER_KEY = 'remember_login'
const AUTH_KEYS = [ACCESS_KEY, REFRESH_KEY, USER_KEY, REMEMBER_KEY] as const

function clearStorage(storage: Storage): void {
  AUTH_KEYS.forEach((key) => storage.removeItem(key))
}

function readUser(storage: Storage): UserInfo | null {
  const raw = storage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    clearStorage(storage)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const rememberLogin = ref(localStorage.getItem(REMEMBER_KEY) === 'true')
  const initialStorage = rememberLogin.value ? localStorage : sessionStorage
  const accessToken = ref(initialStorage.getItem(ACCESS_KEY) ?? '')
  const refreshToken = ref(initialStorage.getItem(REFRESH_KEY) ?? '')
  const user = ref<UserInfo | null>(readUser(initialStorage))
  const menus = ref<MenuItem[]>([])
  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))

  function persist(data: AuthResponse['data'], remember: boolean): void {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user_info
    rememberLogin.value = remember
    const target = remember ? localStorage : sessionStorage
    const other = remember ? sessionStorage : localStorage
    clearStorage(other)
    target.setItem(ACCESS_KEY, data.access_token)
    target.setItem(REFRESH_KEY, data.refresh_token)
    target.setItem(USER_KEY, JSON.stringify(data.user_info))
    target.setItem(REMEMBER_KEY, String(remember))
  }

  function clear(): void {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    menus.value = []
    rememberLogin.value = false
    clearStorage(localStorage)
    clearStorage(sessionStorage)
  }

  async function login(username: string, password: string, rememberMe: boolean): Promise<void> {
    const response = await http.post<AuthResponse>('/auth/login', { username, password, remember_me: rememberMe })
    persist(response.data.data, rememberMe)
    await loadMenus()
  }

  async function refresh(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const response = await http.post<AuthResponse>('/auth/refresh', { refresh_token: refreshToken.value })
      persist(response.data.data, rememberLogin.value)
      return true
    } catch {
      clear()
      return false
    }
  }

  async function logout(): Promise<void> {
    try {
      if (accessToken.value) await http.post('/auth/logout', { refresh_token: refreshToken.value })
    } finally { clear() }
  }

  async function loadMenus(): Promise<void> {
    if (!accessToken.value) return
    const response = await http.get<MenuItem[]>('/me/menus')
    menus.value = response.data
  }

  return { accessToken, refreshToken, user, menus, isAuthenticated, login, refresh, logout, clear, loadMenus }
})
