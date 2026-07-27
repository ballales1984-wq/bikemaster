/**
 * Store delle notifiche e preferenze.
 *
 * Gestisce la lista di notifiche, le preferenze utente (pausa,
 * canali) e il push verso i toast dell'app.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useToast } from "../composables/useToast";
import {
  DEFAULT_NOTIFICATION_PREFERENCES,
  fetchNotifications,
  updateNotificationPreferences,
} from "../services/notifications";
import type {
  Notification,
  NotificationPreferences,
} from "../types/notifications";

const PREFS_KEY = "bikemaster_notification_prefs";

function loadPrefs(): NotificationPreferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) return { ...DEFAULT_NOTIFICATION_PREFERENCES, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_NOTIFICATION_PREFERENCES };
}

export const useNotificationStore = defineStore("notifications", () => {
  const notifications = ref<Notification[]>([]);
  const preferences = ref<NotificationPreferences>(loadPrefs());
  const loading = ref(false);
  const lastError = ref<string | null>(null);

  const toasts = useToast();

  const appNotifications = computed(() =>
    notifications.value.filter((n) => n.channel === "app"),
  );
  const voiceNotifications = computed(() =>
    notifications.value.filter((n) => n.channel === "voice"),
  );

  function persistPrefs() {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(preferences.value));
    } catch {
      /* ignore */
    }
  }

  async function refresh(params: Record<string, unknown> = {}) {
    loading.value = true;
    lastError.value = null;
    try {
      const res = await fetchNotifications(params as never);
      notifications.value = res.notifications;
      pushToasts(res.notifications);
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : "Errore notifiche";
    } finally {
      loading.value = false;
    }
  }

  function pushToasts(list: Notification[]) {
    for (const n of list) {
      if (n.channel === "app") {
        toasts.add(n.title ? `${n.title}: ${n.message}` : n.message, "info");
      }
    }
  }

  async function savePreferences(prefs: Partial<NotificationPreferences>) {
    preferences.value = { ...preferences.value, ...prefs };
    persistPrefs();
    try {
      await updateNotificationPreferences(preferences.value);
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : "Errore preferenze";
    }
  }

  function setPaused(paused: boolean) {
    preferences.value.paused = paused;
    persistPrefs();
  }

  function clear() {
    notifications.value = [];
  }

  return {
    notifications,
    preferences,
    loading,
    lastError,
    appNotifications,
    voiceNotifications,
    refresh,
    savePreferences,
    setPaused,
    clear,
  };
});
