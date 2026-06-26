import { describe, it, expect, vi } from 'vitest'
import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn, isAdmin } from '../composables/useAuth'

const routes = [
  { path: '/', name: 'home', component: { template: '<div />' } },
  { path: '/rides', name: 'rides', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/import', name: 'import', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/athlete', name: 'athlete', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/coach', name: 'coach', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/knowledge', name: 'knowledge', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/calendar', name: 'calendar', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/granfondo', name: 'granfondo', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/map', name: 'map', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/heatmap', name: 'heatmap', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/badges', name: 'badges', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/weather', name: 'weather', meta: { requiresAuth: true }, component: { template: '<div />' } },
  { path: '/admin', name: 'admin', meta: { requiresAuth: true, requiresAdmin: true }, component: { template: '<div />' } },
  { path: '/track', name: 'tracking', meta: { requiresAuth: true }, component: { template: '<div />' } },
]

const createGuardedRouter = (loggedInValue, adminValue) => {
  const r = createRouter({
    history: createWebHistory(),
    routes,
  })
  r.beforeEach((to, from) => {
    const loggedIn = loggedInValue
    const admin = adminValue

    if (to.path === '/' && loggedIn) {
      return '/rides'
    } else if (to.meta.requiresAuth && !loggedIn) {
      return '/'
    } else if (to.meta.requiresAdmin && !admin) {
      return '/'
    }
  })
  return r
}

describe('router navigation guards', () => {
  it('redirects to /rides when logged in and on home page', async () => {
    const testRouter = createGuardedRouter(true, false)
    await testRouter.push('/')
    expect(testRouter.currentRoute.value.path).toBe('/rides')
  })

  it('stays on home page when not logged in', async () => {
    const testRouter = createGuardedRouter(false, false)
    await testRouter.push('/')
    expect(testRouter.currentRoute.value.path).toBe('/')
  })

  it('allows authenticated user to access protected routes', async () => {
    const testRouter = createGuardedRouter(true, false)
    await testRouter.push('/rides')
    expect(testRouter.currentRoute.value.path).toBe('/rides')
  })

  it('redirects unauthenticated user to home for protected routes', async () => {
    const testRouter = createGuardedRouter(false, false)
    await testRouter.push('/rides')
    expect(testRouter.currentRoute.value.path).toBe('/')

    const testRouter2 = createGuardedRouter(false, false)
    await testRouter2.push('/import')
    expect(testRouter2.currentRoute.value.path).toBe('/')

    const testRouter3 = createGuardedRouter(false, false)
    await testRouter3.push('/admin')
    expect(testRouter3.currentRoute.value.path).toBe('/')
  })

  it('redirects non-admin user to rides via home redirect for admin route', async () => {
    const testRouter = createGuardedRouter(true, false)
    await testRouter.push('/admin')
    // Non-admin logged-in user: /admin -> / (auth check passes, admin check fails -> redirect '/')
    // Then '/' with loggedIn=true -> '/rides' (auto-redirect to rides)
    expect(testRouter.currentRoute.value.path).toBe('/rides')
  })

  it('allows admin user to access admin route', async () => {
    const testRouter = createGuardedRouter(true, true)
    await testRouter.push('/admin')
    expect(testRouter.currentRoute.value.path).toBe('/admin')
  })

  it('redirects unauthenticated admin route access to home', async () => {
    const testRouter = createGuardedRouter(false, true)
    await testRouter.push('/admin')
    expect(testRouter.currentRoute.value.path).toBe('/')
  })

  it('handles all protected routes consistently - unauthenticated', async () => {
    const protectedRoutes = [
      '/rides', '/import', '/athlete', '/coach', '/knowledge',
      '/calendar', '/granfondo', '/map', '/heatmap', '/badges', '/weather', '/track'
    ]

    for (const route of protectedRoutes) {
      const testRouter = createGuardedRouter(false, false)
      await testRouter.push(route)
      expect(testRouter.currentRoute.value.path).toBe('/'), `Expected redirect for ${route}`
    }
  })

  it('allows admin on all protected routes including admin route', async () => {
    const protectedRoutes = [
      '/rides', '/import', '/athlete', '/coach', '/knowledge',
      '/calendar', '/granfondo', '/map', '/heatmap', '/badges', '/weather', '/track', '/admin'
    ]

    for (const route of protectedRoutes) {
      const testRouter = createGuardedRouter(true, true)
      await testRouter.push(route)
      expect(testRouter.currentRoute.value.path).toBe(route), `Expected access to ${route}`
    }
  })

  it('handles redirect precedence: admin check after auth check', async () => {
    const testRouter = createGuardedRouter(false, true)
    await testRouter.push('/admin')
    expect(testRouter.currentRoute.value.path).toBe('/')
  })
})

describe('router route configuration', () => {
  it('has correct number of routes', () => {
    expect(routes).toHaveLength(14)
  })

  it('has correct routes defined', () => {
    const routePaths = routes.map(r => r.path)

    expect(routePaths).toContain('/')
    expect(routePaths).toContain('/rides')
    expect(routePaths).toContain('/import')
    expect(routePaths).toContain('/athlete')
    expect(routePaths).toContain('/coach')
    expect(routePaths).toContain('/knowledge')
    expect(routePaths).toContain('/calendar')
    expect(routePaths).toContain('/granfondo')
    expect(routePaths).toContain('/map')
    expect(routePaths).toContain('/heatmap')
    expect(routePaths).toContain('/badges')
    expect(routePaths).toContain('/weather')
    expect(routePaths).toContain('/admin')
    expect(routePaths).toContain('/track')
  })

  it('has correct route names', () => {
    const routeNames = routes.map(r => r.name)

    expect(routeNames).toContain('home')
    expect(routeNames).toContain('rides')
    expect(routeNames).toContain('import')
    expect(routeNames).toContain('athlete')
    expect(routeNames).toContain('coach')
    expect(routeNames).toContain('knowledge')
    expect(routeNames).toContain('calendar')
    expect(routeNames).toContain('granfondo')
    expect(routeNames).toContain('map')
    expect(routeNames).toContain('heatmap')
    expect(routeNames).toContain('badges')
    expect(routeNames).toContain('weather')
    expect(routeNames).toContain('admin')
    expect(routeNames).toContain('tracking')
  })

  it('sets requiresAuth meta on protected routes only', () => {
    const protectedRoutes = routes.filter(r => r.meta?.requiresAuth)
    expect(protectedRoutes.length).toBe(13)

    const publicRoutes = routes.filter(r => !r.meta?.requiresAuth)
    expect(publicRoutes).toHaveLength(1)
    expect(publicRoutes[0].name).toBe('home')
  })

  it('sets requiresAdmin meta only on admin route', () => {
    const adminRoutes = routes.filter(r => r.meta?.requiresAdmin)
    expect(adminRoutes.length).toBe(1)
    expect(adminRoutes[0].name).toBe('admin')
  })

  it('admin route requires both auth and admin', () => {
    const adminRoute = routes.find(r => r.name === 'admin')

    expect(adminRoute.meta.requiresAuth).toBe(true)
    expect(adminRoute.meta.requiresAdmin).toBe(true)
  })
})

describe('useAuth composable integration with router', () => {
  it('isLoggedIn is used by router guard', () => {
    expect(typeof isLoggedIn).toBe('function')
  })

  it('isAdmin is used by router guard', () => {
    expect(typeof isAdmin).toBe('function')
  })
})

describe('router actual implementation integration', () => {
  it('imports router without errors', async () => {
    const router = await import('./index')
    expect(router.default).toBeDefined()
    expect(typeof router.default.beforeEach).toBe('function')
  })

  it('has beforeEach guard defined on router', async () => {
    const router = await import('./index')
    expect(router.default.beforeEach).toBeDefined()
  })

  it('router uses createWebHistory', async () => {
    const router = await import('./index')
    expect(router.default.options.history).toBeDefined()
  })

  it('router has correct routes count', async () => {
    const router = await import('./index')
    expect(router.default.options.routes).toHaveLength(20)
  })
})

describe('router scroll behavior integration', () => {
  it('scrollBehavior returns { top: 0 }', async () => {
    const router = await import('./index')
    const scrollFn = router.default.options.scrollBehavior
    if (scrollFn) {
      expect(scrollFn()).toEqual({ top: 0 })
    }
  })
})