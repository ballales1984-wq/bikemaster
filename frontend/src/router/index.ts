import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn, isAdmin, token, user, parseJWTPayload } from '../composables/useAuth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: { template: '<div />' }
  },
  {
    path: '/rides',
    name: 'rides',
    component: () => import('../views/RidesView.vue'),
    meta: { requiresAuth: true }
  },
{
    path: '/import',
    name: 'import',
    component: () => import('../components/ImportPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/athlete',
    name: 'athlete',
    component: () => import('../components/AthletePanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/coach',
    name: 'coach',
    component: () => import('../components/CoachPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('../components/KnowledgePanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/calendar',
    name: 'calendar',
    component: () => import('../components/CalendarPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/granfondo',
    name: 'granfondo',
    component: () => import(/* webpackChunkName: "granfondo" */ '../components/GranfondoPlanner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/map',
    name: 'map',
    component: () => import(/* webpackChunkName: "map" */ '../components/RideMapPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/comparison',
    name: 'comparison',
    component: () => import('../components/RideComparison.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/heatmap',
    name: 'heatmap',
    component: () => import(/* webpackChunkName: "heatmap" */ '../components/HeatmapPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/badges',
    name: 'badges',
    component: () => import('../components/BadgesPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/weather',
    name: 'weather',
    component: () => import('../components/WeatherPanel.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../components/AdminPanel.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/track',
    name: 'tracking',
    component: () => import('../views/RideTracking.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/privacy',
    name: 'privacy',
    component: () => import('../views/PrivacyPolicy.vue')
  },
  {
    path: '/terms',
    name: 'terms',
    component: () => import('../views/TermsOfService.vue')
  },
  {
    path: '/cookies',
    name: 'cookies',
    component: () => import('../views/CookiePolicy.vue')
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/AboutUs.vue')
  },
  {
    path: '/contact',
    name: 'contact',
    component: () => import('../views/ContactUs.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, from) => {
  // Handle OAuth callback token from URL params
  if (to.query.token && typeof to.query.token === 'string') {
    token.value = to.query.token
    const payload = parseJWTPayload(to.query.token)
    user.value = {
      id: typeof to.query.user_id === 'string' ? parseInt(to.query.user_id, 10) : 0,
      username: typeof payload?.sub === 'string' ? payload.sub : '',
      is_admin: !!payload?.is_admin,
    }
    localStorage.setItem('bikemaster_token', to.query.token)
    localStorage.setItem('bikemaster_user', JSON.stringify(user.value))
  }

  const loggedIn = isLoggedIn()

  if (to.path === '/' && loggedIn) {
    return '/rides'
  } else if (to.meta.requiresAuth && !loggedIn) {
    return '/'
  } else if (to.meta.requiresAdmin && !isAdmin()) {
    return '/'
  }
})

export default router