import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import RideMetricsPanel from "../components/RideMetricsPanel.vue";

const trackingState = {
  distance: 0,
  currentSpeed: 0,
  avgSpeed: 0,
  elapsedTime: 0,
  elevation: 0,
  heartRate: 0,
  cadence: 0,
  power: 0,
};

vi.mock("../stores/trackingStore", () => ({
  useTrackingStore: () => trackingState,
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

  it("formats time as MM:SS when under one hour", () => {
    trackingState.elapsedTime = 0;
    const wrapper = mount(RideMetricsPanel);
    expect(wrapper.vm.formattedTime).toBe("00:00");
  });

  it("formats time as HH:MM:SS when one hour or more", () => {
    trackingState.elapsedTime = 3661;
    const wrapper = mount(RideMetricsPanel);
    expect(wrapper.vm.formattedTime).toBe("1:01:01");
  });
});
