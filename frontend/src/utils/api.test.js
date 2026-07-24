import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { apiDelete, apiGet, apiPost, apiPut, apiUpload } from "./api";
import { useAuthStore } from "../stores/auth";

describe("api helpers", () => {
  let origFetch;

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    if (origFetch) globalThis.fetch = origFetch;
    else delete globalThis.fetch;
  });

  it("apiGet sends query params", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        headers: { get: () => "application/json" },
        json: async () => ({ ok: true }),
      });
    const result = await apiGet("/api/v1/rides", { q: "1" });
    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/rides?q=1",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer tok" }),
      }),
    );
  });

  it("apiGet throws on 401 and clears auth", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "expired" }),
    });
    await expect(apiGet("/api/v1/x")).rejects.toThrow();
    expect(auth.token).toBe("");
    expect(auth.isLoggedIn).toBe(false);
  });

  it("apiGet returns null body on parse error", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => {
        throw new Error("parse");
      },
    });
    await expect(apiGet("/api/v1/x")).rejects.toThrow("Request failed");
  });

  it("apiPost calls POST with body", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: 1 }) });
    await apiPost("/api/v1/rides", { date: "2026" });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/rides",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ date: "2026" }),
      }),
    );
  });

  it("apiPut calls PUT with body", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ ok: true }),
    });
    await apiPut("/api/v1/rides/1", { distance_km: 50 });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/rides/1",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ distance_km: 50 }),
      }),
    );
  });

  it("apiDelete calls DELETE", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
    await apiDelete("/api/v1/rides/1");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/rides/1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("apiPost throws non-ok with detail", async () => {
    const auth = useAuthStore();
    auth.token = "tok";
    origFetch = globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Server error" }),
    });
    await expect(apiPost("/api/v1/rides", {})).rejects.toThrow("Server error");
  });
});
