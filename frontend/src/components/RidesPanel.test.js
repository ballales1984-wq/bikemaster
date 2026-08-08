import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
const apiDelete = vi.hoisted(() => vi.fn());

vi.mock("../utils/api.ts", () => ({ apiGet, apiPost, apiDelete }));
vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}));

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

const pinia = createPinia();
setActivePinia(pinia);

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", component: { template: "<div />" } }],
});

const globalConfig = {
  plugins: [pinia, router],
  stubs: { ConfirmModal: true, RouterLink: true },
};

import RidesPanel from "./RidesPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("RidesPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    mockAuth.isLoggedIn = true;
  });

  it("shows the list of loaded rides", async () => {
    apiGet.mockResolvedValueOnce({
      rides: [
        {
          id: 1,
          date: "2026-06-01",
          distance_km: 42.5,
          duration_minutes: 90,
          avg_speed_kmh: 28.3,
        },
        {
          id: 2,
          date: "2026-06-08",
          distance_km: 25.0,
          duration_minutes: 60,
          avg_speed_kmh: 25.0,
        },
      ],
      total: 2,
    });

    const wrapper = mount(RidesPanel, {
      global: globalConfig,
    });
    await flush();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/rides", expect.any(Object));
    const items = wrapper.findAll(".ride-item");
    expect(items).toHaveLength(2);
  });

  it("shows empty state when no rides", async () => {
    apiGet.mockResolvedValueOnce({ rides: [], total: 0 });

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    });
    await flush();

    expect(wrapper.find(".empty-state").exists()).toBe(true);
    expect(wrapper.text()).toContain("rides.noRides");
  });

  it("adds a ride by filling the form", async () => {
    apiGet
      .mockResolvedValueOnce({ rides: [], total: 0 })
      .mockResolvedValueOnce({ rides: 0, distance_km: 50, calories: 0, avg_speed_kmh: 25, duration_minutes: 120 });
    apiPost.mockResolvedValueOnce({ id: 10 });

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    });
    await flush();

    await wrapper.find(".add-header").trigger("click");
    await flush();

    const dateInput = wrapper.find('input[type="date"]');
    const numberInputs = wrapper.findAll('input[type="number"]');
    await dateInput.setValue("2026-06-15");
    await numberInputs[0].setValue("50");
    await numberInputs[1].setValue("120");
    await wrapper.find("form").trigger("submit");
    await flush();

    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/rides",
      expect.objectContaining({
        date: "2026-06-15",
        distance_km: 50,
        duration_minutes: 120,
      }),
    );
  });

  it("opens ride detail on click", async () => {
    apiGet.mockResolvedValueOnce({
      rides: [
        {
          id: 5,
          date: "2026-05-20",
          distance_km: 30,
          duration_minutes: 70,
          avg_speed_kmh: 25,
        },
      ],
      total: 1,
    });

    const wrapper = mount(RidesPanel, {
      global: {
        stubs: {
          ConfirmModal: { template: '<div class="confirm-modal-stub" />' },
        },
      },
    });
    await flush();

    await wrapper.findAll(".ride-item")[0].trigger("click");
    await flush();

    expect(wrapper.vm.selectedRide).toBeTruthy();
  });

  it("shows guest state when not logged in", async () => {
    mockAuth.isLoggedIn = false;

    const wrapper = mount(RidesPanel, {
      global: { stubs: { ConfirmModal: true } },
    });
    await flush();

    expect(wrapper.vm.guest).toBe(true);
    expect(wrapper.find(".empty-state").exists()).toBe(true);
  });
});
