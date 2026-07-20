import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

const mockAuth = vi.hoisted(() => ({
  isLoggedIn: true,
  token: "fake-token",
  getAuthHeader: () => ({ Authorization: "Bearer fake-token" }),
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => mockAuth,
}));

function jsonResponse(body) {
  return {
    ok: true,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => body,
  };
}

describe("usePerformanceStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ athlete_id: 1, metrics: [], history: [], latest_ftp: null }),
    );
  });

  afterEach(() => {
    delete globalThis.fetch;
  });

  it("fetchFtpHistory populates latestFtp and history", async () => {
    const { usePerformanceStore } = await import("../stores/performance.ts");

    globalThis.fetch.mockResolvedValueOnce(
      jsonResponse({
        athlete_id: 1,
        latest_ftp: 250,
        history: [{ id: 1, athlete_id: 1, date: "2026-07-01", ftp_watts: 250 }],
      }),
    );

    const store = usePerformanceStore();
    const data = await store.fetchFtpHistory();
    expect(data?.latest_ftp).toBe(250);
    expect(store.latestFtp).toBe(250);
    expect(store.ftpHistory.length).toBe(1);
  });

  it("recordFtp upserts by date and updates latest", async () => {
    const { usePerformanceStore } = await import("../stores/performance.ts");
    globalThis.fetch
      .mockResolvedValueOnce(
        jsonResponse({ athlete_id: 1, latest_ftp: 230, history: [] }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: 2,
          athlete_id: 1,
          date: "2026-07-02",
          ftp_watts: 245,
          source: "test",
        }),
      );

    const store = usePerformanceStore();
    await store.fetchFtpHistory();
    const rec = await store.recordFtp({ ftp_watts: 245, date: "2026-07-02" });
    expect(rec.ftp_watts).toBe(245);
    expect(store.latestFtp).toBe(245);
  });

  it("fetchMetrics returns persisted metrics", async () => {
    const { usePerformanceStore } = await import("../stores/performance.ts");
    globalThis.fetch.mockResolvedValueOnce(
      jsonResponse({
        athlete_id: 1,
        metrics: [
          {
            id: 1,
            athlete_id: 1,
            ride_id: 5,
            date: "2026-07-01",
            average_power: 150,
            normalized_power: 172,
            intensity_factor: 0.688,
            tss: 7.9,
            ftp_watts: 250,
          },
        ],
      }),
    );

    const store = usePerformanceStore();
    const rows = await store.fetchMetrics();
    expect(rows.length).toBe(1);
    expect(rows[0].normalized_power).toBe(172);
    expect(store.hasData).toBe(true);
  });

  it("computeFromStream returns power metrics", async () => {
    const { usePerformanceStore } = await import("../stores/performance.ts");
    globalThis.fetch.mockResolvedValueOnce(
      jsonResponse({
        average_power: 150,
        normalized_power: 172,
        intensity_factor: null,
        tss: null,
      }),
    );

    const store = usePerformanceStore();
    const res = await store.computeFromStream({
      power_stream: [200, 200, 100, 100],
      duration_seconds: 600,
    });
    expect(res.normalized_power).toBe(172);
    expect(res.intensity_factor).toBeNull();
  });
});
