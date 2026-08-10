import { describe, expect, it, vi, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import RideComparison from "./RideComparison.vue";

const mockAuth = vi.hoisted(() => ({
  isLoggedIn: true,
  token: "test-token",
  user: { id: 1, username: "test" },
  isAdmin: false,
  isClient: false,
  justLoggedIn: false,
  setJustLoggedIn: vi.fn(),
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => mockAuth,
}));

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}));

vi.mock("../utils/api.ts", () => ({
  apiGet: vi.fn().mockResolvedValue({ rides: [] }),
}));

const pinia = createPinia();
setActivePinia(pinia);

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", component: { template: "<div />" } }],
});

const globalConfig = {
  plugins: [pinia, router],
};

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("RideComparison", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the title", () => {
    const wrapper = mount(RideComparison, {
      global: globalConfig,
    });
    expect(wrapper.find("h2").text()).toContain("comparison.title");
  });

  it("has swap button", () => {
    const wrapper = mount(RideComparison, {
      global: globalConfig,
    });
    expect(wrapper.find(".swap-btn").exists()).toBe(true);
  });

  it("shows empty state initially", async () => {
    const wrapper = mount(RideComparison, {
      global: globalConfig,
    });
    await flush();
    expect(wrapper.find(".empty-state").exists()).toBe(true);
  });

  it("calculates comparison correctly", async () => {
    const wrapper = mount(RideComparison, {
      global: globalConfig,
    });

    wrapper.vm.rideA = {
      id: 1,
      date: "2026-01-01",
      distance_km: 40,
      duration_minutes: 90,
      avg_speed_kmh: 26.7,
      elevation_gain_m: 500,
      calories: 400,
    };
    wrapper.vm.rideB = {
      id: 2,
      date: "2026-01-02",
      distance_km: 50,
      duration_minutes: 120,
      avg_speed_kmh: 25,
      elevation_gain_m: 600,
      calories: 500,
    };

    const comparison = wrapper.vm.comparison;
    expect(comparison.ready).toBe(true);
  });

  it("has metrics defined", () => {
    const wrapper = mount(RideComparison, {
      global: globalConfig,
    });
    expect(wrapper.vm.metrics.length).toBe(5);
  });
});
