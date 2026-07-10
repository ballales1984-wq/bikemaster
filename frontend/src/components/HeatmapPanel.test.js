import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

import HeatmapPanel from "./HeatmapPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockAthletes = {
  athletes: [{ id: 1, name: "Test Rider", experience_level: "Intermediate" }],
};

const mockHeatmap = {
  total_points: 1500,
  points: [
    { lat: 45.46, lon: 9.19, intensity: 0.8 },
    { lat: 45.47, lon: 9.2, intensity: 0.6 },
  ],
};

describe("HeatmapPanel", () => {
  afterEach(() => {
    apiGet.mockClear();
  });

  it("loads athlete ID on mount", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockHeatmap);
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(apiGet).toHaveBeenCalledWith("/api/v1/athletes");
  });

  it("sets athlete ID correctly", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockHeatmap);
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(wrapper.vm.athleteId).toBe(1);
  });

  it("displays heatmap data when loaded successfully", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockHeatmap);
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(wrapper.vm.heatmapData).toEqual(mockHeatmap);
  });

  it("shows GPS point count when data is loaded", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockHeatmap);
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(wrapper.text()).toContain("1500 GPS points");
    expect(wrapper.vm.heatmapData.points.length).toBeGreaterThan(0);
  });

  it("shows empty state when no GPS data", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce({ total_points: 0, points: [] });
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(wrapper.vm.heatmapData.points.length).toBe(0);
  });

  it("has athlete ID input field", () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(HeatmapPanel);
    expect(wrapper.find("#heatmap-athlete-id").exists()).toBe(true);
  });

  it("renders load button text", () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(HeatmapPanel);
    expect(wrapper.text()).toContain("heatmap.load");
  });

  it("allows manual athlete ID input and triggers heatmap load", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockHeatmap)
      .mockResolvedValueOnce(mockHeatmap);
    const wrapper = mount(HeatmapPanel);
    await flush();
    await wrapper.find("#heatmap-athlete-id").setValue(99);
    await wrapper.find("button").trigger("click");
    const heatmapCalls = apiGet.mock.calls.filter(
      (c) => c[0] === "/api/v1/heatmap",
    );
    const lastHeatmapCall = heatmapCalls[heatmapCalls.length - 1];
    expect(lastHeatmapCall[1]).toEqual({ athlete_id: 99 });
  });

  it("handles athletes API failure gracefully", async () => {
    apiGet.mockRejectedValueOnce(new Error("API error"));
    const wrapper = mount(HeatmapPanel);
    await flush();
    expect(wrapper.find("button").exists()).toBe(true);
  });

  it("no heatmap call when no athletes available", async () => {
    apiGet.mockResolvedValueOnce({ athletes: [] });
    const wrapper = mount(HeatmapPanel);
    await flush();
    const heatmapCalls = apiGet.mock.calls.filter(
      (c) => c[0] === "/api/v1/heatmap",
    );
    expect(heatmapCalls.length).toBe(0);
  });
});
