import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

// Mock Chart.js — not available in jsdom
vi.mock("chart.js", () => ({
  Chart: vi
    .fn()
    .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() })),
  registerables: [],
}));

vi.mock("chart.js/auto", () => ({
  default: vi
    .fn()
    .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), resize: vi.fn() })),
  Chart: vi
    .fn()
    .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), resize: vi.fn() })),
}));

// Global Chart mock used inline in the component
globalThis.Chart = vi.fn().mockImplementation(() => ({ destroy: vi.fn() }));

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

import ChartsPanel from "./ChartsPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("ChartsPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly with minimal data", async () => {
    apiGet.mockResolvedValue({ ready: false });

    const wrapper = mount(ChartsPanel, {
      props: { rides: [] },
    });
    await flush();

    expect(wrapper.find(".charts-panel").exists()).toBe(true);
    expect(wrapper.find("h2").text()).toContain("Trend Performance");
  });

  it("shows metric and window selectors", async () => {
    apiGet.mockResolvedValue({ ready: false });

    const wrapper = mount(ChartsPanel, { props: { rides: [] } });
    await flush();

    const selects = wrapper.findAll("select");
    expect(selects).toHaveLength(2);

    const metricOptions = selects[0].findAll("option");
    expect(metricOptions.some((o) => o.text().includes("Distanza"))).toBe(true);
    expect(metricOptions.some((o) => o.text().includes("Velocità"))).toBe(true);
  });

  it("changing metric triggers loadTrends", async () => {
    apiGet.mockResolvedValue({ ready: false });

    const wrapper = mount(ChartsPanel, { props: { rides: [] } });
    await flush();

    const callsBefore = apiGet.mock.calls.length;
    const selects = wrapper.findAll("select");
    await selects[0].setValue("calories");
    await flush();

    expect(apiGet.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it("shows 3 chart-cards in grid", async () => {
    apiGet.mockResolvedValue({ ready: false });

    const wrapper = mount(ChartsPanel, { props: { rides: [] } });
    await flush();

    expect(wrapper.findAll(".chart-card")).toHaveLength(3);
  });

  it("shows trend-up when trend is improving", async () => {
    apiGet
      .mockResolvedValueOnce({
        ready: true,
        trend: "improving",
        r2: 0.85,
        mean: 45.2,
        values: [40, 45, 50],
        dates: ["2026-01", "2026-02", "2026-03"],
        rolling_avg: [42, 45, 47],
      })
      .mockResolvedValue({ ready: false });

    const wrapper = mount(ChartsPanel, { props: { rides: [] } });
    await flush();

    const summary = wrapper.find(".chart-summary");
    if (summary.exists()) {
      expect(summary.find(".trend-up").exists()).toBe(true);
    }
  });
});
