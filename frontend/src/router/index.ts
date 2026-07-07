import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { syncAuthState } from '../services/authSync'

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
    meta: { title: 'Le mie uscite' }
  },
  {
    path: '/import',
    name: 'import',
    component: () => import('../components/ImportPanel.vue'),
    meta: { requiresAuth: true, title: 'Importa uscite' }
  },
  {
    path: '/athlete',
    name: 'athlete',
    component: () => import('../components/AthletePanel.vue'),
    meta: { requiresAuth: true, title: 'Profilo atleta' }
  },
  {
    path: '/coach',
    name: 'coach',
    component: () => import('../components/CoachPanel.vue'),
    meta: { requiresAuth: true, title: 'AI Coach' }
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('../components/KnowledgePanel.vue'),
    meta: { requiresAuth: true, title: 'Knowledge Base' }
  },
  {
    path: '/calendar',
    name: 'calendar',
    component: () => import('../components/CalendarPanel.vue'),
    meta: { requiresAuth: true, title: 'Calendario' }
  },
  {
    path: '/granfondo',
    name: 'granfondo',
    component: () => import('../components/GranfondoPlanner.vue'),
    meta: { requiresAuth: true, title: 'Granfondo Planner' }
  },
  {
    path: '/map',
    name: 'map',
    component: () => import('../components/RideMapPanel.vue'),
    meta: { requiresAuth: true, title: 'Mappa uscite' }
  },
  {
    path: '/comparison',
    name: 'comparison',
    component: () => import('../components/RideComparison.vue'),
    meta: { requiresAuth: true, title: 'Confronto uscite' }
  },
  {
    path: '/heatmap',
    name: 'heatmap',
    component: () => import('../components/HeatmapPanel.vue'),
    meta: { requiresAuth: true, title: 'Heatmap' }
  },
  {
    path: '/badges',
    name: 'badges',
    component: () => import('../components/BadgesPanel.vue'),
    meta: { requiresAuth: true, title: 'Badge' }
  },
  {
    path: '/weather',
    name: 'weather',
    component: () => import('../components/WeatherPanel.vue'),
    meta: { requiresAuth: true, title: 'Meteo' }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../components/AdminPanel.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Amministrazione' }
  },
  {
    path: '/track',
    name: 'tracking',
    component: () => import('../views/RideTracking.vue'),
    meta: { requiresAuth: true, title: 'Tracciamento uscita' }
  },
  {
    path: '/privacy',
    name: 'privacy',
    component: () => import('../views/PrivacyPolicy.vue'),
    meta: { title: 'Privacy Policy' }
  },
  {
    path: '/terms',
    name: 'terms',
    component: () => import('../views/TermsOfService.vue'),
    meta: { title: 'Termini di servizio' }
  },
  {
    path: '/cookies',
    name: 'cookies',
    component: () => import('../views/CookiePolicy.vue'),
    meta: { title: 'Cookie Policy' }
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/AboutUs.vue'),
    meta: { title: 'Chi siamo' }
  },
  {
    path: '/contact',
    name: 'contact',
    component: () => import('../views/ContactUs.vue'),
    meta: { title: 'Contatti' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (to && to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

async function checkProfileComplete(auth: ReturnType<typeof useAuthStore>): Promise<boolean> {
  try {
    const resp = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    if (!resp.ok) return false
    const data = await resp.json()
    return data.profile_complete === true
  } catch {
    return false
  }
}

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  const ui = useUIStore()
  const { hasToken, justLoggedIn } = syncAuthState()

  if (to.meta.requiresAuth && !hasToken) {
    next('/')
    return
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    next('/')
    return
  }

  if (hasToken && (to.path === '/' || justLoggedIn)) {
    const hasCompleteProfile = await checkProfileComplete(auth)
    next(hasCompleteProfile ? '/rides' : '/athlete')
    localStorage.removeItem('bikemaster_just_logged_in')
    auth.setJustLoggedIn(false)
    ui.setOauthLoading(false)
    return
  }

  if (ui.oauthLoading) {
    ui.setOauthLoading(false)
  }

  next()
})

router.afterEach((to) => {
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
})

export default router
