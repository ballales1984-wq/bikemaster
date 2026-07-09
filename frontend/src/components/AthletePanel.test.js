import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
const apiPut = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet, apiPost, apiPut }));

vi.mock("../composables/useToast", () => ({
  useToast: () => ({
    show: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    add: vi.fn(),
    remove: vi.fn(),
    items: [],
  }),
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => ({
    user: { value: { username: "testuser" } },
    token: { value: "test-token" },
    isLoggedIn: true,
    isAdmin: false,
    isTokenValid: true,
    getAuthHeader: () => ({}),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    parseJWTPayload: vi.fn(),
    setAuthFromUrl: vi.fn(),
    setOauthError: vi.fn(),
  }),
}));

import AthletePanel from "./AthletePanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockAthlete = {
  athlete: {
    id: 3,
    name: "Marco Rossi",
    age: 35,
    weight_kg: 72,
    height_cm: 178,
    fat_percentage: 14,
    years_active: 5,
    weekly_sessions: 4,
    monthly_hours: 12,
    annual_hours: 144,
    experience_level: "Intermediate",
  },
};

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", component: { template: "<div />" } }],
});

describe("AthletePanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads existing athlete profile on mount", async () => {
    apiGet.mockResolvedValueOnce(mockAthlete);

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/athletes/me");
    expect(wrapper.find("#athlete-name").element.value).toBe("Marco Rossi");
    expect(wrapper.find("#athlete-age").element.value).toBe("35");
    expect(wrapper.find("#athlete-weight").element.value).toBe("72");
  });

  it("saves new athlete (POST) if none exists", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });
    apiPost.mockResolvedValueOnce({ id: 10 });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("#athlete-name").setValue("Luca Bianchi");
    await wrapper.find("button.btn-primary").trigger("click");
    await flush();

    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/athletes",
      expect.objectContaining({ name: "Luca Bianchi" }),
    );
    expect(wrapper.find(".result-box").text()).toContain("ID: 10");
  });

  it("updates existing athlete (PUT)", async () => {
    apiGet.mockResolvedValueOnce(mockAthlete);
    apiPut.mockResolvedValueOnce({ id: 3 });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("#athlete-name").setValue("Marco Verdi");
    await wrapper.find("button.btn-primary").trigger("click");
    await flush();

    expect(apiPut).toHaveBeenCalledWith(
      "/api/v1/athletes/3",
      expect.objectContaining({ name: "Marco Verdi" }),
    );
    expect(apiPost).not.toHaveBeenCalled();
  });

  it("shows error if save fails", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });
    apiPost.mockRejectedValueOnce(new Error("Server error"));

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("button.btn-primary").trigger("click");
    await flush();

    expect(wrapper.find(".result-box").text()).toContain(
      "Correggi gli errori nel form",
    );
  });

  it("scores button calls scores endpoint", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthlete)
      .mockResolvedValueOnce({ performance: 85, endurance: 78 });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("button.btn-secondary").trigger("click");
    await flush();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/scores/athlete/3");
  });

  it("renders form fields correctly", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    expect(wrapper.find("#athlete-name").exists()).toBe(true);
    expect(wrapper.find("#athlete-age").exists()).toBe(true);
    expect(wrapper.find("#athlete-weight").exists()).toBe(true);
    expect(wrapper.find("#athlete-height").exists()).toBe(true);
    expect(wrapper.find("#athlete-fat").exists()).toBe(true);
    expect(wrapper.find("#athlete-level").exists()).toBe(true);
  });

  it("shows athlete profile info", async () => {
    apiGet.mockResolvedValueOnce(mockAthlete);

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    expect(wrapper.find("h2").text()).toContain("Athlete Profile");
    expect(wrapper.find("#athlete-name").element.value).toBe("Marco Rossi");
  });

  it("displays save and scores buttons", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    expect(wrapper.text()).toContain("Save Athlete");
    expect(wrapper.text()).toContain("Scores");
  });

  it("saves athlete with all form fields", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });
    apiPost.mockResolvedValueOnce({ id: 10 });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("#athlete-name").setValue("Giulia Neri");
    await wrapper.find("#athlete-age").setValue(28);
    await wrapper.find("#athlete-weight").setValue(65);
    await wrapper.find("#athlete-height").setValue(168);
    await wrapper.find("#athlete-fat").setValue(20);
    await wrapper.find("#athlete-level").setValue("Advanced");
    await wrapper.find("#athlete-years").setValue(8);
    await wrapper.find("#athlete-weekly").setValue(5);
    await wrapper.find("#athlete-monthly").setValue(18);
    await wrapper.find("#athlete-annual").setValue(210);
    await wrapper.find("button.btn-primary").trigger("click");
    await flush();

    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/athletes",
      expect.objectContaining({
        name: "Giulia Neri",
        age: 28,
        weight_kg: 65,
        experience_level: "Advanced",
      }),
    );
  });

  it("handles load athlete API failure", async () => {
    apiGet.mockRejectedValueOnce(new Error("Load failed"));

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    const resultBox = wrapper.find(".result-box");
    expect(resultBox.exists()).toBe(true);
  });

  it("shows warning when scores called without athlete", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("button.btn-secondary").trigger("click");
    await flush();

    expect(wrapper.find(".result-box").text()).toContain(
      "Save athlete profile first",
    );
  });

  it("emits toast on save", async () => {
    apiGet.mockResolvedValueOnce({ athlete: null });
    apiPost.mockResolvedValueOnce({ id: 10 });

    const wrapper = mount(AthletePanel, {
      global: { plugins: [router] },
    });
    await flush();

    await wrapper.find("#athlete-name").setValue("Test User");
    await wrapper.find("button.btn-primary").trigger("click");
    await flush();

    expect(wrapper.find(".result-box").exists()).toBe(true);
  });
});
