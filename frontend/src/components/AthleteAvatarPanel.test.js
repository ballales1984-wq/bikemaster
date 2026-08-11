import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { reactive, ref, toRef } from "vue";

const mockFetchProfile = vi.hoisted(() => vi.fn(() => Promise.resolve(null)));
const mockFetchState = vi.hoisted(() => vi.fn(() => Promise.resolve(null)));

const mockAthleteStore = reactive({
  profile: null,
  fetchProfile: mockFetchProfile,
  updateProfile: vi.fn(),
  fetchMetricLog: vi.fn(() => Promise.resolve([])),
  error: null,
});

const mockAuthStore = reactive({
  isLoggedIn: true,
});

const mockAthleteStateStore = reactive({
  state: null,
  fetchState: mockFetchState,
  error: null,
});

vi.mock("../stores/athlete", () => ({
  useAthleteStore: () => mockAthleteStore,
}));

vi.mock("../stores/athleteState", () => ({
  useAthleteStateStore: () => mockAthleteStateStore,
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => mockAuthStore,
}));

vi.mock("pinia", async () => {
  const actual = await vi.importActual("pinia");
  return {
    ...actual,
    storeToRefs: (store) => {
      if (store === mockAthleteStore) {
        return {
          profile: toRef(store, "profile"),
          error: toRef(store, "error"),
        };
      }
      if (store === mockAthleteStateStore) {
        return {
          state: toRef(store, "state"),
          error: toRef(store, "error"),
        };
      }
      return actual.storeToRefs(store);
    },
  };
});

import AthleteAvatarPanel from "./AthleteAvatarPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockProfile = {
  id: 1,
  name: "Marco Rossi",
  age: 35,
  weight_kg: 72,
  height_cm: 178,
  ftp_watts: 280,
  experience_level: "Intermediate",
  years_active: 8,
  weekly_sessions: 4,
  monthly_hours: 12,
  annual_hours: 144,
  body_water_percentage: 55,
  muscle_mass_percentage: 42,
  bmr_kcal: 1850,
  fat_mass_kg: 10,
  muscle_mass_kg: 32,
  bone_mass_kg: 4.5,
  protein_percentage: 18,
  visceral_fat_level: 6,
  equipment: "S-Works Tarmac, 4iiii",
  medical_notes: null,
};

const mockState = {
  athlete_id: 1,
  computed_at: "2026-08-08T20:00:00Z",
  fatigue_score: 4.2,
  readiness: 78,
  acwr: 1.05,
  tsb: 12,
  atl: 55,
  ctl: 62,
  fitness: 62,
  form: 7,
  recovery_hours_needed: 0,
  weekly_tss: 450,
  monthly_tss: 1800,
  trend_7d: "stable",
  trend_30d: "improving",
  risk_indicators: [],
  recommendation: "Continue current training load.",
  risk_level: "ok",
  is_overtraining_risk: false,
  is_fresh: true,
  is_ready_for_hard_effort: true,
};

describe("AthleteAvatarPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    mockAthleteStore.profile = null;
    mockAthleteStore.error = null;
    mockAthleteStateStore.state = null;
    mockAthleteStateStore.error = null;
    mockAuthStore.isLoggedIn = true;
  });

  it("loads profile and state on mount when logged in", async () => {
    mockFetchProfile.mockResolvedValueOnce(mockProfile);
    mockFetchState.mockResolvedValueOnce(mockState);
    mockAthleteStore.profile = mockProfile;
    mockAthleteStateStore.state = mockState;

    const wrapper = mount(AthleteAvatarPanel);
    await flush();

    expect(mockFetchProfile).toHaveBeenCalledTimes(1);
    expect(mockFetchState).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Marco Rossi");
    expect(wrapper.text()).toContain("280");
  });

  it("does not fetch when not logged in", async () => {
    mockAuthStore.isLoggedIn = false;

    const wrapper = mount(AthleteAvatarPanel);
    await flush();

    expect(mockFetchProfile).not.toHaveBeenCalled();
    expect(mockFetchState).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Atleta");
  });

  it("shows equipment and medical notes when present", async () => {
    mockAthleteStore.profile = {
      ...mockProfile,
      equipment: "S-Works Tarmac",
      medical_notes: "Asma lieve",
    };
    mockAthleteStateStore.state = mockState;

    const wrapper = mount(AthleteAvatarPanel);
    await flush();

    expect(wrapper.text()).toContain("Equipaggiamento");
    expect(wrapper.text()).toContain("S-Works Tarmac");
    expect(wrapper.text()).toContain("Note mediche");
    expect(wrapper.text()).toContain("Asma lieve");
  });

  it("hides equipment section when both fields are empty", async () => {
    mockAthleteStore.profile = {
      ...mockProfile,
      equipment: null,
      medical_notes: null,
    };
    mockAthleteStateStore.state = mockState;

    const wrapper = mount(AthleteAvatarPanel);
    await flush();

    expect(wrapper.text()).not.toContain("Equipaggiamento");
    expect(wrapper.text()).not.toContain("Note mediche");
  });

  it("renders fitness state when available", async () => {
    mockAthleteStore.profile = mockProfile;
    mockAthleteStateStore.state = mockState;

    const wrapper = mount(AthleteAvatarPanel);
    await flush();

    expect(wrapper.text()).toContain("Fitness State");
    expect(wrapper.text()).toContain("Readiness");
    expect(wrapper.text()).toContain("78%");
    expect(wrapper.text()).toContain("OK");
  });
});
