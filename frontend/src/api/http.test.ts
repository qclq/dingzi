// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { http } from '@/api/http'

const originalAdapter = http.defaults.adapter

function response(config: InternalAxiosRequestConfig, data: unknown): AxiosResponse {
  return { data, status: 200, statusText: 'OK', headers: {}, config }
}

function unauthorized(config: InternalAxiosRequestConfig): AxiosError {
  return new AxiosError(
    'Unauthorized',
    'ERR_BAD_REQUEST',
    config,
    undefined,
    { data: {}, status: 401, statusText: 'Unauthorized', headers: {}, config },
  )
}

describe('authenticated HTTP client', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    http.defaults.adapter = originalAdapter
    vi.restoreAllMocks()
  })

  it('injects a session-scoped access token into Authorization', async () => {
    sessionStorage.setItem('access_token', 'session-access')
    const adapter = vi.fn<AxiosAdapter>(async (config) => response(config, { ok: true }))
    http.defaults.adapter = adapter

    await http.get('/me')

    expect(adapter.mock.calls[0]?.[0].headers.get('Authorization')).toBe('Bearer session-access')
  })

  it('performs only one refresh for concurrent 401 responses and retries both requests', async () => {
    sessionStorage.setItem('access_token', 'access-old')
    sessionStorage.setItem('refresh_token', 'refresh-old')
    sessionStorage.setItem('remember_login', 'false')
    sessionStorage.setItem('user_info', JSON.stringify({
      user_id: 1,
      username: 'operator',
      display_name: '操作员',
      role: 'operator',
    }))
    let refreshCalls = 0
    const adapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/refresh') {
        refreshCalls += 1
        await Promise.resolve()
        return response(config, {
          code: 'SUCCESS', message: '刷新成功', trace_id: 'trace-2',
          data: {
            access_token: 'access-new', refresh_token: 'refresh-new', token_type: 'Bearer', expires_in: 28_800,
            user_info: { user_id: 1, username: 'operator', display_name: '操作员', role: 'operator' },
          },
        })
      }
      if (config.headers.get('Authorization') === 'Bearer access-old') throw unauthorized(config)
      return response(config, { ok: true })
    }
    http.defaults.adapter = vi.fn(adapter)

    const [first, second] = await Promise.all([http.get('/first'), http.get('/second')])

    expect(first.data).toEqual({ ok: true })
    expect(second.data).toEqual({ ok: true })
    expect(refreshCalls).toBe(1)
    expect(sessionStorage.getItem('access_token')).toBe('access-new')
    expect(sessionStorage.getItem('refresh_token')).toBe('refresh-new')
  })
})
