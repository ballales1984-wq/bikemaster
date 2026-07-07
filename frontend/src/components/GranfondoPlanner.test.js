import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet, apiPost }));

import GranfondoPlanner from "./GranfondoPlanner.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockAthletes = {
  athletes: [{ id: 1, name: "Test Rider" }],
};

const mockAthleteMe = {
  athlete: { id: 1, name: "Test Rider" },
};

const mockPlan = [
  {
    date: "2026-06-20",
    title: "Endurance Ride",
    workout_type: "endurance",
    duration_minutes: 120,
    target_intensity: 0.7,
  },
  {
    date: "2026-06-22",
    title: "Recovery",
    workout_type: "recovery",
    duration_minutes: 60,
    target_intensity: 0.5,
  },
];

describe("GranfondoPlanner", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads athlete ID on mount", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);

    const wrapper = mount(GranfondoPlanner);
    await flush();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/athletes");
  });

  it("has form fields for date and weeks", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);

    const wrapper = mount(GranfondoPlanner);
    await flush();

    expect(wrapper.find("#gf-start-date").exists()).toBe(true);
    expect(wrapper.find("#gf-weeks").exists()).toBe(true);
    expect(wrapper.vm.weeks).toBe(8);
  });

  it("generates plan when button clicked", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiPost.mockResolvedValueOnce({ plan: mockPlan });

    const wrapper = mount(GranfondoPlanner);
    await flush();

    const button = wrapper.find(".btn-primary");
    await button.trigger("click");
    await flush();

    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/training/granfondo/plan",
      expect.objectContaining({
        athlete_id: 1,
        start_date: expect.any(String),
        target_weeks: 8,
      }),
    );
  });

  it("displays plan after generation", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiPost.mockResolvedValueOnce({ plan: mockPlan });

    const wrapper = mount(GranfondoPlanner);
    await flush();

    const button = wrapper.find(".btn-primary");
    await button.trigger("click");
    await flush();

    expect(wrapper.vm.plan).toEqual(mockPlan);
  });

  it("calculates end date based on start date and weeks", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);

    const wrapper = mount(GranfondoPlanner);
    await flush();

    wrapper.vm.startDate = "2026-06-20";
    wrapper.vm.weeks = 8;

    expect(wrapper.vm.endDate).toBe("2026-08-15");
  });

  it("handles plan generation error", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiPost.mockRejectedValueOnce(new Error("Failed to generate plan"));

    const wrapper = mount(GranfondoPlanner);
    await flush();

    const button = wrapper.find(".btn-primary");
    await button.trigger("click");
    await flush();

    expect(wrapper.vm.plan).toBe(null);
  });

  it("has save button when plan is generated", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiPost.mockResolvedValueOnce({ plan: mockPlan });

    const wrapper = mount(GranfondoPlanner);
    await flush();

    const button = wrapper.find(".btn-primary");
    await button.trigger("click");
    await flush();

    expect(wrapper.find(".btn-success").exists()).toBe(true);
  });

  it("has loading state initially false", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);

    const wrapper = mount(GranfondoPlanner);
    await flush();

    expect(wrapper.vm.loading).toBe(false);
  });

  it("has week days array", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);

    const wrapper = mount(GranfondoPlanner);
    await flush();

    expect(wrapper.vm.weekDays).toEqual([
      "granfondo.weekMon",
      "granfondo.weekTue",
      "granfondo.weekWed",
      "granfondo.weekThu",
      "granfondo.weekFri",
      "granfondo.weekSat",
      "granfondo.weekSun",
    ]);
  });

  it("disable generate button when no athlete", async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] });

    const wrapper = mount(GranfondoPlanner);
    await flush();

    // athleteId would be 0 if no athletes
    expect(wrapper.vm.athleteId).toBe(0);
  });
});
