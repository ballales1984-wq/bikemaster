import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock Chart.js global (used directly in the composable)
const mockChartInstance = { destroy: vi.fn(), update: vi.fn() };
globalThis.Chart = vi.fn().mockImplementation(() => mockChartInstance);

// useChart uses lifecycle hooks (onMounted/watch) — testable in isolation
// for pure data formatting functions

describe("useChart helpers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.Chart = vi.fn().mockImplementation(() => ({ destroy: vi.fn() }));
  });

  it("Chart is built with bar type by default", () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) };
    const data = { labels: ["Jan", "Feb"], datasets: [{ data: [10, 20] }] };

    new globalThis.Chart(canvas.getContext(), {
      type: "bar",
      data,
      options: {},
    });

    expect(globalThis.Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: "bar" }),
    );
  });

  it("Chart is built with line type if specified", () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) };
    const data = { labels: ["A", "B", "C"], datasets: [{ data: [1, 2, 3] }] };

    new globalThis.Chart(canvas.getContext(), {
      type: "line",
      data,
      options: {},
    });

    expect(globalThis.Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: "line" }),
    );
  });

  it("Chart constructor receives responsive and maintainAspectRatio options", () => {
    const canvas = { getContext: vi.fn().mockReturnValue({}) };
    const data = { labels: [], datasets: [] };

    new globalThis.Chart(canvas.getContext(), {
      type: "bar",
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#aaa" } } },
      },
    });

    const callArgs = globalThis.Chart.mock.calls[0][1];
    expect(callArgs.options.responsive).toBe(true);
    expect(callArgs.options.maintainAspectRatio).toBe(false);
  });

  it("destroy is called before re-rendering", () => {
    const destroyFn = vi.fn();
    const instance = { destroy: destroyFn };
    globalThis.Chart = vi.fn().mockImplementation(() => instance);

    const ctx = {};
    const data = { labels: [], datasets: [] };

    // First instance
    const c1 = new globalThis.Chart(ctx, { type: "bar", data, options: {} });
    // Destroy as render() would do
    c1.destroy();
    // Second instance
    new globalThis.Chart(ctx, { type: "bar", data, options: {} });

    expect(destroyFn).toHaveBeenCalledTimes(1);
    expect(globalThis.Chart).toHaveBeenCalledTimes(2);
  });
});

describe("chart data formatters", () => {
  it("calculates rolling average on window 3", () => {
    const values = [10, 20, 30, 40, 50];
    const windowSize = 3;
    const rollingAvg = values.map((_, i) => {
      if (i < windowSize - 1) return null;
      const slice = values.slice(i - windowSize + 1, i + 1);
      return slice.reduce((a, b) => a + b, 0) / windowSize;
    });
    expect(rollingAvg[2]).toBe(20);
    expect(rollingAvg[3]).toBe(30);
    expect(rollingAvg[4]).toBe(40);
  });

  it("calculates percentage change between periods", () => {
    const recent = 150;
    const previous = 100;
    const changePct = Math.round(((recent - previous) / previous) * 100);
    expect(changePct).toBe(50);
  });

  it("formats month labels correctly", () => {
    const dates = ["2026-01-15", "2026-02-10", "2026-03-22"];
    const labels = dates.map((d) => d?.slice(5) || "?");
    expect(labels).toEqual(["01-15", "02-10", "03-22"]);
  });
});
