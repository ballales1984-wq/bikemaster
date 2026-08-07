/**
 * Syncs the authentication state for the Pinia store.
 *
 * On startup it validates the in-memory token; if absent or expired
 * the state is considered unauthenticated. Returns an object with
 * the resulting state (hasToken, justLoggedIn).
 *
 * Exports: syncAuthState
 */

import { useAuthStore } from "../stores/auth";

export function syncAuthState() {
  const auth = useAuthStore();
  if (auth.token && !auth.isTokenValid()) {
    if (auth.refreshToken) {
      void auth.refreshAccessToken().then((ok) => {
        if (!ok) {
          auth.token = "";
          auth.user = null;
          auth.setJustLoggedIn(false);
        }
      });
      return { hasToken: !!auth.token, justLoggedIn: auth.justLoggedIn };
    }
    auth.token = "";
    auth.user = null;
    auth.setJustLoggedIn(false);
    return { hasToken: false, justLoggedIn: false };
  }

  const result = { hasToken: !!auth.token, justLoggedIn: auth.justLoggedIn };
  return result;
}
