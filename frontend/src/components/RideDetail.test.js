import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import RideDetail from "../components/RideDetail.vue";

vi.mock("../utils/api.ts", () => ({
  apiGet: vi.fn().mockResolvedValue({}),
}));

vi.mock("../components/SpeedMap.vue", () => ({
  default: { template: '<div class="speed-map-stub" />' },
}));

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("RideDetail", () => {
  it("does not render when no ride", () => {
    const wrapper = mount(RideDetail, {
      global: { stubs: { SpeedMap: true } },
    });
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("renders ride details when ride is set", async () => {
    const wrapper = mount(RideDetail, {
      props: { rideId: 1 },
      global: { stubs: { SpeedMap: true } },
    });

    wrapper.vm.ride = {
      id: 1,
      date: "2026-01-01",
      distance_km: 40,
      duration_minutes: 90,
      avg_speed_kmh: 26.7,
      calories: 400,
    };
    await flush();

    expect(wrapper.find("h2").exists()).toBe(true);
    expect(wrapper.find(".metrics-grid").exists()).toBe(true);
    expect(wrapper.findAll(".metric-card").length).toBe(4);
  });

  it("formats distance correctly", () => {
    const wrapper = mount(RideDetail, {
      global: { stubs: { SpeedMap: true } },
    });
    expect(wrapper.vm.fmt(40)).toBe("40.0");
    expect(wrapper.vm.fmt(null)).toBe("—");
  });
});
