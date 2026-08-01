import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

import { useConnectionsStore } from "../stores/connections";
import { useAuthStore } from "../stores/auth";

describe("useConnectionsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("starts empty and exposes known services after load", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const store = useConnectionsStore();
    await store.load();

    expect(store.items.length).toBe(5);
    expect(store.items.map((s) => s.service)).toEqual([
      "strava",
      "google_fit",
      "google_health",
      "wahoo",
      "garmin",
    ]);
  });

  it("marks services returned by backend as connected", async () => {
    apiGet.mockResolvedValue({
      connections: [
        { service: "strava", method: "oauth", connected: true, label: "Strava" },
      ],
    });
    const store = useConnectionsStore();
    await store.load();

    const strava = store.items.find((s) => s.service === "strava");
    expect(strava.connected).toBe(true);
    expect(store.connectedServices).toContain(strava);
  });

  it("sets error when backend request fails", async () => {
    apiGet.mockRejectedValue(new Error("boom"));
    const store = useConnectionsStore();
    await store.load();

    expect(store.error).toBe("boom");
    expect(store.items.length).toBe(0);
  });

  it("disconnect calls the backend endpoint with auth header", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const auth = useAuthStore();
    auth.token = "fake-token";

    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue({ ok: true, json: async () => ({}) });

    const store = useConnectionsStore();
    await store.load();
    await store.disconnect("strava");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/import/strava/disconnect",
      expect.objectContaining({ method: "DELETE" }),
    );
    const init = fetchSpy.mock.calls[0][1];
    expect(init.headers).toEqual({ Authorization: "Bearer fake-token" });
    fetchSpy.mockRestore();
  });

  it("disconnect sets error when response is not ok", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "nope" }),
    });

    const store = useConnectionsStore();
    await store.load();
    await store.disconnect("wahoo");

    expect(store.error).toBe("nope");
    fetchSpy.mockRestore();
  });
});
