import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import StatsSummary from "../components/StatsSummary.vue";

describe("StatsSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.requestAnimationFrame = (cb) =>
      setTimeout(() => cb(performance.now()), 0);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders zero stats when props are null", () => {
    const wrapper = mount(StatsSummary, {
      props: { stats: null, loading: false },
    });
    const values = wrapper.findAll(".stat-value");
    // StatsSummary has 5 stat values (rides, distance, calories, speed, hours)
    expect(values.length).toBe(5);
    expect(values[0].text()).toBe("0");
  });

  it("has correct number of stat cards", async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: {
          rides: 42,
          calories: 1234,
          distance_km: 123.45,
          avg_speed_kmh: 28.3,
          duration_minutes: 125,
        },
        loading: false,
      },
    });
    // Wait for animation
    await new Promise((resolve) => setTimeout(resolve, 50));
    const cards = wrapper.findAll(".stat-card");
    expect(cards.length).toBe(6);
  });

  it("emits refresh when refresh button is clicked", async () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: {
          rides: 0,
          distance_km: 0,
          avg_speed_kmh: 0,
          calories: 0,
          duration_minutes: 0,
        },
        loading: false,
      },
    });
    await wrapper.find("button.stat-refresh").trigger("click");
    expect(wrapper.emitted("refresh")).toBeTruthy();
  });

  it("disables refresh button and shows loading text", () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: {
          rides: 0,
          distance_km: 0,
          avg_speed_kmh: 0,
          calories: 0,
          duration_minutes: 0,
        },
        loading: true,
      },
    });
    const btn = wrapper.find("button.stat-refresh");
    expect(btn.attributes("disabled")).toBeDefined();
    expect(btn.text()).toContain("Updating");
  });

  it("has accessible labels", () => {
    const wrapper = mount(StatsSummary, {
      props: {
        stats: {
          rides: 0,
          distance_km: 0,
          avg_speed_kmh: 0,
          calories: 0,
          duration_minutes: 0,
        },
        loading: false,
      },
    });
    expect(wrapper.find('[aria-label="General Statistics"]').exists()).toBe(
      true,
    );
    expect(wrapper.findAll('[role="status"]').length).toBe(5);
  });
});
