import { useAuthStore } from "../stores/auth";

const API_BASE = "";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

function clearAuth() {
  localStorage.removeItem("bikemaster_token");
  localStorage.removeItem("bikemaster_user");
  localStorage.removeItem("bikemaster_just_logged_in");
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
  const token = localStorage.getItem("bikemaster_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Gateway statuses returned by Render while the free instance is asleep or
// restarting. The request never reached the app, so retrying is always safe.
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const MAX_RETRIES = 4;
const RETRY_BASE_DELAY_MS = 1500;

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
}

async function request<T>(options: RequestOptions): Promise<T> {
  const {
    path,
    method = "GET",
    body,
    headers = {},
    suppressAuthClear,
    ...rest
  } = options;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams;
  const init: RequestInit = {
    ...rest,
    method,
    headers: {
      ...(isForm || isUrlSearchParams
        ? {}
        : { "Content-Type": "application/json" }),
      ...authHeaders(),
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

  let resp: Response;
  for (let attempt = 0; ; attempt++) {
    try {
      resp = await fetch(path, init);
    } catch {
      if (idempotent && attempt < MAX_RETRIES) {
        notifyServerWaking();
        await sleep(RETRY_BASE_DELAY_MS * (attempt + 1));
        continue;
      }
      throw new ApiError(
        "Server non raggiungibile. Riprova tra qualche istante.",
        0,
      );
    }
    if (
      idempotent &&
      RETRYABLE_STATUS.has(resp.status) &&
      attempt < MAX_RETRIES
    ) {
      notifyServerWaking();
      await sleep(RETRY_BASE_DELAY_MS * (attempt + 1));
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
    !resp.headers.get("content-type")?.includes("application/json")
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
  options: RequestInit = {},
): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`;
  return request<T>({ ...options, path: url, method: "GET" });
}

export async function apiPost<T = ApiResponse>(
  path: string,
  body: unknown,
  options: RequestInit = {},
): Promise<T> {
  return request<T>({
    ...options,
    path: `${API_BASE}${path}`,
    method: "POST",
    body,
  });
}

export async function apiDelete<T = ApiResponse>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return request<T>({
    ...options,
    path: `${API_BASE}${path}`,
    method: "DELETE",
  });
}

export async function apiUpload<T = ApiResponse>(
  path: string,
  file: Blob | File,
  options: RequestInit = {},
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return request<T>({
    ...options,
    path: `${API_BASE}${path}`,
    method: "POST",
    body: form,
  });
}

export async function apiPut<T = ApiResponse>(
  path: string,
  body: unknown,
  options: RequestInit = {},
): Promise<T> {
  return request<T>({
    ...options,
    path: `${API_BASE}${path}`,
    method: "PUT",
    body,
  });
}
