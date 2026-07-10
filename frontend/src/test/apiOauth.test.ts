import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiGet } from "../utils/api";
import { useAuthStore } from "../stores/auth";
import { setActivePinia, createPinia } from "pinia";

function makeFetch(status: number, body: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })) as unknown as typeof fetch;
}

describe("api 401 handling (OAuth return safety)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("clears the session on a normal 401", async () => {
    const auth = useAuthStore();
    auth.token = "valid.jwt.token";
    localStorage.setItem("bikemaster_token", "valid.jwt.token");
    (globalThis as unknown as { fetch: typeof fetch }).fetch = makeFetch(401, {
      detail: "expired",
    });

    await expect(
      apiGet("/api/v1/auth/me", {}, { headers: { Authorization: "Bearer x" } }),
    ).rejects.toThrow();

    expect(localStorage.getItem("bikemaster_token")).toBeNull();
    expect(auth.isLoggedIn).toBe(false);
  });

  it("keeps the session on a 401 when suppressAuthClear is set", async () => {
    const auth = useAuthStore();
    auth.token = "valid.jwt.token";
    localStorage.setItem("bikemaster_token", "valid.jwt.token");
    (globalThis as unknown as { fetch: typeof fetch }).fetch = makeFetch(401, {
      detail: "expired",
    });

    await expect(
      apiGet("/api/v1/auth/me", {}, {
        headers: { Authorization: "Bearer x" },
        suppressAuthClear: true,
      } as RequestInit),
    ).rejects.toThrow();

    // Session must survive so the OAuth return still reaches the dashboard
    // instead of being bounced to the login screen.
    expect(localStorage.getItem("bikemaster_token")).toBe("valid.jwt.token");
    expect(auth.isLoggedIn).toBe(true);
  });
});
