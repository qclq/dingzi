// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'
import { createAppRouter } from '@/router'

function authenticate(role: 'admin' | 'operator'): void {
  sessionStorage.setItem('access_token', `${role}-access`)
  sessionStorage.setItem('refresh_token', `${role}-refresh`)
  sessionStorage.setItem('remember_login', 'false')
  sessionStorage.setItem('user_info', JSON.stringify({
    user_id: 1,
    username: role,
    display_name: role,
    role,
  }))
}

describe('authentication route guard', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it.each(['/', '/realtime', '/history', '/history/1', '/analytics'])('redirects anonymous access to %s', async (path) => {
    const router = createAppRouter(createMemoryHistory())

    await router.push(path)

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe(path)
  })

  it('redirects an authenticated operator away from admin routes', async () => {
    authenticate('operator')
    const router = createAppRouter(createMemoryHistory())

    await router.push('/system')

    expect(router.currentRoute.value.path).toBe('/403')
  })

  it('allows an authenticated administrator to access admin routes', async () => {
    authenticate('admin')
    const router = createAppRouter(createMemoryHistory())

    await router.push('/system')

    expect(router.currentRoute.value.path).toBe('/system')
  })
})
