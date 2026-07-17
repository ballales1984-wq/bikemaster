import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Athlete } from "../types/index";
import {
  apiPost,
  apiGet,
  ApiError,
  resetSessionExpiredNotification,
} from "../utils/api";
import { resolveApiBase } from "../utils/backend-config";
import {
  AUTH_TOKEN_KEY,
  AUTH_USER_KEY,
  AUTH_JUST_LOGGED_IN_KEY,
  AUTH_REFRESH_TOKEN_KEY,
  AUTH_LOGIN_ERROR_KEY,
} from "../utils/auth-storage";

const TOKEN_KEY = AUTH_TOKEN_KEY;
const USER_KEY = AUTH_USER_KEY;
const JUST_LOGGED_IN_KEY = AUTH_JUST_LOGGED_IN_KEY;
const REFRESH_TOKEN_KEY = AUTH_REFRESH_TOKEN_KEY;
const LOGIN_ERROR_KEY = AUTH_LOGIN_ERROR_KEY;

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
    typeof localStorage !== "undefined"
      ? localStorage.getItem(TOKEN_KEY) || ""
      : "",
  );

  const user = ref<Athlete | null>(
    (function () {
      try {
        if (typeof localStorage === "undefined") return null;
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    })(),
  );

  const justLoggedIn = ref(false);

  const refreshToken = ref(
    typeof localStorage !== "undefined"
      ? localStorage.getItem(REFRESH_TOKEN_KEY) || ""
      : "",
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

  // Thin fetch wrapper that injects the Bearer header and points at the
  // resolved backend base URL (defaults to the embedded Axum backend). Used to
  // call endpoints outside the JSON/Form helpers, e.g. the sync endpoints.
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
    const data = await apiGet<{ id: number; username: string; email?: string }>(
      "/api/v1/auth/me",
      {},
      { suppressAuthClear: true },
    );
    user.value = {
      id: typeof data.id === "number" ? data.id : user.value?.id ?? 0,
      username: data.username || user.value?.username || "",
      email: data.email ?? user.value?.email ?? null,
      is_admin: user.value?.is_admin ?? false,
      is_client: user.value?.is_client ?? false,
      tenant_id: user.value?.tenant_id ?? 0,
    };
    localStorage.setItem(USER_KEY, JSON.stringify(user.value));
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
      is_admin?: boolean;
    }>("/api/v1/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    token.value = data.access_token;
    if (data.refresh_token) {
      refreshToken.value = data.refresh_token;
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
    }
    const payload = parseJWTPayload(data.access_token);
    user.value = {
      id: typeof data.id === "number" ? data.id : 0,
      username: typeof data.username === "string" ? data.username : "",
      is_admin: !!data.is_admin,
      is_client: !!(payload as { is_client?: boolean } | null)?.is_client,
      tenant_id: typeof payload?.tenant_id === "number" ? payload.tenant_id : 0,
    };
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user.value));
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
      const currentToken = localStorage.getItem(TOKEN_KEY);
      if (currentToken) {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: { ...getAuthHeader() },
        }).catch(() => {});
      }
    } catch {}

    token.value = "";
    user.value = null;
    refreshToken.value = "";
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
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
    };
    localStorage.setItem(TOKEN_KEY, urlToken);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    token.value = urlToken;
    user.value = userData;
    refreshToken.value = "";
    localStorage.removeItem(AUTH_LOGIN_ERROR_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.setItem(JUST_LOGGED_IN_KEY, "true");
    justLoggedIn.value = true;
    resetSessionExpiredNotification();
  }

  function setOauthError(oauthError: string) {
    token.value = "";
    user.value = null;
    localStorage.setItem(AUTH_LOGIN_ERROR_KEY, oauthError);

    justLoggedIn.value = false;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(JUST_LOGGED_IN_KEY);
  }

  function setJustLoggedIn(value: boolean) {
    justLoggedIn.value = value;
    if (value) {
      localStorage.setItem(JUST_LOGGED_IN_KEY, "true");
    } else {
      localStorage.removeItem(JUST_LOGGED_IN_KEY);
    }
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
  };
});
