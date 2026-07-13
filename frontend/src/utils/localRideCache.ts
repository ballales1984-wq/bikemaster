import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Ride } from "../types/index";

const DB_NAME = "bikemaster-local";
const DB_VERSION = 1;
const STORE_RIDES = "rides";
const STORE_META = "meta";
const SUMMARY_KEY = "summary";

interface CachedRide {
  id: number;
  ride: Ride;
  cachedAt: number;
}

interface CachedSummary {
  summary: Record<string, unknown>;
  cachedAt: number;
}

interface BikeMasterLocalDB extends DBSchema {
  rides: {
    key: number;
    value: CachedRide;
  };
  meta: {
    key: string;
    value: unknown;
  };
}

let dbPromise: Promise<IDBPDatabase<BikeMasterLocalDB>> | null = null;

function getDB(): Promise<IDBPDatabase<BikeMasterLocalDB>> | null {
  if (typeof indexedDB === "undefined") return null;
  if (!dbPromise) {
    dbPromise = openDB<BikeMasterLocalDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_RIDES)) {
          db.createObjectStore(STORE_RIDES, { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains(STORE_META)) {
          db.createObjectStore(STORE_META);
        }
      },
    });
  }
  return dbPromise;
}

export async function cacheRides(rides: Ride[]): Promise<void> {
  const db = getDB();
  if (!db) return;
  try {
    const conn = await db;
    const tx = conn.transaction(STORE_RIDES, "readwrite");
    await Promise.all(
      rides
        .filter((r) => r && typeof r.id === "number")
        .map((r) => tx.store.put({ id: r.id, ride: r, cachedAt: Date.now() })),
    );
    await tx.done;
  } catch {
    /* storage unavailable: degrade silently */
  }
}

export async function getCachedRides(): Promise<Ride[] | null> {
  const db = getDB();
  if (!db) return null;
  try {
    const conn = await db;
    const cached = await conn.getAll(STORE_RIDES);
    if (!cached.length) return null;
    return cached.sort((a, b) => b.cachedAt - a.cachedAt).map((c) => c.ride);
  } catch {
    return null;
  }
}

export async function removeCachedRide(id: number): Promise<void> {
  const db = getDB();
  if (!db) return;
  try {
    const conn = await db;
    await conn.delete(STORE_RIDES, id);
  } catch {
    /* ignore */
  }
}

export async function cacheSummary(
  summary: Record<string, unknown>,
): Promise<void> {
  const db = getDB();
  if (!db) return;
  try {
    const conn = await db;
    await conn.put(
      STORE_META,
      { summary, cachedAt: Date.now() } as CachedSummary,
      SUMMARY_KEY,
    );
  } catch {
    /* ignore */
  }
}

export async function getCachedSummary(): Promise<Record<
  string,
  unknown
> | null> {
  const db = getDB();
  if (!db) return null;
  try {
    const conn = await db;
    const cached = (await conn.get(STORE_META, SUMMARY_KEY)) as
      CachedSummary | undefined;
    return cached?.summary ?? null;
  } catch {
    return null;
  }
}

export async function clearLocalRideCache(): Promise<void> {
  const db = getDB();
  if (!db) return;
  try {
    const conn = await db;
    await conn.clear(STORE_RIDES);
    await conn.delete(STORE_META, SUMMARY_KEY);
  } catch {
    /* ignore */
  }
}
