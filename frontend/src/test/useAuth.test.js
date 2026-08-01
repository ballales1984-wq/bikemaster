import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "../stores/auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    sessionStorage.clear();
  });

  it("isLoggedIn reflects token presence", () => {
    const store = useAuthStore();
    expect(store.isLoggedIn).toBe(false);
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isLoggedIn).toBe(true);
  });

  it("getAuthHeader returns empty object when no token", () => {
    const store = useAuthStore();
    expect(store.getAuthHeader()).toEqual({});
    store.token = "fake-token";
    expect(store.getAuthHeader()).toEqual({
      Authorization: "Bearer fake-token",
    });
  });

  it("parseJWTPayload handles invalid token", () => {
    const store = useAuthStore();
    expect(store.parseJWTPayload("invalid")).toBe(null);
    expect(store.parseJWTPayload("a.b.c")).toBe(null);
  });
});
