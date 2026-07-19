import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import App from "./App.vue";

const authState = { isLoggedIn: false, isAdmin: false };
const authStore = vi.hoisted(() => ({
  token: { value: "" },
  user: { value: null },
  get isLoggedIn() {
    return authState.isLoggedIn;
  },
  get isAdmin() {
    return authState.isAdmin;
  },
  isTokenValid: vi.fn(() => false),
  getAuthHeader: vi.fn(() => ({})),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  parseJWTPayload: vi.fn(),
  setAuthFromUrl: vi.fn(),
  setOauthError: vi.fn(),
}));

vi.mock("./stores/auth", () => ({
  useAuthStore: () => authStore,
}));

vi.mock("./composables/useRides", () => ({
  useRides: vi.fn(() => ({
    fetchSummary: vi.fn().mockResolvedValue({
      rides: 0,
      distance_km: 0,
      calories: 0,
      avg_speed_kmh: 0,
      duration_minutes: 0,
    }),
  })),
}));

describe("App.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    authState.isLoggedIn = false;
    authState.isAdmin = false;
    localStorage.clear();
    vi.clearAllMocks();
  });

  const stubs = {
    StatsSummary: { template: '<div class="stats-stub" />' },
    ToastContainer: { template: '<div class="toast-stub" />' },
    PWAInstallPrompt: { template: '<div class="pwa-stub" />' },
    HeaderTabs: { template: '<div class="tabs-stub" />' },
    HelpGuide: { template: '<div class="help-stub" />' },
    RouterView: { template: '<div class="rv-stub" />' },
  };

  it("shows login form when not logged in", () => {
    authState.isLoggedIn = false;
    const router = createRouter({ history: createWebHistory(), routes: [] });
    router.push = vi.fn();
    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
        stubs,
      },
    });
    expect(wrapper.find("form").exists()).toBe(true);
  });

  it("shows header tabs and summary when logged in", () => {
    authState.isLoggedIn = true;
    authState.isAdmin = false;
    const router = createRouter({ history: createWebHistory(), routes: [] });
    router.push = vi.fn();
    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
        stubs,
      },
    });
    expect(wrapper.find(".tabs-stub").exists()).toBe(true);
    expect(wrapper.find(".stats-stub").exists()).toBe(true);
  });

  it("displays login error when present", () => {
    authState.isLoggedIn = false;
    localStorage.setItem("bikemaster_login_error", "bad");
    const router = createRouter({ history: createWebHistory(), routes: [] });
    router.push = vi.fn();
    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
        stubs,
      },
    });
    expect(wrapper.find(".login-error").exists()).toBe(true);
    expect(localStorage.getItem("bikemaster_login_error")).toBe("bad");
  });

  it("loads summary on mount when already logged in", async () => {
    authState.isLoggedIn = true;
    const router = createRouter({ history: createWebHistory(), routes: [] });
    router.push = vi.fn();
    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
        stubs,
      },
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.find(".stats-stub").exists()).toBe(true);
  });
});
