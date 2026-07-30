/**
 * Per-user API keys store.
 *
 * API keys are held in memory only for the session duration and are lost
 * when the page is reloaded. This addresses the security concern of keys
 * being exposed on disk.
 */
import { defineStore } from "pinia";
import { ref } from "vue";
import { type UserApiKeys, setUserKeys } from "../utils/userKeys";

export const useApiKeysStore = defineStore("apiKeys", () => {
  const keys = ref<UserApiKeys>({});
  const loaded = ref(false);

  function load(): void {
    setUserKeys(keys.value);
    loaded.value = true;
  }

  function setKey(name: keyof UserApiKeys, value: string): void {
    keys.value = { ...keys.value, [name]: value };
    setUserKeys(keys.value);
  }

  function clearKey(name: keyof UserApiKeys): void {
    const next = { ...keys.value };
    delete next[name];
    keys.value = next;
    setUserKeys(keys.value);
  }

  function save(): void {
    setUserKeys(keys.value);
  }

  return { keys, loaded, load, setKey, clearKey, save };
});
