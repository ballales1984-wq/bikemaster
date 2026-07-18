/**
 * Store delle chiavi API per-utente.
 *
 * Inserite dall'utente, persistite in SQLite locale e propagate
 * al backend via header ad ogni richiesta.
 */
import { defineStore } from "pinia";
import { ref } from "vue";
import {
  type UserApiKeys,
  setUserKeys,
} from "../utils/userKeys";
import {
  initLocalDb,
  isLocalDbReady,
  saveUserApiKeys,
  loadUserApiKeys,
} from "../db/localDb";

// Chiavi API per-utente: inserite dall'utente, persistite in SQLite locale sul
// dispositivo, inviate al backend via header ad ogni richiesta.
export const useApiKeysStore = defineStore("apiKeys", () => {
  const keys = ref<UserApiKeys>({});
  const loaded = ref(false);

  async function load(): Promise<void> {
    await initLocalDb();
    if (isLocalDbReady()) {
      keys.value = loadUserApiKeys();
    }
    setUserKeys(keys.value);
    loaded.value = true;
  }

  function setKey(name: keyof UserApiKeys, value: string): void {
    keys.value = { ...keys.value, [name]: value };
    setUserKeys(keys.value);
    if (isLocalDbReady()) saveUserApiKeys(keys.value);
  }

  function clearKey(name: keyof UserApiKeys): void {
    const next = { ...keys.value };
    delete next[name];
    keys.value = next;
    setUserKeys(keys.value);
    if (isLocalDbReady()) saveUserApiKeys(keys.value);
  }

  function save(): void {
    setUserKeys(keys.value);
    if (isLocalDbReady()) saveUserApiKeys(keys.value);
  }

  return { keys, loaded, load, setKey, clearKey, save };
});
