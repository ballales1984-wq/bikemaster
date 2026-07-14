// Chiavi API per-utente, inserite dall'utente sul dispositivo e inviate al
// backend del PC tramite l'header `X-User-Api-Keys`. Il backend le usa per la
// singola richiesta al posto delle sue chiavi di server.

export interface UserApiKeys {
  groq?: string;
  google_maps?: string;
  serpapi?: string;
  weather?: string;
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
      for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
        const slot = (ENV_KEY_MAP[key.toUpperCase()] ||
          (key.toLowerCase() as keyof UserApiKeys)) as keyof UserApiKeys;
        if (typeof value === "string") assign(slot, value);
      }
      return result;
    }
  } catch {
    // Non è JSON: prova il formato KEY=VALUE (una per riga).
  }

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const name = trimmed.slice(0, eq).replace(/^(export|set)\s+/i, "").trim();
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
    const slot = ENV_KEY_MAP[name.toUpperCase()];
    if (slot) assign(slot, value);
  }
  return result;
}
