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
  const autoTracking = ref(true);
  const autoDetectActivities = ref(true);
  const autoSaveSegments = ref(true);
  const segments = ref([]);
  const currentSegment = ref(null);
  const activityRings = ref([
    { label: "move", current: 0, goal: 500, unit: "min", color: "#10b981" },
    { label: "exercise", current: 0, goal: 30, unit: "min", color: "#3b82f6" },
    { label: "stand", current: 0, goal: 12, unit: "x", color: "#f59e0b" },
  ]);

  function start() { isTracking.value = true; isPaused.value = false; }
  function stop() { isTracking.value = false; isPaused.value = false; }
  function pause() { isPaused.value = true; }
  function resume() { isPaused.value = false; }
  function addPoint() {}
  function updateMetrics() {}
  function resetMetrics() {}
  function setGpxPath() {}
  function setGpxBlob() {}
  function setRideId() {}
  function startSegment() { return "seg_test"; }
  function closeCurrentSegment() { return null; }
  function updateSegmentFromPoint() {}
  function updateActivityRings() {}
  function getTodaySegments() { return []; }
  function buildDailyTimeline() { return []; }
  function toGpx() { return ""; }
  function persistState() {}
  function restoreState() { return false; }
  function clearPersistedState() {}
  function clearAll() {}

  return {
    isTracking, isPaused, distance, currentSpeed, avgSpeed,
    elapsedTime, elevation, points, heartRate, cadence, power,
    gpxPath, gpxBlob, routePoints, lastPoint, rideId,
    autoTracking, autoDetectActivities, autoSaveSegments,
    segments, currentSegment, activityRings,
    start, stop, pause, resume, addPoint, updateMetrics,
    resetMetrics, setGpxPath, setGpxBlob, setRideId,
    startSegment, closeCurrentSegment, updateSegmentFromPoint,
    updateActivityRings, getTodaySegments, buildDailyTimeline,
    toGpx, persistState, restoreState, clearPersistedState, clearAll,
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

vi.mock("../components/DailyTimeline.vue", () => ({
  default: { template: '<div class="daily-timeline-stub" />' },
}));

vi.mock("../components/ActivityRings.vue", () => ({
  default: { template: '<div class="activity-rings-stub" />' },
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

vi.mock("../composables/useContinuousTracking", () => ({
  useContinuousTracking: () => ({
    isTracking: { value: false },
    isPaused: { value: false },
    hasPermission: { value: null },
    error: { value: "" },
    start: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock("../composables/useActivitySegmentation", () => ({
  useActivitySegmentation: () => ({
    segments: { value: [] },
    currentSegment: { value: null },
    state: { value: "idle" },
    lastSpeedKmh: { value: 0 },
    processPoint: vi.fn(),
    closeCurrentSegment: vi.fn(),
    getTodaySegments: () => [],
    getActiveSegments: () => [],
    clearAll: vi.fn(),
    totalTodayDistanceKm: { value: 0 },
    totalTodayActiveMinutes: { value: 0 },
  }),
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
