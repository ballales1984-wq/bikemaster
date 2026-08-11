/**
 * ContinuousTracking composable.
 *
 * Manages automatic GPS tracking lifecycle:
 * - Auto-starts GPS when mounted (after permission check)
 * - Auto-pauses when the page/tab is hidden (visibilitychange)
 * - Auto-resumes when the page becomes visible again
 * - Integrates with the existing useBatteryEfficientGps
 */

import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useBatteryEfficientGps } from "./useBatteryEfficientGps";
import type { GpsPoint } from "../types/index";

export interface ContinuousTrackingOptions {
  onPosition: (point: GpsPoint) => void;
  onError: (error: GeolocationPositionError) => void;
  onWaiting?: () => void;
  onFirstFix?: () => void;
  onActivityChange?: (moving: boolean) => void;
  batterySaver?: () => boolean;
  autoStart?: boolean;
  autoPauseOnHidden?: boolean;
  minMovementMeters?: number;
}

export interface ContinuousTrackingState {
  isTracking: boolean;
  isPaused: boolean;
  isWaiting: boolean;
  isMoving: boolean;
  hasPermission: boolean | null;
  error: string;
}

export function useContinuousTracking(options: ContinuousTrackingOptions) {
  const {
    autoStart = true,
    autoPauseOnHidden = true,
    minMovementMeters = 1.5,
  } = options;

  const isTracking = ref(false);
  const isPaused = ref(false);
  const hasPermission = ref<boolean | null>(null);
  const error = ref("");

  let gps: ReturnType<typeof useBatteryEfficientGps> | null = null;
  let wasTrackingBeforeHidden = false;

  async function checkPermission(): Promise<boolean> {
    if (!navigator.geolocation) {
      error.value = "Geolocation not supported";
      return false;
    }
    try {
      const result = await navigator.permissions.query({ name: "geolocation" });
      if (result.state === "granted") {
        hasPermission.value = true;
        return true;
      }
      if (result.state === "prompt") {
        hasPermission.value = null;
        return true;
      }
      hasPermission.value = false;
      return false;
    } catch {
      hasPermission.value = null;
      return true;
    }
  }

  async function requestPermission(): Promise<boolean> {
    try {
      const position = await new Promise<GeolocationPosition>(
        (resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
          });
        },
      );
      hasPermission.value = true;
      return true;
    } catch (err) {
      hasPermission.value = false;
      error.value =
        err instanceof GeolocationPositionError
          ? err.message
          : "Permission denied";
      return false;
    }
  }

  function initGps() {
    gps = useBatteryEfficientGps({
      onPosition: (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const altitude = position.coords.altitude;
        const timestamp = position.timestamp;
        options.onPosition({
          lat,
          lon,
          altitude: altitude ?? null,
          timestamp: new Date(timestamp).toISOString(),
          timestampNumber: timestamp,
          heartRate: null,
          cadence: null,
          power: null,
        });
      },
      onError: (err) => {
        error.value = err.message;
        options.onError(err);
      },
      onWaiting: options.onWaiting,
      onFirstFix: () => {
        error.value = "";
        options.onFirstFix?.();
      },
      onActivityChange: options.onActivityChange,
      batterySaver: options.batterySaver,
    });
  }

  async function start() {
    if (isTracking.value) return;
    const granted = await checkPermission();
    if (!granted) {
      const requested = await requestPermission();
      if (!requested) return;
    }

    if (!gps) initGps();

    error.value = "";
    isPaused.value = false;
    isTracking.value = true;
    gps.start();
  }

  function pause() {
    if (!isTracking.value || isPaused.value) return;
    isPaused.value = true;
    gps?.pause();
  }

  function resume() {
    if (!isTracking.value || !isPaused.value) return;
    isPaused.value = false;
    gps?.resume();
  }

  function stop() {
    isTracking.value = false;
    isPaused.value = false;
    gps?.stop();
    gps = null;
  }

  function handleVisibilityChange() {
    if (!autoPauseOnHidden) return;
    if (document.hidden) {
      wasTrackingBeforeHidden = isTracking.value && !isPaused.value;
      if (wasTrackingBeforeHidden) {
        pause();
      }
    } else {
      if (wasTrackingBeforeHidden && isTracking.value) {
        resume();
      }
      wasTrackingBeforeHidden = false;
    }
  }

  onMounted(async () => {
    if (autoStart) {
      await start();
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    stop();
  });

  return {
    isTracking,
    isPaused,
    hasPermission,
    error,
    start,
    pause,
    resume,
    stop,
  };
}
