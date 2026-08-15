/**
 * Runtime-configurable resolution of the backend base URL.
 *
 * Establishes the primary base (localStorage setting, `VITE_API_BASE`,
 * auto-detect Tauri, same-origin) and the cloud hub base. `resolveFallbackBase`
 * exposes the Render fallback (used only on network error/5xx if enabled).
 * Also exports storage keys, getters/setters and `getBackendMode`
 * ("pc"|"render"|"local"|"tauri"|"mobile"|"hub") describing the active mode.
 */

// Resolves the backend base URL in a configurable way at runtime.
//
// Priority of the primary base:
//   1. Runtime setting (localStorage) — modifiable from the app Settings
//   2. Build variable VITE_API_BASE (e.g. on Vercel)
//   3. Auto-detect Tauri → localhost:8001 (full FastAPI backend)
//   4. "" → same origin (default: in dev Vite proxies /api to localhost:8001)
//
// If the primary base is empty, calls go to the same origin. On Vercel
// (static frontend, no backend at same origin) an explicit base must be set:
// usually the URL of the backend on the user's PC.
//
// RENDER_FALLBACK_BASE is used ONLY as fallback: if the primary base is
// unreachable (network error or 502/503/504) and fallback is enabled,
// the last attempt is retried against Render.

export const API_BASE_STORAGE_KEY = "bikemaster_api_base";
export const API_FALLBACK_ENABLED_KEY = "bikemaster_api_fallback_enabled";
export const RENDER_FALLBACK_BASE = "https://bikemaster.onrender.com";
export const TAURI_EMBEDDED_BACKEND_BASE = "http://localhost:8001";
export const HUB_API_BASE_STORAGE_KEY = "bikemaster_hub_api_base";
export const MOBILE_API_BASE_STORAGE_KEY = "bikemaster_mobile_api_base";

function normalizeBase(base: string): string {
  const trimmed = base.trim();
  if (!trimmed) return "";
  const normalized = trimmed.replace(/\/+$/, "");
  const schemeCount = (normalized.match(/https?:\/\//gi) || []).length;
  if (schemeCount > 1) {
    return "";
  }
  const idx = normalized.indexOf("://");
  if (idx >= 0) {
    const after = normalized.slice(idx + 3);
    if (
      after.includes("://") ||
      after.includes("http//") ||
      after.includes("https//")
    ) {
      return "";
    }
  }
  return normalized;
}

export function isTauri(): boolean {
  if (typeof window === "undefined") return false;
  const win = window as Window & {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
  };
  return !!win.__TAURI__ || !!win.__TAURI_INTERNALS__;
}

export function isCapacitor(): boolean {
  if (typeof window === "undefined") return false;
  const win = window as Window & {
    Capacitor?: { isNative?: boolean; isNativePlatform?: boolean };
  };
  if (!win.Capacitor) return false;
  return Boolean(win.Capacitor.isNative || win.Capacitor.isNativePlatform);
}

export function getStoredApiBase(): string {
  if (typeof localStorage === "undefined") return "";
  return normalizeBase(localStorage.getItem(API_BASE_STORAGE_KEY) || "");
}

export function getStoredHubApiBase(): string {
  if (typeof localStorage === "undefined") return "";
  return localStorage.getItem(HUB_API_BASE_STORAGE_KEY) || "";
}

export function setStoredApiBase(base: string): void {
  if (typeof localStorage === "undefined") return;
  const normalized = normalizeBase(base);
  if (normalized) {
    localStorage.setItem(API_BASE_STORAGE_KEY, normalized);
  } else {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
  }
}

export function setStoredHubApiBase(base: string): void {
  if (typeof localStorage === "undefined") return;
  const normalized = normalizeBase(base);
  if (normalized) {
    localStorage.setItem(HUB_API_BASE_STORAGE_KEY, normalized);
  } else {
    localStorage.removeItem(HUB_API_BASE_STORAGE_KEY);
  }
}

export function getStoredMobileApiBase(): string {
  if (typeof localStorage === "undefined") return "";
  return localStorage.getItem(MOBILE_API_BASE_STORAGE_KEY) || "";
}

export function setStoredMobileApiBase(base: string): void {
  if (typeof localStorage === "undefined") return;
  const normalized = normalizeBase(base);
  if (normalized) {
    localStorage.setItem(MOBILE_API_BASE_STORAGE_KEY, normalized);
  } else {
    localStorage.removeItem(MOBILE_API_BASE_STORAGE_KEY);
  }
}

export function isFallbackEnabled(): boolean {
  if (typeof localStorage === "undefined") return false;
  return localStorage.getItem(API_FALLBACK_ENABLED_KEY) === "true";
}

export function setFallbackEnabled(enabled: boolean): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(API_FALLBACK_ENABLED_KEY, enabled ? "true" : "false");
}

export function resolveApiBase(): string {
  if (isCapacitor()) {
    const stored = getStoredMobileApiBase();
    if (stored) return stored;
    return resolveMobileApiBase();
  }

  if (typeof window !== "undefined" && typeof location !== "undefined") {
    const h = location.hostname.toLowerCase();
    if (h === "localhost" || h === "127.0.0.1") {
      const p = location.port;
      if (p === "8001") return "";
    }
    if (h.endsWith(".ngrok-free.dev") || h.endsWith(".onrender.com")) {
      return "";
    }
  }

  const stored = getStoredApiBase();
  if (stored) return stored;

  if (isTauri()) {
    return TAURI_EMBEDDED_BACKEND_BASE;
  }

  const envBase =
    typeof import.meta !== "undefined"
      ? // @ts-ignore Vite injects VITE_* env vars at build time
        import.meta.env.VITE_API_BASE
      : undefined;
  if (envBase && typeof envBase === "string" && envBase.trim()) {
    return normalizeBase(envBase);
  }

  return "";
}

export function resolveMobileApiBase(): string {
  if (typeof window === "undefined") return "";

  const stored = getStoredMobileApiBase();
  if (stored) return stored;

  return "";
}

export function resolveHubApiBase(): string {
  const stored = getStoredHubApiBase();
  if (stored) return stored;

  const envHub =
    typeof import.meta !== "undefined"
      ? // @ts-ignore Vite injects VITE_* env vars at build time
        import.meta.env.VITE_HUB_API_BASE
      : undefined;
  if (envHub && typeof envHub === "string" && envHub.trim()) {
    return normalizeBase(envHub);
  }

  return "";
}

export function resolveFallbackBase(): string {
  return RENDER_FALLBACK_BASE;
}

// "pc" quando l'utente punta al proprio backend, "render" per il fallback,
// "local" per same-origin (dev), "tauri" per backend embedded Tauri,
// "mobile" per Capacitor Android che parla con il backend sulla rete locale,
// "hub" quando l'app gira su Vercel e parla con il backend cloud.
export type BackendMode =
  "pc" | "render" | "local" | "tauri" | "mobile" | "hub";

export function getBackendMode(): BackendMode {
  if (isCapacitor()) return "mobile";

  const base = resolveApiBase();
  if (!base) return isTauri() ? "local" : "local";
  if (isTauri() && base === TAURI_EMBEDDED_BACKEND_BASE) return "tauri";
  if (base.includes("onrender.com")) return "render";
  return "pc";
}
