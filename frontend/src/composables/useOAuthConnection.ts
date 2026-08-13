import { ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useToast } from "./useToast";
import { isTauri, TAURI_EMBEDDED_BACKEND_BASE, resolveApiBase } from "../utils/backend-config";

export interface OAuthProviderConfig {
  provider: string;
  authEndpoint: string;
  callbackEndpoint: string;
  popupName: string;
  popupWidth: number;
  popupHeight: number;
  successEventType: string;
  errorEventType: string;
  extractCallbackBody: (
    eventData: Record<string, unknown>,
    authResponse: Record<string, unknown>,
  ) => Record<string, unknown>;
  handleCustomError?: (detail: string, status: number) => string;
  onConnected: (result: Record<string, unknown> | null) => string;
}

export const oauthProviders: Record<string, OAuthProviderConfig> = {
  strava: {
    provider: "strava",
    authEndpoint: "/api/v1/import/strava/auth",
    callbackEndpoint: "/api/v1/import/strava/callback",
    popupName: "strava-auth",
    popupWidth: 600,
    popupHeight: 700,
    successEventType: "strava-success",
    errorEventType: "strava-error",
    extractCallbackBody: (eventData, authResponse) => ({
      code: eventData.code as string,
      code_verifier: (authResponse as Record<string, unknown>)
        .code_verifier as string,
    }),
    handleCustomError: (detail, status) => {
      if (status === 502 && /Authorization Error|invalid/i.test(detail)) {
        return (
          "Strava rejected the connection: the BikeMaster app is in sandbox mode. " +
          "Open strava.com/settings/api, enter the BikeMaster app and add your " +
          "Strava account to 'Athlete Testers', then try again."
        );
      }
      return detail || "Strava connection failed";
    },
    onConnected: () => "Strava connected",
  },
  google_fit: {
    provider: "google_fit",
    authEndpoint: "/api/v1/import/google-fit/auth",
    callbackEndpoint: "/api/v1/import/google-fit",
    popupName: "google-fit-auth",
    popupWidth: 500,
    popupHeight: 600,
    successEventType: "google-fit-success",
    errorEventType: "google-fit-error",
    extractCallbackBody: (eventData) => ({
      access_token: eventData.token as string,
      refresh_token: (eventData.refresh_token as string) || "",
    }),
    onConnected: (result) => {
      const count = (result as Record<string, number>)?.count ?? 0;
      return `Importati ${count} percorsi da Google Fit`;
    },
  },
  google_health: {
    provider: "google_health",
    authEndpoint: "/api/v1/import/google-health/auth",
    callbackEndpoint: "/api/v1/import/google-health",
    popupName: "google-health-auth",
    popupWidth: 500,
    popupHeight: 600,
    successEventType: "google-health-success",
    errorEventType: "google-health-error",
    extractCallbackBody: (eventData) => ({
      access_token: eventData.token as string,
      refresh_token: (eventData.refresh_token as string) || "",
    }),
    onConnected: (result) => {
      const count = (result as Record<string, number>)?.count ?? 0;
      return `Importati ${count} percorsi da Google Health`;
    },
  },
  wahoo: {
    provider: "wahoo",
    authEndpoint: "/api/v1/import/wahoo/auth",
    callbackEndpoint: "/api/v1/import/wahoo/callback",
    popupName: "wahoo-auth",
    popupWidth: 500,
    popupHeight: 600,
    successEventType: "wahoo-success",
    errorEventType: "wahoo-error",
    extractCallbackBody: (eventData, authResponse) => ({
      code: eventData.code as string,
      code_verifier: (authResponse as Record<string, unknown>)
        .code_verifier as string,
    }),
    onConnected: () => "Wahoo connesso",
  },
  garmin: {
    provider: "garmin",
    authEndpoint: "/api/v1/import/garmin/auth",
    callbackEndpoint: "/api/v1/import/garmin/callback",
    popupName: "garmin-auth",
    popupWidth: 600,
    popupHeight: 700,
    successEventType: "garmin-success",
    errorEventType: "garmin-error",
    extractCallbackBody: (eventData, authResponse) => ({
      code: eventData.code as string,
      redirect_uri: "",
      state: (authResponse as Record<string, unknown>).state as string,
    }),
    onConnected: () => "Garmin connected",
  },
};

const OAUTH_RESULT_KEY = "bikemaster_oauth_result";

export function useOAuthConnection(config: OAuthProviderConfig) {
  const authStore = useAuthStore();
  const toast = useToast();

  const isConnecting = ref(false);
  const error = ref("");

  function setError(msg: string) {
    error.value = msg;
    toast.error(msg);
  }

  function clearError() {
    error.value = "";
  }

  function getRedirectUri(): string {
    const dev = import.meta.env.DEV;
    if (dev) return `http://localhost:8000${config.callbackEndpoint}`;
    if (isTauri())
      return `${TAURI_EMBEDDED_BACKEND_BASE}${config.callbackEndpoint}`;
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}${config.callbackEndpoint}`;
  }

  function getExpectedOAuthOrigin(): string {
    const base = resolveApiBase();
    if (!base) return typeof window !== "undefined" ? window.location.origin : "";
    try {
      return new URL(base).origin;
    } catch {
      return typeof window !== "undefined" ? window.location.origin : "";
    }
  }

  function cleanupListeners(
    handleMessage: (event: MessageEvent) => void,
    handleStorage: (event: StorageEvent) => void,
  ) {
    window.removeEventListener("message", handleMessage);
    window.removeEventListener("storage", handleStorage);
  }

  function closePopup(popup: Window | null) {
    if (popup && !popup.closed) {
      try {
        popup.close();
      } catch {
        try {
          popup.location.replace("about:blank");
        } catch {
          /* ignore */
        }
      }
    }
  }

  async function connect(): Promise<void> {
    isConnecting.value = true;
    clearError();
    try {
      const redirectUri = getRedirectUri();
      const state = btoa(JSON.stringify({ redirect_uri: redirectUri }));
      const url = `${config.authEndpoint}?redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`;
      const authResp = await fetch(url);
      if (!authResp.ok) {
        const err = await authResp.json().catch(() => ({}));
        throw new Error(
          err.detail ||
            `Impossibile avviare l'autenticazione ${config.provider}`,
        );
      }
      const authData = await authResp.json();

      const popup = window.open(
        (authData as Record<string, unknown>).auth_url as string,
        config.popupName,
        `width=${config.popupWidth},height=${config.popupHeight}`,
      );
      if (!popup) throw new Error("Popup bloccato - abilita i popup");

      const expectedOrigin = getExpectedOAuthOrigin();
      const code = await new Promise<string>((resolve, reject) => {
        let settled = false;
        const finish = () => {
          if (settled) return;
          settled = true;
          cleanupListeners(handleMessage, handleStorage);
          clearTimeout(timer);
          clearInterval(pollTimer);
          try {
            localStorage.removeItem(OAUTH_RESULT_KEY);
          } catch {
            /* ignore */
          }
        };
        const timer = setTimeout(
          () => {
            finish();
            closePopup(popup);
            reject(
              new Error(
                `Timeout: autenticazione ${config.provider} annullata. ` +
                  "Il popup potrebbe essere bloccato. Prova ad abilitare i popup per questo sito e riprova.",
              ),
            );
          },
          5 * 60 * 1000,
        );
        const pollTimer = setInterval(() => {
          if (popup && popup.closed && !settled) {
            finish();
            reject(
              new Error(
                `L'autenticazione ${config.provider} è stata annullata o il popup è stato chiuso.`,
              ),
            );
          }
        }, 1000);
        const handleMessage = (event: MessageEvent) => {
          if (!event.data) return;
          if (event.origin && event.origin !== expectedOrigin) return;
          if (event.data.type === config.errorEventType) {
            finish();
            closePopup(popup);
            reject(
              new Error(
                (event.data.error_description as string) ||
                  (event.data.error as string) ||
                  `Errore ${config.provider}`,
              ),
            );
            return;
          }
          if (event.data.type === config.successEventType) {
            finish();
            closePopup(popup);
            resolve(event.data.code as string);
          }
        };
        const handleStorage = (event: StorageEvent) => {
          if (event.key !== OAUTH_RESULT_KEY || !event.newValue) return;
          try {
            handleMessage({
              data: JSON.parse(event.newValue),
              origin: expectedOrigin,
            } as MessageEvent);
          } catch {
            /* ignore */
          }
        };
        window.addEventListener("message", handleMessage);
        window.addEventListener("storage", handleStorage);
      });

      const token = authStore.token;
      const headers: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {};
      const body = config.extractCallbackBody(
        { code } as Record<string, unknown>,
        authData as Record<string, unknown>,
      );
      const cbResp = await fetch(config.callbackEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify(body),
      });
      if (!cbResp.ok) {
        const err = await cbResp.json().catch(() => ({}));
        const detail: string = (err as { detail?: string }).detail || "";
        if (config.handleCustomError) {
          throw new Error(config.handleCustomError(detail, cbResp.status));
        }
        throw new Error(detail || `${config.provider} connection failed`);
      }
      const result = cbResp.ok ? await cbResp.json().catch(() => null) : null;
      toast.success(config.onConnected(result));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      throw e;
    } finally {
      isConnecting.value = false;
    }
  }

  async function disconnect(): Promise<void> {
    clearError();
    try {
      const token = authStore.token;
      const resp = await fetch(`/api/v1/import/${config.provider}/disconnect`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          (err as { detail?: string }).detail ||
            `Disconnessione ${config.provider} fallita`,
        );
      }
      toast.success("Disconnected");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      throw e;
    }
  }

  return {
    connect,
    disconnect,
    isConnecting,
    error,
    clearError,
  };
}
