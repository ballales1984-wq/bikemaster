import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "../stores/auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("isLoggedIn reflects token presence", () => {
    const store = useAuthStore();
    expect(store.isLoggedIn).toBe(false);
    store.token = "fake-token";
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
