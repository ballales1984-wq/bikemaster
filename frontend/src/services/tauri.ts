/**
 * Bridge between the frontend and the embedded Rust/Tauri backend (Axum).
 *
 * In a Tauri environment it uses direct IPC commands to obtain app info,
 * the local DB path and the data directory. In a web/PWA environment
 * all REST calls are routed through the configured base API.
 *
 * Exports: getTauriAppInfo, getTauriDbPath, getAppDataDir,
 *          resetLocalData, getEffectiveApiBase, getEffectiveBackendMode,
 *          checkBackendHealth
 */

import {
  resolveApiBase,
  getBackendMode,
  isTauri,
} from "../utils/backend-config";

async function loadTauriCore(): Promise<Record<string, unknown>> {
  try {
    const core = await import("@tauri-apps/api/core");
    return core as Record<string, unknown>;
  } catch {
    const tauri = await import("@tauri-apps/api");
    return tauri as Record<string, unknown>;
  }
}

async function loadTauriPath(): Promise<Record<string, unknown>> {
  try {
    const path = await import("@tauri-apps/api/path");
    return path as Record<string, unknown>;
  } catch {
    const tauri = await import("@tauri-apps/api");
    return tauri as Record<string, unknown>;
  }
}

export interface AppInfo {
  name: string;
  version: string;
  platform: string;
  arch: string;
}

async function tauriInvoke<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  const mod = await loadTauriCore();

  const fn = mod.invoke as ((..._a: unknown[]) => Promise<T>) | undefined;
  if (!fn) throw new Error("invoke not available");
  return fn(cmd, args);
}

async function tauriGetAppPath(dir: string): Promise<string> {
  const mod = await loadTauriPath();

  const fn = mod.getAppPath as
    ((..._a: unknown[]) => Promise<string>) | undefined;
  if (!fn) throw new Error("getAppPath not available");
  return fn(dir);
}

export async function getTauriAppInfo(): Promise<AppInfo | null> {
  if (!isTauri()) return null;
  try {
    return await tauriInvoke<AppInfo>("get_app_info");
  } catch {
    return null;
  }
}

export async function getTauriDbPath(): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    return await tauriInvoke<string>("get_db_path");
  } catch {
    return null;
  }
}

export async function getAppDataDir(): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    return await tauriGetAppPath("appData");
  } catch {
    return null;
  }
}

export async function resetLocalData(): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    return await tauriInvoke<string>("reset_local_data");
  } catch (e) {
    console.warn("[tauri] reset_local_data failed:", e);
    return null;
  }
}

// Returns the correct base URL for API calls in the current context.
export function getEffectiveApiBase(): string {
  return resolveApiBase();
}

export function getEffectiveBackendMode(): string {
  return getBackendMode();
}

// Health check of the embedded backend. Uses the Axum /health endpoint.
export async function checkBackendHealth(timeoutMs = 3000): Promise<boolean> {
  const base = getEffectiveApiBase();
  if (!base) return false;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const resp = await fetch(`${base}/health`, {
      method: "GET",
      signal: controller.signal,
    });

    clearTimeout(timer);
    return resp.ok;
  } catch {
    return false;
  }
}
