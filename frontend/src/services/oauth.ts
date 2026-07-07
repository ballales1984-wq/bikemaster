import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'

export function processOAuthToken() {
  const auth = useAuthStore()
  const ui = useUIStore()
  const urlParams = new URLSearchParams(window.location.search)
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const urlToken = urlParams.get('token') || hashParams.get('token')
  const email = urlParams.get('email') || hashParams.get('email') || ''
  const oauthError = urlParams.get('oauth_error') || hashParams.get('oauth_error')

  if (urlToken) {
    auth.setAuthFromUrl(urlToken, email)
    ui.setOauthLoading(false)
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, '/')
    }
    return true
  }

  if (oauthError) {
    auth.setOauthError(oauthError)
    ui.setOauthLoading(false)
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, '/')
    }
    return true
  }

  return false
}
