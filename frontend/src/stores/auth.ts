/**
 * Store di autenticazione.
 *
 * Gestisce token JWT, utente corrente, login/logout/register e refresh
 * token. Lo stato e' persistito in sessionStorage (non localStorage) cosi'
 * da sopravvivere a reload della pagina (es. aggiornamento service worker
 * durante il round-trip OAuth) senza mai scrivere il token su disco in modo
 * persistente. sessionStorage viene cancellato automaticamente alla chiusura
 * della scheda, riducendo la superficie di attacco XSS.
 */
import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import type { Athlete } from "../types/index";
import {
  apiPost,
  apiGet,
  ApiError,
  resetSessionExpiredNotification,
} from "../utils/api";
import { resolveApiBase } from "../utils/backend-config";
import { useUIStore } from "./ui";
import {
  AUTH_TOKEN_KEY,
  AUTH_USER_KEY,
  AUTH_JUST_LOGGED_IN_KEY,
  AUTH_REFRESH_TOKEN_KEY,
} from "../utils/auth-storage";

function parseBase64Url(base64Url: string): string {
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "==".slice(0, (4 - (base64.length % 4)) % 4);
  return decodeURIComponent(
    Array.from(atob(padded))
      .map((c) => `%${c.charCodeAt(0).toString(16).padStart(2, "0")}`)
      .join(""),
  );
}

function parseJWTPayload(tokenStr: string): Record<string, unknown> | null {
  try {
    const parts = tokenStr.split(".");
    if (parts.length < 2) return null;
    const decoded = parseBase64Url(parts[1]);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref(
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem(AUTH_TOKEN_KEY) || ""
      : "",
  );

  const user = ref<Athlete | null>(
    (function () {
      try {
        if (typeof sessionStorage === "undefined") return null;
        const raw = sessionStorage.getItem(AUTH_USER_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    })(),
  );

  const justLoggedIn = ref(
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem(AUTH_JUST_LOGGED_IN_KEY) === "true"
      : false,
  );

  const refreshToken = ref(
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem(AUTH_REFRESH_TOKEN_KEY) || ""
      : "",
  );

  watch(
    token,
    (val) => {
      try {
        if (val && typeof sessionStorage !== "undefined") {
          sessionStorage.setItem(AUTH_TOKEN_KEY, val);
        } else if (typeof sessionStorage !== "undefined") {
          sessionStorage.removeItem(AUTH_TOKEN_KEY);
        }
      } catch {
        /* ignore storage errors */
      }
    },
    { flush: "sync" },
  );

  watch(
    user,
    (val) => {
      try {
        if (val && typeof sessionStorage !== "undefined") {
          sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(val));
        } else if (typeof sessionStorage !== "undefined") {
          sessionStorage.removeItem(AUTH_USER_KEY);
        }
      } catch {
        /* ignore storage errors */
      }
    },
    { flush: "sync" },
  );

  watch(
    justLoggedIn,
    (val) => {
      try {
        if (val && typeof sessionStorage !== "undefined") {
          sessionStorage.setItem(AUTH_JUST_LOGGED_IN_KEY, "true");
        } else if (typeof sessionStorage !== "undefined") {
          sessionStorage.removeItem(AUTH_JUST_LOGGED_IN_KEY);
        }
      } catch {
        /* ignore storage errors */
      }
    },
    { flush: "sync" },
  );

  watch(
    refreshToken,
    (val) => {
      try {
        if (val && typeof sessionStorage !== "undefined") {
          sessionStorage.setItem(AUTH_REFRESH_TOKEN_KEY, val);
        } else if (typeof sessionStorage !== "undefined") {
          sessionStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
        }
      } catch {
        /* ignore storage errors */
      }
    },
    { flush: "sync" },
  );

  const isLoggedIn = computed(() => !!token.value && isTokenValid());
  const isAdmin = computed(() => user.value?.is_admin === true);
  const isClient = computed(() => user.value?.is_client === true);

  function isTokenValid(): boolean {
    if (!token.value) return false;
    const payload = parseJWTPayload(token.value);
    if (!payload) return false;
    const exp = payload.exp as number | undefined;
    if (!exp) return true;
    return Date.now() < exp * 1000;
  }

  function getAuthHeader(): Record<string, string> {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {};
  }

  async function apiFetch<T = unknown>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const base = resolveApiBase();
    const url = base ? `${base}${path}` : path;
    const resp = await fetch(url, {
      ...options,
      headers: {
        ...getAuthHeader(),
        ...(options.headers as Record<string, string> | undefined),
      },
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new ApiError(
        (err as { detail?: string }).detail || `Request failed: ${resp.status}`,
        resp.status,
      );
    }
    if (
      resp.status === 204 ||
      !resp.headers?.get("content-type")?.includes("application/json")
    ) {
      return {} as T;
    }
    return (await resp.json()) as T;
  }

  async function fetchMe(): Promise<void> {
    const data = await apiGet<{
      id: number;
      username: string;
      email?: string;
      active_athlete_id?: number;
    }>("/api/v1/auth/me", {}, { suppressAuthClear: true });
    user.value = {
      id: typeof data.id === "number" ? data.id : (user.value?.id ?? 0),
      username: data.username || user.value?.username || "",
      email: data.email ?? user.value?.email ?? null,
      is_admin: user.value?.is_admin ?? false,
      is_client: user.value?.is_client ?? false,
      tenant_id: user.value?.tenant_id ?? 0,
      active_athlete_id:
        typeof data.active_athlete_id === "number"
          ? data.active_athlete_id
          : (user.value?.active_athlete_id ?? data.id),
    };
  }

  async function login(username: string, password: string): Promise<void> {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const data = await apiPost<{
      access_token: string;
      refresh_token?: string;
      token_type?: string;
      username?: string;
      id?: number;
      athlete_id?: number;
      is_admin?: boolean;
    }>("/api/v1/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    token.value = data.access_token;
    if (data.refresh_token) {
      refreshToken.value = data.refresh_token;
    }
    const payload = parseJWTPayload(data.access_token);
    user.value = {
      id: typeof data.id === "number" ? data.id : 0,
      username: typeof data.username === "string" ? data.username : "",
      is_admin: !!data.is_admin,
      is_client: !!(payload as { is_client?: boolean } | null)?.is_client,
      tenant_id: typeof payload?.tenant_id === "number" ? payload.tenant_id : 0,
      active_athlete_id:
        typeof data.athlete_id === "number"
          ? data.athlete_id
          : typeof data.id === "number"
            ? data.id
            : 0,
    };
    resetSessionExpiredNotification();
  }

  async function register(
    username: string,
    password: string,
  ): Promise<unknown> {
    const data = await apiPost<{ detail?: unknown; message?: unknown }>(
      "/api/v1/auth/register",
      { username, password },
    );
    return data;
  }

  async function logout(): Promise<void> {
    try {
      if (token.value) {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: { ...getAuthHeader() },
        }).catch(() => {});
      }
    } catch {
      // ignore logout cleanup errors
    }

    token.value = "";
    user.value = null;
    refreshToken.value = "";
    justLoggedIn.value = false;

    const resetStoreMap: Record<string, string> = {
      "./athlete": "useAthleteStore",
      "./athleteState": "useAthleteStateStore",
      "./settings": "useSettingsStore",
      "./connections": "useConnectionsStore",
      "./apiKeys": "useApiKeysStore",
      "./rides": "useRidesStore",
      "./trackingStore": "useTrackingStore",
      "./ui": "useUIStore",
      "./notifications": "useNotificationStore",
      "./voiceCommands": "useVoiceCommandsStore",
      "./voiceSystem": "useVoiceSystemStore",
      "./performance": "usePerformanceStore",
      "./metabolism": "useMetabolismStore",
      "./ble": "useBleStore",
      "./healthConnect": "useHealthConnectStore",
      "./itinerary": "useItineraryStore",
      "./beck": "useBeckStore",
    };
    for (const [mod, exportName] of Object.entries(resetStoreMap)) {
      try {
        const mod_ = await import(mod);
        const store = mod_[exportName]();
        if (typeof store.$reset === "function") store.$reset();
      } catch {
        /* store may not export the expected function or may not implement $reset */
      }
    }

    try {
      const ui = useUIStore();
      ui.setOauthLoading(false);
    } catch {
      /* ui store may be disposed */
    }
    try {
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.removeItem("bikemaster_oauth_loading");
      }
    } catch {
      /* ignore */
    }
  }

  function setAuthFromUrl(urlToken: string, email: string, userId?: string) {
    const payload = parseJWTPayload(urlToken);
    const parsedId = userId
      ? parseInt(userId, 10)
      : typeof payload?.sub === "string"
        ? parseInt(payload.sub as string, 10)
        : 0;
    const userData = {
      id: isNaN(parsedId) ? 0 : parsedId,
      username: email || "",
      email,
      is_admin: false,
      is_client: false,
      tenant_id: typeof payload?.tenant_id === "number" ? payload.tenant_id : 0,
      active_athlete_id:
        typeof payload?.athlete_id === "number"
          ? payload.athlete_id
          : isNaN(parsedId)
            ? 0
            : parsedId,
    };
    token.value = urlToken;
    user.value = userData;
    refreshToken.value = "";
    justLoggedIn.value = true;
    resetSessionExpiredNotification();
  }

  async function fetchMyAthletes() {
    return apiFetch<{
      athletes: Array<{ id: number; name: string; email?: string | null }>;
    }>("/api/v1/athletes/mine");
  }

  async function createMyAthlete(data: {
    name: string;
    email?: string | null;
  }) {
    return apiFetch<{ athlete_id: number }>("/api/v1/athletes/mine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  async function deleteMyAthlete(athleteId: number) {
    return apiFetch<{ status: string }>(`/api/v1/athletes/mine/${athleteId}`, {
      method: "DELETE",
    });
  }

  async function switchAthlete(athleteId: number) {
    const data = await apiFetch<{
      access_token: string;
      refresh_token?: string;
      user_id: number;
      athlete_id: number;
    }>(`/api/v1/auth/switch-athlete/${athleteId}`, { method: "POST" });
    token.value = data.access_token;
    if (data.refresh_token) {
      refreshToken.value = data.refresh_token;
    }
    if (user.value) {
      user.value.active_athlete_id = data.athlete_id;
    }
    resetSessionExpiredNotification();
    return data;
  }

  async function fetchOAuthCredentials() {
    return apiFetch<{
      credentials: Array<{
        id: number;
        provider: string;
        client_id?: string;
        has_secret: boolean;
      }>;
    }>("/api/v1/connections/credentials");
  }

  async function setOAuthCredentials(
    provider: string,
    data: {
      client_id?: string;
      client_secret?: string;
      redirect_uri?: string;
      scope?: string;
    },
  ) {
    return apiFetch<{ status: string }>("/api/v1/connections/credentials", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, ...data }),
    });
  }

  async function deleteOAuthCredentials(provider: string) {
    return apiFetch<{ status: string }>(
      `/api/v1/connections/credentials/${provider}`,
      { method: "DELETE" },
    );
  }

  function setOauthError(_oauthError: string) {
    token.value = "";
    user.value = null;
    justLoggedIn.value = false;
  }

  function setJustLoggedIn(value: boolean) {
    justLoggedIn.value = value;
  }

  return {
    token,
    user,
    refreshToken,
    justLoggedIn,
    isLoggedIn,
    isAdmin,
    isClient,
    isTokenValid,
    getAuthHeader,
    apiFetch,
    fetchMe,
    login,
    register,
    logout,
    parseJWTPayload,
    setAuthFromUrl,
    setOauthError,
    setJustLoggedIn,
    fetchMyAthletes,
    createMyAthlete,
    deleteMyAthlete,
    switchAthlete,
    fetchOAuthCredentials,
    setOAuthCredentials,
    deleteOAuthCredentials,
  };
});
