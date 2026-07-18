/**
 * Ponte tra il frontend e il backend Rust/Tauri embedded (Axum).
 *
 * In ambiente Tauri usa comandi IPC diretti per ottenere info sull'app,
 * il percorso del DB locale e la directory dei dati. In ambiente web/PWA
 * tutte le chiamate REST sono instradate tramite l'API base configurata.
 *
 * Esporta: getTauriAppInfo, getTauriDbPath, getAppDataDir,
 *          resetLocalData, getEffectiveApiBase, getEffectiveBackendMode,
 *          checkBackendHealth
 */

import { resolveApiBase, getBackendMode, isTauri } from "../utils/backend-config";

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
  // eslint-disable-next-line no-unused-vars
  const fn = mod.invoke as ((..._a: unknown[]) => Promise<T>) | undefined;
  if (!fn) throw new Error("invoke not available");
  return fn(cmd, args);
}

async function tauriGetAppPath(dir: string): Promise<string> {
  const mod = await loadTauriPath();
  // eslint-disable-next-line no-unused-vars
  const fn = mod.getAppPath as ((..._a: unknown[]) => Promise<string>) | undefined;
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

// Restituisce l'URL base corretto per le chiamate API nel contesto corrente.
export function getEffectiveApiBase(): string {
  return resolveApiBase();
}

export function getEffectiveBackendMode(): string {
  return getBackendMode();
}

// Health check del backend embedded. Usa l'endpoint /health di Axum.
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
