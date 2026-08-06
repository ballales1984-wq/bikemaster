/**
 * Handles the client-side OAuth 2.0 flow.
 *
 * Processes the token present in the URL (query or fragment) after the provider
 * redirect, persists it in the Pinia store and removes it from the address
 * bar. To survive page reloads during the round-trip, it temporarily saves the
 * token in sessionStorage and recovers it if needed. The auth store itself
 * also mirrors state to sessionStorage so a mid-round-trip reload (service
 * worker update, bfcache restore) cannot drop a finalized login.
 *
 * Exports: hasPendingOAuth, processOAuthToken
 */

import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

// In-flight OAuth tokens are stashed here so a page reload that happens during
// the OAuth round-trip (a service-worker update, a bfcache restore, a transient
// error) cannot drop the login. The flag is cleared as soon as the token is
// consumed from the URL, so it only ever bridges the gap between "token arrived
// in the URL" and "auth state persisted to localStorage".
const OAUTH_PENDING_KEY = "bikemaster_oauth_pending";

type PendingOAuth = { token: string; email: string; userId: string };

function persistPendingOAuth(token: string, email: string, userId: string) {
  try {
    sessionStorage.setItem(
      OAUTH_PENDING_KEY,
      JSON.stringify({ token, email, userId } as PendingOAuth),
    );
  } catch {
    /* sessionStorage unavailable — login simply won't survive a reload */
  }
}

function clearPendingOAuth() {
  try {
    sessionStorage.removeItem(OAUTH_PENDING_KEY);
  } catch {
    /* ignore */
  }
}

function consumePendingOAuth(): PendingOAuth | null {
  try {
    const raw = sessionStorage.getItem(OAUTH_PENDING_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PendingOAuth;
    if (parsed && typeof parsed.token === "string" && parsed.token) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

function clearUrlToken() {
  if (window.history.replaceState) {
    window.history.replaceState({}, document.title, "/");
  }
}

export function hasPendingOAuth(): boolean {
  try {
    return sessionStorage.getItem(OAUTH_PENDING_KEY) !== null;
  } catch {
    return false;
  }
}

export function processOAuthToken(): boolean {
  const auth = useAuthStore();
  const ui = useUIStore();
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(
    window.location.hash.replace(/^#/, ""),
  );
  const urlToken = urlParams.get("token") || hashParams.get("token");
  const email = urlParams.get("email") || hashParams.get("email") || "";
  const userId = urlParams.get("user_id") || hashParams.get("user_id") || "";
  const oauthError =
    urlParams.get("oauth_error") || hashParams.get("oauth_error");

  if (oauthError) {
    clearPendingOAuth();
    auth.setOauthError(oauthError);
    ui.setOauthLoading(false);
    clearUrlToken();
    console.warn("[OAuth] URL error:", oauthError);
    return true;
  }

  // Fresh OAuth return: the token is in the URL fragment/query.
  if (urlToken) {
    // Stash before anything else, so a reload in the next few milliseconds
    // (e.g. a service-worker update) can still complete the login.
    persistPendingOAuth(urlToken, email, userId);
    if (auth.isLoggedIn && auth.isTokenValid()) {
      clearPendingOAuth();
      ui.setOauthLoading(false);
      clearUrlToken();
      if (import.meta.env.DEV)
        console.log("[OAuth] already logged in, skipping");
      return false;
    }
    auth.setAuthFromUrl(urlToken, email, userId);
    clearPendingOAuth();
    ui.setOauthLoading(false);
    clearUrlToken();
    if (import.meta.env.DEV)
      console.log("[OAuth] token consumed from URL, profile:", email);
    return true;
  }

  // No token in the URL: recover one stashed by a previous load that was
  // interrupted by a reload during the OAuth round-trip.
  const pending = consumePendingOAuth();
  if (pending) {
    auth.setAuthFromUrl(pending.token, pending.email, pending.userId);
    clearPendingOAuth();
    ui.setOauthLoading(false);
    if (import.meta.env.DEV)
      console.log("[OAuth] token recovered from sessionStorage");
    return true;
  }

  // Safety: if there is no OAuth token/error to process, never leave the app
  // stuck behind the loading overlay (e.g. a backend redirect that dropped
  // the param, or a transient round-trip error).
  if (import.meta.env.DEV)
    console.log("[OAuth] no token found in URL or sessionStorage");
  ui.setOauthLoading(false);
  return false;
}
