/**
 * Client HTTP verso il backend con gestione auth, retry e failover.
 *
 * `request` incapsula `fetch` aggiungendo header di autenticazione e delle
 * chiavi utente, timeout via `AbortController` e retry con backoff su errori di
 * rete e stati 502/503/504 (avviando il failover Render sull'ultimo tentativo).
 * Su 401 pulisce la sessione e notifica la scadenza. Espone `apiGet`, `apiPost`,
 * `apiPut`, `apiDelete`, `apiUpload` e la classe `ApiError`.
 */

import { useAuthStore } from "../stores/auth";
import {
  resolveApiBase,
  resolveFallbackBase,
  isFallbackEnabled,
} from "./backend-config";
import { getUserKeysHeaderValue } from "./userKeys";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

function clearAuth() {
  const auth = useAuthStore();
  auth.token = "";
  auth.user = null;
  auth.justLoggedIn = false;
}

let sessionExpiredNotified = false;

export function resetSessionExpiredNotification() {
  sessionExpiredNotified = false;
}

function extractApiErrorMessage(body: unknown): string {
  if (typeof body === "string") return body;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  if (Array.isArray(obj.detail)) {
    const messages = obj.detail
      .map((d: unknown) =>
        typeof d === "object" && d && "msg" in d
          ? String((d as { msg?: unknown }).msg)
          : String(d),
      )
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (typeof obj.message === "string") return obj.message;
  if (typeof obj.errors === "string") return obj.errors;
  if (Array.isArray(obj.errors)) {
    const messages = obj.errors.map((d: unknown) => String(d)).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (typeof obj.reason === "string") return obj.reason;
  return "Request failed";
}

function notifySessionExpired() {
  const toast = (
    window as unknown as {
      __toast?: { add?: (msg: string, type?: string, ms?: number) => void };
    }
  ).__toast;
  if (toast?.add && !sessionExpiredNotified) {
    toast.add("Sessione scaduta. Effettua di nuovo il login.", "error");
    sessionExpiredNotified = true;
  }
  const auth = useAuthStore();
  if (auth.isLoggedIn) {
    void auth.logout().catch(() => {});
  }
}

function authHeaders(): Record<string, string> {
  try {
    const auth = useAuthStore();
    return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
  } catch {
    return {};
  }
}

// Gateway statuses returned by Render while the free instance is asleep or
// restarting. The request never reached the app, so retrying is always safe.
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const MAX_RETRIES = 6;
const RETRY_BASE_DELAY_MS = 3000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let wakingNotified = false;

function notifyServerWaking() {
  const toast = (
    window as unknown as {
      __toast?: { add?: (msg: string, type?: string, ms?: number) => void };
    }
  ).__toast;
  if (toast?.add && !wakingNotified) {
    toast.add(
      "Il server si sta riavviando, attendo qualche secondo…",
      "info",
      8000,
    );
    wakingNotified = true;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  path: string;
  body?: unknown;
  // When true, a 401 response does NOT clear the stored session or trigger a
  // "session expired" logout. Used by the OAuth-return profile check, where a
  // transient 401 must never wipe a freshly established session.
  suppressAuthClear?: boolean;
  // Per-request timeout in ms. Enforced via AbortController so a stalled
  // backend (e.g. a cold free-tier instance) cannot hang the caller
  // indefinitely — critical for the OAuth-return navigation in the router
  // guard, which awaits this call before resolving the initial navigation.
  timeoutMs?: number;
  // When true, do not retry on network errors / 5xx gateway statuses.
  noRetry?: boolean;
}

export interface ApiCallOptions extends Omit<RequestInit, "body"> {
  suppressAuthClear?: boolean;
  timeoutMs?: number;
  noRetry?: boolean;
}

async function request<T>(options: RequestOptions): Promise<T> {
  const {
    path,
    method = "GET",
    body,
    headers = {},
    suppressAuthClear,
    timeoutMs,
    noRetry,
    ...rest
  } = options;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams;
  const userKeysHeader = getUserKeysHeaderValue();
  const init: RequestInit = {
    ...rest,
    method,
    headers: {
      ...(isForm || isUrlSearchParams
        ? {}
        : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(userKeysHeader ? { "X-User-Api-Keys": userKeysHeader } : {}),
      ...(headers as Record<string, string>),
    } as Record<string, string>,
    body: (isForm
      ? (body as BodyInit)
      : isUrlSearchParams
        ? (body as URLSearchParams).toString()
        : body !== undefined
          ? JSON.stringify(body)
          : undefined) as BodyInit | undefined,
  };

  const idempotent =
    method === "GET" || method === "HEAD" || method === "OPTIONS";
  const canRetry = !noRetry;

  // Base primario (relativo di default, altrimenti backend configurato).
  // On Vercel/device the app points to the backend on the PC; Render is the fallback.
  let currentBase = resolveApiBase();
  const fallbackBase = isFallbackEnabled() ? resolveFallbackBase() : "";
  const canUseFallback = !!fallbackBase && fallbackBase !== currentBase;
  const buildUrl = (base: string) => (base ? `${base}${path}` : path);

  let resp: Response;
  for (let attempt = 0; ; attempt++) {
    const isLastAttempt = attempt >= MAX_RETRIES;
    const url = buildUrl(currentBase);
    const controller =
      typeof timeoutMs === "number" &&
      timeoutMs > 0 &&
      typeof AbortController !== "undefined"
        ? new AbortController()
        : null;
    const timer =
      controller && typeof setTimeout !== "undefined"
        ? setTimeout(() => controller.abort(), timeoutMs)
        : undefined;
    try {
      resp = await fetch(
        url,
        controller ? { ...init, signal: controller.signal } : init,
      );
    } catch {
      if (timer) clearTimeout(timer);
      if (canRetry && !isLastAttempt) {
        notifyServerWaking();
        // Ultimo tentativo: riprova contro il failover (Render) se attivo.
        if (canUseFallback && attempt === MAX_RETRIES - 1) {
          currentBase = fallbackBase;
        }
        await sleep(RETRY_BASE_DELAY_MS * (attempt + 1) + Math.random() * 1000);
        continue;
      }
      throw new ApiError(
        "Server non raggiungibile. Riprova tra qualche istante.",
        0,
      );
    } finally {
      if (timer) clearTimeout(timer);
    }
    if (
      canRetry &&
      RETRYABLE_STATUS.has(resp.status) &&
      !isLastAttempt
    ) {
      notifyServerWaking();
      if (canUseFallback && attempt === MAX_RETRIES - 1) {
        currentBase = fallbackBase;
      }
      await sleep(RETRY_BASE_DELAY_MS * (attempt + 1) + Math.random() * 1000);
      continue;
    }
    break;
  }

  wakingNotified = false;
  if (!resp.ok) {
    if (resp.status === 401 && !suppressAuthClear) {
      clearAuth();
      notifySessionExpired();
      throw new ApiError("expired", 401);
    }
    const err = await resp.json().catch(() => ({}));
    const message =
      extractApiErrorMessage(err) || `${method} ${path}: ${resp.status}`;
    throw new ApiError(message, resp.status);
  }
  if (
    resp.status === 204 ||
    !resp.headers?.get("content-type")?.includes("application/json")
  ) {
    return {} as T;
  }
  return resp.json() as Promise<T>;
}

export interface ApiResponse {
  [key: string]: unknown;
}

export async function apiGet<T = ApiResponse>(
  path: string,
  params: Record<string, string> = {},
  options: ApiCallOptions = {},
): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const url = qs ? `${path}?${qs}` : path;
  return request<T>({ ...options, path: url, method: "GET" });
}

export async function apiPost<T = ApiResponse>(
  path: string,
  body: unknown,
  options: ApiCallOptions = {},
): Promise<T> {
  return request<T>({
    ...options,
    path,
    method: "POST",
    body,
  });
}

export async function apiDelete<T = ApiResponse>(
  path: string,
  options: ApiCallOptions = {},
): Promise<T> {
  return request<T>({
    ...options,
    path,
    method: "DELETE",
  });
}

export async function apiUpload<T = ApiResponse>(
  path: string,
  file: Blob | File,
  options: ApiCallOptions = {},
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return request<T>({
    ...options,
    path,
    method: "POST",
    body: form,
  });
}

export async function apiPut<T = ApiResponse>(
  path: string,
  body: unknown,
  options: ApiCallOptions = {},
): Promise<T> {
  return request<T>({
    ...options,
    path,
    method: "PUT",
    body,
  });
}
