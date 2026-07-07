import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";

vi.mock("pinia", async () => {
  const actual = await vi.importActual("pinia");
  return {
    ...actual,
    storeToRefs: (store) => store,
  };
});

import RideTracking from "../views/RideTracking.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div />' } }],
})

vi.mock("../stores/trackingStore", () => ({
  useTrackingStore: () => ({
    isTracking: { value: false },
    isPaused: { value: false },
    start: vi.fn(),
    stop: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    addPoint: vi.fn(),
    updateMetrics: vi.fn(),
    resetMetrics: vi.fn(),
    setGpxPath: vi.fn(),
    setGpxBlob: vi.fn(),
    toGpx: vi.fn(() => ""),
    routePoints: [],
    gpxPath: null,
    gpxBlob: null,
  }),
}));

vi.mock("../utils/api", () => ({
  apiUpload: vi.fn(),
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
  it("has isTracking initially false", () => {
    const wrapper = mount(RideTracking, {
      global: { plugins: [router] },
    });
    expect(wrapper.vm.isTracking.value).toBe(false);
  });

  it("has start tracking functionality", () => {
    const wrapper = mount(RideTracking, {
      global: { plugins: [router] },
    });
    expect(wrapper.vm.startTracking).toBeDefined();
  });

  it("renders header", () => {
    const wrapper = mount(RideTracking, {
      global: { plugins: [router] },
    });
    expect(wrapper.find("h2").exists()).toBe(true);
    expect(wrapper.find("h2").text()).toBe("GPS Tracking");
  });
});
