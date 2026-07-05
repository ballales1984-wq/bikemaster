import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

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
    component: () => import('../components/GranfondoPlanner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/map',
    name: 'map',
    component: () => import('../components/RideMapPanel.vue'),
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
    component: () => import('../components/HeatmapPanel.vue'),
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

async function checkProfileComplete(auth: ReturnType<typeof useAuthStore>): Promise<boolean> {
  try {
    const resp = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${auth.token.value}` }
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
   // Handle OAuth callback token from URL fragment
   if (!to.query.token && to.hash) {
     const hashParams = new URLSearchParams(to.hash.replace(/^#/, ''))
     const fragmentToken = hashParams.get('token')
     if (fragmentToken) {
       auth.token.value = fragmentToken
       const payload = auth.parseJWTPayload(fragmentToken)
       auth.user.value = {
         id: hashParams.get('user_id') ? parseInt(hashParams.get('user_id')!, 10) : 0,
         username: typeof payload?.sub === 'string' ? payload.sub : '',
         is_admin: !!payload?.is_admin,
       }
        localStorage.setItem('bikemaster_token', fragmentToken)
        localStorage.setItem('bikemaster_user', JSON.stringify(auth.user.value))
      }
    }

    // Also handle query params for backward compatibility
   if (to.query.token && typeof to.query.token === 'string') {
     auth.token.value = to.query.token
     const payload = auth.parseJWTPayload(to.query.token)
     auth.user.value = {
       id: typeof to.query.user_id === 'string' ? parseInt(to.query.user_id, 10) : 0,
       username: typeof payload?.sub === 'string' ? payload.sub : '',
       is_admin: !!payload?.is_admin,
     }
     localStorage.setItem('bikemaster_token', to.query.token)
     localStorage.setItem('bikemaster_user', JSON.stringify(auth.user.value))
   }

   // Check for invalid/expired token and clean up
   if (auth.token.value && !auth.isTokenValid()) {
     auth.token.value = ''
     auth.user.value = null
     localStorage.removeItem('bikemaster_token')
     localStorage.removeItem('bikemaster_user')
   }

    const loggedIn = auth.isLoggedIn.value

    if (to.path === '/' && loggedIn) {
      const hasCompleteProfile = await checkProfileComplete(auth)
      if (!hasCompleteProfile) {
        const toast = useToast()
        toast.show('Welcome! Please complete your athlete profile', 'info')
      }
      window.dispatchEvent(new CustomEvent('oauth-loading-end'))
      next(hasCompleteProfile ? '/rides' : '/athlete')
    } else if (to.path === '/rides' && loggedIn) {
      const hasCompleteProfile = await checkProfileComplete(auth)
      if (!hasCompleteProfile) {
        const toast = useToast()
        toast.show('Complete your profile to see your rides', 'info')
        window.dispatchEvent(new CustomEvent('oauth-loading-end'))
        next('/athlete')
      } else {
        window.dispatchEvent(new CustomEvent('oauth-loading-end'))
        next()
      }
    } else if (to.meta.requiresAuth && !loggedIn) {
      next('/')
    } else if (to.meta.requiresAdmin && !auth.isAdmin.value) {
      next('/')
    } else {
      next()
    }
})

export default router