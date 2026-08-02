import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import RideDetail from "../components/RideDetail.vue";

const apiGet = vi.hoisted(() => vi.fn().mockResolvedValue({}));
const apiPut = vi.hoisted(() => vi.fn().mockResolvedValue({}));

vi.mock("../utils/api.ts", () => ({
  apiGet,
  apiPut,
}));

vi.mock("../components/SpeedMap.vue", () => ({
  default: { template: '<div class="speed-map-stub" />' },
}));

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("RideDetail", () => {
  afterEach(() => vi.clearAllMocks());

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

  it("saves ride edits via PUT including avg_speed_kmh, weight_kg, is_official, source", async () => {
    const ride = {
      id: 42,
      date: "2026-08-01",
      title: "Morning ride",
      distance_km: 40,
      duration_minutes: 90,
      avg_speed_kmh: 22,
      weight_kg: 72,
      calories: 400,
      heart_rate_avg: 150,
      elevation_gain_m: 200,
      activity_type: "ride",
      is_official: true,
      source: "manual",
    };
    apiGet.mockResolvedValue(ride);
    apiPut.mockResolvedValue({ ...ride, distance_km: 50 });

    const wrapper = mount(RideDetail, {
      props: { rideId: 42 },
      global: { stubs: { SpeedMap: true } },
    });
    await flush();

    await wrapper.find('[aria-label="Modifica"]').trigger("click");
    await flush();

    await wrapper.find(".save-btn").trigger("click");
    await flush();

    expect(apiPut).toHaveBeenCalledWith(
      "/api/v1/rides/42",
      expect.objectContaining({
        distance_km: 40,
        heart_rate_avg: 150,
        elevation_gain_m: 200,
        avg_speed_kmh: 22,
        weight_kg: 72,
        is_official: true,
        source: "manual",
      })
    );
  });
});
