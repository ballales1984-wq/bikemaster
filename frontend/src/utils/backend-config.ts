/**
 * Risoluzione configurabile a runtime dell'URL base del backend.
 *
 * Stabilisce il base *primario* (impostazione localStorage, `VITE_API_BASE`,
 * auto-detect Tauri, same-origin) e quello dell'hub cloud. `resolveFallbackBase`
 * espone il failover Render (usato solo su errore di rete/5xx se abilitato).
 * Esporta inoltre gli storage key, i getter/setter e `getBackendMode`
 * ("pc"|"render"|"local"|"tauri"|"hub") che descrive la modalità attiva.
 */

// Risolve l'URL base del backend in modo configurabile a runtime.
//
// Priorità del base *primario*:
//   1. Impostazione runtime (localStorage) — modificabile dalle Settings dell'app
//   2. Variabile di build VITE_API_BASE (es. su Vercel)
//   3. Auto-detect Tauri → localhost:8001 (backend Axum embedded)
//   4. ""  → stesso origine (default: in dev Vite fa proxy di /api a localhost:8000)
//
// Se il base primario è vuoto, le chiamate vanno allo stesso origine. Su Vercel
// (frontend statico, nessun backend allo stesso origine) va impostato un base
// esplicito: di solito l'URL del backend sul PC dell'utente.
//
// RENDER_FALLBACK_BASE è usato SOLO come failover: se il base primario è
// irraggiungibile (errore di rete o 502/503/504) e il failover è abilitato,
// l'ultimo tentativo viene riprovato contro Render.

export const API_BASE_STORAGE_KEY = "bikemaster_api_base";
export const API_FALLBACK_ENABLED_KEY = "bikemaster_api_fallback_enabled";
export const RENDER_FALLBACK_BASE = "https://bikemaster-api.onrender.com";
export const TAURI_EMBEDDED_BACKEND_BASE = "http://localhost:8001";
export const HUB_API_BASE_STORAGE_KEY = "bikemaster_hub_api_base";

function normalizeBase(base: string): string {
  const trimmed = base.trim();
  if (!trimmed) return "";
  return trimmed.replace(/\/+$/, "");
}

export function isTauri(): boolean {
  if (typeof window === "undefined") return false;
  const win = window as Window & {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
  };
  return !!win.__TAURI__ || !!win.__TAURI_INTERNALS__;
}

export function getStoredApiBase(): string {
  if (typeof localStorage === "undefined") return "";
  return localStorage.getItem(API_BASE_STORAGE_KEY) || "";
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

export function isFallbackEnabled(): boolean {
  if (typeof localStorage === "undefined") return false;
  return localStorage.getItem(API_FALLBACK_ENABLED_KEY) === "true";
}

export function setFallbackEnabled(enabled: boolean): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(API_FALLBACK_ENABLED_KEY, enabled ? "true" : "false");
}

export function resolveApiBase(): string {
  const stored = getStoredApiBase();
  if (stored) return stored;

  if (isTauri()) {
    return TAURI_EMBEDDED_BACKEND_BASE;
  }

  // Se la SPA è servita dallo stesso backend (es. http://localhost:8000
  // o http://localhost:8001), usa same-origin per evitare richieste
  // cross-origin (ngrok-free strip gli header CORS sulle risposte).
  if (typeof window !== "undefined" && typeof location !== "undefined") {
    const h = location.hostname;
    const p = location.port;
    if ((h === "localhost" || h === "127.0.0.1") && (p === "8000" || p === "8001")) {
      return "";
    }
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
// "hub" quando l'app gira su Vercel e parla con il backend cloud.
export type BackendMode = "pc" | "render" | "local" | "tauri" | "hub";

export function getBackendMode(): BackendMode {
  const base = resolveApiBase();
  if (!base) return isTauri() ? "local" : "local";
  if (isTauri() && base === TAURI_EMBEDDED_BACKEND_BASE) return "tauri";
  if (base.includes("onrender.com")) return "render";
  return "pc";
}
