/**
 * Syncs the authentication state between the Pinia store and localStorage.
 *
 * On startup it restores the token and user profile from local storage;
 * if the token is present but expired, it removes it. Returns an object
 * with the resulting state (hasToken, justLoggedIn).
 *
 * Exports: syncAuthState
 */

import { useAuthStore } from "../stores/auth";
import {
  AUTH_TOKEN_KEY,
  AUTH_USER_KEY,
  AUTH_JUST_LOGGED_IN_KEY,
} from "../utils/auth-storage";

export function syncAuthState() {
  const auth = useAuthStore();
  const hasLocalStorage = typeof localStorage !== "undefined";
  const storedToken = hasLocalStorage
    ? localStorage.getItem(AUTH_TOKEN_KEY)
    : null;
  const storedJustLoggedIn = hasLocalStorage
    ? localStorage.getItem(AUTH_JUST_LOGGED_IN_KEY) === "true"
    : false;

  if (hasLocalStorage && !auth.token && storedToken) {
    auth.token = storedToken;
  }
  if (
    hasLocalStorage &&
    !auth.user &&
    localStorage.getItem(AUTH_USER_KEY)
  ) {
    try {
      auth.user = JSON.parse(localStorage.getItem(AUTH_USER_KEY)!);
    } catch {}
  }
  if (!auth.justLoggedIn && storedJustLoggedIn) {
    auth.setJustLoggedIn(true);
  }

  if (auth.token && !auth.isTokenValid()) {
    auth.token = "";
    auth.user = null;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    auth.setJustLoggedIn(false);
    console.warn("[OAuth] token invalid/expired, cleared");
    return { hasToken: false, justLoggedIn: false };
  }

  const result = { hasToken: !!auth.token, justLoggedIn: storedJustLoggedIn };
  console.log("[OAuth] sync result:", result);
  return result;
}
