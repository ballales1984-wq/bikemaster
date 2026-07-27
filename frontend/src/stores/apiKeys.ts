/**
 * Per-user API keys store.
 *
 * Entered by the user, persisted in local SQLite and propagated
 * to the backend via header on every request.
 */
import { defineStore } from "pinia";
import { ref } from "vue";
import { type UserApiKeys, setUserKeys } from "../utils/userKeys";
import {
  initLocalDb,
  isLocalDbReady,
  saveUserApiKeys,
  loadUserApiKeys,
} from "../db/localDb";

// Per-user API keys: entered by the user, persisted in local SQLite on the
// device, sent to the backend via header on every request.
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
