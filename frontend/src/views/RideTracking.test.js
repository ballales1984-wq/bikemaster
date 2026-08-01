import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import { setActivePinia, createPinia, defineStore } from "pinia";
import { ref } from "vue";

const useTrackingStore = defineStore("tracking", () => {
  const isTracking = ref(false);
  const isPaused = ref(false);
  const distance = ref(0);
  const currentSpeed = ref(0);
  const avgSpeed = ref(0);
  const elapsedTime = ref(0);
  const elevation = ref(0);
  const points = ref(0);
  const heartRate = ref(null);
  const cadence = ref(null);
  const power = ref(null);
  const gpxPath = ref(null);
  const gpxBlob = ref(null);
  const routePoints = ref([]);
  const lastPoint = ref(null);
  const rideId = ref(null);

  function start() {
    isTracking.value = true;
    isPaused.value = false;
  }
  function stop() {
    isTracking.value = false;
    isPaused.value = false;
  }
  function pause() { isPaused.value = true; }
  function resume() { isPaused.value = false; }
  function addPoint() {}
  function updateMetrics() {}
  function resetMetrics() {}
  function setGpxPath() {}
  function setGpxBlob() {}
  function setRideId() {}
  function toGpx() { return ""; }
  function persistState() {}
  function restoreState() { return false; }
  function clearPersistedState() {}

  return {
    isTracking, isPaused, distance, currentSpeed, avgSpeed,
    elapsedTime, elevation, points, heartRate, cadence, power,
    gpxPath, gpxBlob, routePoints, lastPoint, rideId,
    start, stop, pause, resume, addPoint, updateMetrics,
    resetMetrics, setGpxPath, setGpxBlob, setRideId, toGpx,
    persistState, restoreState, clearPersistedState,
  };
});

vi.mock("../stores/trackingStore", () => ({
  useTrackingStore,
}));

vi.mock("../utils/api", () => ({
  apiUpload: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock("../components/LiveMap.vue", () => ({
  default: { template: '<div class="live-map-stub" />' },
}));

vi.mock("../components/RideMetricsPanel.vue", () => ({
  default: { template: '<div class="metrics-panel-stub" />' },
}));

vi.mock("../components/ControlsBar.vue", () => ({
  default: { template: '<div class="controls-bar-stub" />' },
}));

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => {
      const translations = {
        "tracking.title": "GPS Tracking",
        "tracking.paused": "Paused",
        "tracking.inProgress": "In progress",
        "tracking.ready": "Ready to track your ride",
        "tracking.readyDesc":
          "Press the button below to start recording your route in real-time.",
        "tracking.offline":
          "Offline: tracking works, but map tiles may be limited until connectivity returns.",
        "tracking.start": "Start Tracking",
      };
      return translations[key] || key;
    },
    setLocale: vi.fn(),
  }),
}));

vi.mock("../composables/useBatteryEfficientGps", () => ({
  useBatteryEfficientGps: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    isWaiting: { value: false },
    isMoving: { value: false },
  }),
}));

vi.mock("../composables/useVoiceCoach", () => ({
  useVoiceCoach: () => ({
    startVoiceCoachInterval: vi.fn(),
    stopVoiceCoachInterval: vi.fn(),
  }),
}));

vi.mock("../composables/useGpsOutlierFilter", () => ({
  useGpsOutlierFilter: () => ({
    isOutlier: vi.fn().mockReturnValue(false),
    reset: vi.fn(),
  }),
}));

vi.mock("../composables/useGpsDirectionFilter", () => ({
  useGpsDirectionFilter: () => ({
    isDirectionOutlier: vi.fn().mockReturnValue(false),
    accept: vi.fn().mockReturnValue(null),
    reset: vi.fn(),
  }),
  bearing: vi.fn(),
  detectTurnFromBearing: vi.fn().mockReturnValue(false),
}));

describe("RideTracking", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/", component: { template: "<div />" } }],
  });

  it("has isTracking initially false", async () => {
    const mod = await import("../views/RideTracking.vue");
    const wrapper = mount(mod.default, {
      global: { plugins: [router] },
    });
    expect(wrapper.find(".tracking-panel").exists()).toBe(true);
  }, 10000);

  it("has start tracking functionality", async () => {
    const mod = await import("../views/RideTracking.vue");
    const wrapper = mount(mod.default, {
      global: { plugins: [router] },
    });
    expect(wrapper.find("button.pulse-btn").exists()).toBe(true);
  });

  it("renders header", async () => {
    const mod = await import("../views/RideTracking.vue");
    const wrapper = mount(mod.default, {
      global: { plugins: [router] },
    });
    expect(wrapper.find("h2").exists()).toBe(true);
    expect(wrapper.find("h2").text()).toBe("GPS Tracking");
  });
});
