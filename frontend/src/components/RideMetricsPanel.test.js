import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import RideMetricsPanel from "../components/RideMetricsPanel.vue";

vi.mock("../stores/trackingStore", () => ({
  useTrackingStore: () => ({
    distance: 0,
    currentSpeed: 0,
    avgSpeed: 0,
    elapsedTime: 0,
    elevation: 0,
    heartRate: 0,
    cadence: 0,
    power: 0,
  }),
}));

describe("RideMetricsPanel", () => {
  it("renders metrics grid", () => {
    const wrapper = mount(RideMetricsPanel);
    expect(wrapper.find(".metrics-grid").exists()).toBe(true);
  });

  it("has distance metric", () => {
    const wrapper = mount(RideMetricsPanel);
    const cards = wrapper.findAll(".metric-card");
    expect(cards.length).toBeGreaterThanOrEqual(1);
  });

  it("formats time correctly", () => {
    const wrapper = mount(RideMetricsPanel);
    expect(wrapper.vm.formattedTime).toBe("00:00:00");
  });
});
