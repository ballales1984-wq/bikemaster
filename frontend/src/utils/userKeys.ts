/**
 * Gestione delle chiavi API per-utente immesse sul dispositivo.
 *
 * Esporta l'interfaccia `UserApiKeys` (slot per servizi interni ed esterni),
 * gli helper `setUserKeys`/`getUserKeys` per lo stato in memoria e
 * `getUserKeysHeaderValue` che produce l'header `X-User-Api-Keys` (JSON dei soli
 * slot non vuoti, oppure `null`). `parseBulkKeys` converte un blocco incollato
 * (JSON o righe `KEY=VALUE`, con nomi stile-environment) nelle chiavi utente.
 */

// Chiavi API per-utente, inserite dall'utente sul dispositivo e inviate al
// backend del PC tramite l'header `X-User-Api-Keys`. Il backend le usa per la
// singola richiesta al posto delle sue chiavi di server.

export interface UserApiKeys {
  // Servizi interni/app
  groq?: string;
  google_maps?: string;
  serpapi?: string;
  weather?: string;

  // Servizi esterni - API keys personali dell'utente
  strava_client_id?: string;
  strava_client_secret?: string;
  garmin_api_key?: string;
  wahoo_client_id?: string;
  wahoo_client_secret?: string;
  google_fit_client_id?: string;
  google_fit_client_secret?: string;
  google_health_client_id?: string;
  google_health_client_secret?: string;
}

// Stato corrente in memoria, aggiornato dallo store Pinia e letto da api.ts.
let currentKeys: UserApiKeys = {};

export function setUserKeys(keys: UserApiKeys): void {
  currentKeys = keys || {};
}

export function getUserKeys(): UserApiKeys {
  return currentKeys;
}

// Valore dell'header: solo gli slot non vuoti, come JSON. null se vuoto.
export function getUserKeysHeaderValue(): string | null {
  const filtered: Record<string, string> = {};
  for (const [k, v] of Object.entries(currentKeys)) {
    if (typeof v === "string" && v.trim()) filtered[k] = v.trim();
  }
  if (Object.keys(filtered).length === 0) return null;
  return JSON.stringify(filtered);
}

// Mappa nomi variabile stile-environment → slot interni.
const ENV_KEY_MAP: Record<string, keyof UserApiKeys> = {
  GROQ_API_KEY: "groq",
  GOOGLE_MAPS_API_KEY: "google_maps",
  SERPAPI_API_KEY: "serpapi",
  WEATHER_API_KEY: "weather",
  OPENWEATHER_API_KEY: "weather",
  STRAVA_CLIENT_ID: "strava_client_id",
  STRAVA_CLIENT_SECRET: "strava_client_secret",
  GARMIN_API_KEY: "garmin_api_key",
  WAHOO_CLIENT_ID: "wahoo_client_id",
  WAHOO_CLIENT_SECRET: "wahoo_client_secret",
  GOOGLE_FIT_CLIENT_ID: "google_fit_client_id",
  GOOGLE_FIT_CLIENT_SECRET: "google_fit_client_secret",
  GOOGLE_HEALTH_CLIENT_ID: "google_health_client_id",
  GOOGLE_HEALTH_CLIENT_SECRET: "google_health_client_secret",
};

// Parsa un blocco incollato (JSON o righe KEY=VALUE) nelle chiavi per-utente.
// Accetta sia gli slot interni (groq, google_maps, ...) sia i nomi env.
export function parseBulkKeys(text: string): UserApiKeys {
  const result: UserApiKeys = {};
  const raw = (text || "").trim();
  if (!raw) return result;

  const assign = (slot: keyof UserApiKeys, value: string) => {
    const v = (value || "").trim();
    if (v) result[slot] = v;
  };

  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      for (const [key, value] of Object.entries(
        parsed as Record<string, unknown>,
      )) {
        const slot = (ENV_KEY_MAP[key.toUpperCase()] ||
          (key.toLowerCase() as keyof UserApiKeys)) as keyof UserApiKeys;
        if (typeof value === "string") assign(slot, value);
      }
      return result;
    }
  } catch {
    // Not JSON: try KEY=VALUE format (one per line).
  }

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const name = trimmed
      .slice(0, eq)
      .replace(/^(export|set)\s+/i, "")
      .trim();
    const value = trimmed
      .slice(eq + 1)
      .trim()
      .replace(/^["']|["']$/g, "");
    const slot = ENV_KEY_MAP[name.toUpperCase()];
    if (slot) assign(slot, value);
  }
  return result;
}

