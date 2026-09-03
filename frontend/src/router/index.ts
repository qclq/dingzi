import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export function createAppRouter(history: RouterHistory = createWebHistory(import.meta.env.BASE_URL)) {
  const router = createRouter({
    history,
    routes: [
      { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
      { path: '/403', name: 'forbidden', component: () => import('@/views/ForbiddenView.vue') },
      {
        path: '/', component: () => import('@/layouts/AppLayout.vue'), meta: { requiresAuth: true },
        children: [
          { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
          { path: 'realtime', component: () => import('@/views/realtime/RealtimeView.vue') },
          { path: 'history', name: 'history', component: () => import('@/views/history/HistoryListView.vue') },
          { path: 'history/:id', name: 'history-detail', component: () => import('@/views/history/HistoryDetailView.vue') },
          { path: 'analytics', name: 'analytics', component: () => import('@/views/analytics/AnalyticsView.vue') },
          { path: 'config', component: () => import('@/views/ConfigView.vue'), meta: { roles: ['admin'] } },
          { path: 'system', component: () => import('@/views/SystemView.vue'), meta: { roles: ['admin'] } },
        ],
      },
    ],
  })

  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (to.path === '/login' && auth.isAuthenticated) return '/'
    const requiresAuth = to.matched.some((record) => record.meta.requiresAuth === true)
    if (requiresAuth && !auth.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (to.meta.roles && !(to.meta.roles as string[]).includes(auth.user?.role ?? '')) return '/403'
    return true
  })

  return router
}

export default createAppRouter()
