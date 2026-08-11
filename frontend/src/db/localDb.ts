/**
 * BikeMaster Frontend — local SQLite storage (WASM).
 *
 * Offline/seed cache for the SPA:
 * - Web/PWA: WASM SQLite (@sqlite.org/sqlite-wasm) on OPFS if COOP/COEP
 *   headers are present, otherwise in-memory (session).
 * - Android/Tauri: same WASM module; on native it can be replaced with
 *   native SQLite without changing the exposed API.
 *
 * The backend remains the source of truth: this DB is an offline cache.
 */

// Local client-side SQLite storage layer.
//
// Per-platform strategy:
//   - Web/PWA  → official WASM SQLite (@sqlite.org/sqlite-wasm), persistent
//                on OPFS when the COOP/COEP headers are present, otherwise
//                in-memory (session cache; the backend remains the source of truth).
//   - Android/Tauri → same WASM module; on native it can be replaced with
//                native SQLite without changing the API exposed here.
//
// The backend remains the source of truth: this DB is an offline/seed cache.

import type {
  Database,
  Sqlite3Static,
  BindableValue,
} from "@sqlite.org/sqlite-wasm";

let sqlite3: Sqlite3Static | null = null;
let db: Database | null = null;
let initPromise: Promise<boolean> | null = null;

export function isLocalDbReady(): boolean {
  return db !== null;
}

// Initialize the local DB. Idempotent and safe in tests (no-op without window).
const RIDES_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

export function initLocalDb(): Promise<boolean> {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    if (typeof window === "undefined") return false;
    try {
      const sqlite3InitModule = (await import("@sqlite.org/sqlite-wasm"))
        .default as unknown as (
        config?: Record<string, unknown>,
      ) => Promise<Sqlite3Static>;
      const sqlite3Assets = `${import.meta.env.BASE_URL}sqlite3`;
      sqlite3 = await sqlite3InitModule({
        locateFile: (file: string) => `${sqlite3Assets}/${file}`,
      });
      const hasOpfs =
        !!sqlite3.oo1.OpfsDb && typeof SharedArrayBuffer !== "undefined";
      if (hasOpfs) {
        db = new sqlite3.oo1.OpfsDb("/bikemaster.sqlite3", {
          proxyUri: `${sqlite3Assets}/sqlite3-opfs-async-proxy.js`,
        } as any);
      } else {
        db = new sqlite3.oo1.DB("/bikemaster.sqlite3", "c");
      }
      db.exec(
        `CREATE TABLE IF NOT EXISTS rides_cache (
           id INTEGER PRIMARY KEY,
           updated_at INTEGER NOT NULL,
           expires_at INTEGER NOT NULL DEFAULT 0,
           data TEXT NOT NULL
         );`,
      );
      try {
        db.exec(
          `ALTER TABLE rides_cache ADD COLUMN expires_at INTEGER NOT NULL DEFAULT 0`,
        );
        (db as any).exec(
          `UPDATE rides_cache SET expires_at = ? WHERE expires_at = 0`,
          [Date.now() + RIDES_CACHE_TTL_MS],
        );
      } catch {
        // column already exists
      }
      return true;
    } catch (err) {
      console.warn("[localDb] SQLite locale non disponibile:", err);
      db = null;
      return false;
    }
  })();
  return initPromise;
}

function ensureDb(): Database {
  if (!db) {
    throw new Error("Local DB non inizializzato. Chiama initLocalDb() prima.");
  }
  return db;
}

export function localRun(sql: string, params: BindableValue[] = []): void {
  ensureDb().exec({ sql, bind: params });
}

export function localAll<T = Record<string, unknown>>(
  sql: string,
  params: BindableValue[] = [],
): T[] {
  const rows: unknown[] = [];
  ensureDb().exec({
    sql,
    bind: params,
    rowMode: "object",
    resultRows: rows as never,
  });
  return rows as T[];
}

export function localGet<T = Record<string, unknown>>(
  sql: string,
  params: BindableValue[] = [],
): T | null {
  const rows = localAll<T>(sql, params);
  return rows.length ? rows[0] : null;
}

// --- Ride cache (ride) -------------------------------------------

export interface CachedRide {
  id: number;
  updated_at: number;
  data: unknown;
}

export function upsertRide(id: number, data: unknown): void {
  const now = Date.now();
  localRun(
    `INSERT INTO rides_cache (id, updated_at, expires_at, data)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at,
                                     expires_at = excluded.expires_at,
                                     data = excluded.data`,
    [id, now, now + RIDES_CACHE_TTL_MS, JSON.stringify(data)],
  );
}

function parseCachedData(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getCachedRide(id: number): CachedRide | null {
  const row = localGet<{ id: number; updated_at: number; data: string }>(
    "SELECT id, updated_at, data FROM rides_cache WHERE id = ? AND expires_at > ?",
    [id, Date.now()],
  );
  if (!row) return null;
  return {
    id: row.id,
    updated_at: row.updated_at,
    data: parseCachedData(row.data),
  };
}

export function getCachedRides(limit = 100): CachedRide[] {
  const rows = localAll<{ id: number; updated_at: number; data: string }>(
    "SELECT id, updated_at, data FROM rides_cache WHERE expires_at > ? ORDER BY updated_at DESC LIMIT ?",
    [Date.now(), limit],
  );
  return rows.map((row) => ({
    id: row.id,
    updated_at: row.updated_at,
    data: parseCachedData(row.data),
  }));
}

export function deleteCachedRide(id: number): void {
  localRun("DELETE FROM rides_cache WHERE id = ?", [id]);
}

export function clearRideCache(): void {
  localRun("DELETE FROM rides_cache");
}
