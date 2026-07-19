/**
 * BikeMaster Frontend — storage SQLite locale (WASM).
 *
 * Cache offline/seed per la SPA:
 * - Web/PWA: WASM SQLite (@sqlite.org/sqlite-wasm) su OPFS se COOP/COEP
 *   header sono presenti, altrimenti in-memory (sessione).
 * - Android/Tauri: stesso modulo WASM; su nativo si può sostituire con
 *   SQLite nativo senza cambiare l'API esposta.
 *
 * Il backend resta la fonte di verità: questo DB è una cache offline.
 */

// Layer di storage SQLite locale lato client.
//
// Strategia per piattaforma:
//   - Web/PWA  → WASM SQLite ufficiale (@sqlite.org/sqlite-wasm), persistente
//                su OPFS quando i COOP/COEP header sono presenti, altrimenti
//                in-memory (cache di sessione; il backend resta fonte di verità).
//   - Android/Tauri → stesso modulo WASM; su nativo si può sostituire con
//                SQLite nativo senza cambiare l'API esposta qui.
//
// Il backend resta la fonte di verità: questo DB è una cache offline/seed.

import type { UserApiKeys } from "../utils/userKeys";
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

// Inizializza il DB locale. Idempotente e sicuro nei test (no-op senza window).
export function initLocalDb(): Promise<boolean> {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    if (typeof window === "undefined") return false;
    try {
      const sqlite3InitModule = (
        await import("@sqlite.org/sqlite-wasm")
      ).default as unknown as (
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
        // Default VFS transient (in-memory) se OPFS non disponibile.
        db = new sqlite3.oo1.DB("/bikemaster.sqlite3", "c");
      }
      db.exec(
        `CREATE TABLE IF NOT EXISTS rides_cache (
           id INTEGER PRIMARY KEY,
           updated_at INTEGER NOT NULL,
           data TEXT NOT NULL
         );`,
      );
      db.exec(
        `CREATE TABLE IF NOT EXISTS user_api_keys (
           id INTEGER PRIMARY KEY CHECK (id = 1),
           data TEXT NOT NULL
         );`,
      );
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

// --- Cache delle uscite (ride) -------------------------------------------

export interface CachedRide {
  id: number;
  updated_at: number;
  data: unknown;
}

export function upsertRide(id: number, data: unknown): void {
  localRun(
    `INSERT INTO rides_cache (id, updated_at, data)
     VALUES (?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at,
                                     data = excluded.data`,
    [id, Date.now(), JSON.stringify(data)],
  );
}

export function getCachedRide(id: number): CachedRide | null {
  return localGet<CachedRide>("SELECT * FROM rides_cache WHERE id = ?", [id]);
}

export function getCachedRides(limit = 100): CachedRide[] {
  return localAll<CachedRide>(
    "SELECT * FROM rides_cache ORDER BY updated_at DESC LIMIT ?",
    [limit],
  );
}

export function deleteCachedRide(id: number): void {
  localRun("DELETE FROM rides_cache WHERE id = ?", [id]);
}

export function clearRideCache(): void {
  localRun("DELETE FROM rides_cache");
}

// --- Chiavi API per-utente (salvate localmente sul dispositivo) -----------

export function saveUserApiKeys(keys: UserApiKeys): void {
  localRun(
    `INSERT INTO user_api_keys (id, data) VALUES (1, ?)
     ON CONFLICT(id) DO UPDATE SET data = excluded.data`,
    [JSON.stringify(keys)],
  );
}

export function loadUserApiKeys(): UserApiKeys {
  const row = localGet<{ data: string }>(
    "SELECT data FROM user_api_keys WHERE id = 1",
  );
  if (!row || !row.data) return {};
  try {
    const parsed = JSON.parse(row.data) as UserApiKeys;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}
