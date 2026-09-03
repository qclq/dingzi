// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { AuthResponse, MenuItem } from '@/types/auth'

vi.mock('@/api/http', () => ({
  http: { post: vi.fn(), get: vi.fn() },
}))

const mockedHttp = http as unknown as {
  post: ReturnType<typeof vi.fn>
  get: ReturnType<typeof vi.fn>
}

const menus: MenuItem[] = [
  { name: 'history', label: '历史记录', path: '/history', roles: ['admin', 'operator'] },
]

function authResponse(accessToken = 'access-1', refreshToken = 'refresh-1'): AuthResponse {
  return {
    code: 'SUCCESS',
    message: '登录成功',
    trace_id: 'trace-1',
    data: {
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'Bearer',
      expires_in: 28_800,
      user_info: {
        user_id: 1,
        username: 'operator',
        display_name: '操作员',
        role: 'operator',
      },
    },
  }
}

describe('authentication persistence', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockedHttp.get.mockResolvedValue({ data: menus })
  })

  it('keeps the complete login session in sessionStorage when remember-me is disabled', async () => {
    mockedHttp.post.mockResolvedValue({ data: authResponse() })
    const auth = useAuthStore()

    await auth.login('operator', 'Operator123!', false)

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user_info')).toBeNull()
    expect(sessionStorage.getItem('access_token')).toBe('access-1')
    expect(sessionStorage.getItem('refresh_token')).toBe('refresh-1')
    expect(sessionStorage.getItem('remember_login')).toBe('false')
    expect(auth.menus).toEqual(menus)
    expect(mockedHttp.get).toHaveBeenCalledWith('/me/menus')
  })

  it('persists the complete login session in localStorage when remember-me is enabled', async () => {
    mockedHttp.post.mockResolvedValue({ data: authResponse() })
    const auth = useAuthStore()

    await auth.login('operator', 'Operator123!', true)

    expect(localStorage.getItem('access_token')).toBe('access-1')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1')
    expect(localStorage.getItem('remember_login')).toBe('true')
    expect(sessionStorage.getItem('access_token')).toBeNull()
    expect(sessionStorage.getItem('refresh_token')).toBeNull()
  })

  it('rotates tokens without changing the selected storage lifetime', async () => {
    sessionStorage.setItem('access_token', 'access-old')
    sessionStorage.setItem('refresh_token', 'refresh-old')
    sessionStorage.setItem('remember_login', 'false')
    sessionStorage.setItem('user_info', JSON.stringify(authResponse().data.user_info))
    mockedHttp.post.mockResolvedValue({ data: authResponse('access-new', 'refresh-new') })
    const auth = useAuthStore()

    expect(await auth.refresh()).toBe(true)

    expect(sessionStorage.getItem('access_token')).toBe('access-new')
    expect(sessionStorage.getItem('refresh_token')).toBe('refresh-new')
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('clears both storage scopes on logout', async () => {
    localStorage.setItem('access_token', 'stale-local')
    sessionStorage.setItem('access_token', 'access-1')
    sessionStorage.setItem('refresh_token', 'refresh-1')
    sessionStorage.setItem('remember_login', 'false')
    sessionStorage.setItem('user_info', JSON.stringify(authResponse().data.user_info))
    mockedHttp.post.mockResolvedValue({ data: {} })
    const auth = useAuthStore()

    await auth.logout()

    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(auth.isAuthenticated).toBe(false)
  })
})
