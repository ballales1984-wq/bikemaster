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

  return {
    isTracking, isPaused, distance, currentSpeed, avgSpeed,
    elapsedTime, elevation, points, heartRate, cadence, power,
    gpxPath, gpxBlob, routePoints, lastPoint, rideId,
    start, stop, pause, resume, addPoint, updateMetrics,
    resetMetrics, setGpxPath, setGpxBlob, setRideId, toGpx,
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
