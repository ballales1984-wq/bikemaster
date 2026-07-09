import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it("isLoggedIn is false initially", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    expect(store.isLoggedIn).toBe(false);
  });

  it("isAdmin is false initially", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    expect(store.isAdmin).toBe(false);
  });

  it("getAuthHeader returns empty object when no token", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    expect(store.getAuthHeader()).toEqual({});
  });

  it("parseJWTPayload handles invalid token", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    expect(store.parseJWTPayload("invalid")).toBe(null);
  });

  it("setAuthFromUrl sets token and user", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.setAuthFromUrl("test-token", "test@example.com");
    expect(store.token).toBe("test-token");
    expect(store.user?.username).toBe("test@example.com");
  });

  it("setAuthFromUrl sets justLoggedIn and localStorage flag", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.setAuthFromUrl("test-token", "test@example.com");
    expect(store.justLoggedIn).toBe(true);
    expect(localStorage.getItem("bikemaster_just_logged_in")).toBe("true");
  });

  it("isLoggedIn true when token present", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.token = "abc";
    expect(store.isLoggedIn).toBe(true);
  });

  it("getAuthHeader returns bearer when token present", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.token = "abc";
    expect(store.getAuthHeader()).toEqual({ Authorization: "Bearer abc" });
  });

  it("parseJWTPayload decodes exp and claims", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const header = Buffer.from(
      JSON.stringify({ alg: "HS256", typ: "JWT" }),
    ).toString("base64url");
    const payload = Buffer.from(
      JSON.stringify({
        sub: "user1",
        tenant_id: 7,
        is_admin: true,
        exp: 9999999999,
      }),
    ).toString("base64url");
    const token = `${header}.${payload}.sig`;
    const decoded = store.parseJWTPayload(token);
    expect(decoded?.sub).toBe("user1");
    expect(decoded?.tenant_id).toBe(7);
    expect(decoded?.is_admin).toBe(true);
  });

  it("isTokenValid false when no token", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid true for future exp", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const payload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }),
    ).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(true);
  });

  it("isTokenValid false for expired exp", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const payload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }),
    ).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid true when exp missing", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const payload = Buffer.from(JSON.stringify({ sub: "u" })).toString(
      "base64url",
    );
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(true);
  });

  it("login stores token and user from response", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const header = Buffer.from(
      JSON.stringify({ alg: "HS256", typ: "JWT" }),
    ).toString("base64url");
    const payload = Buffer.from(
      JSON.stringify({ sub: "alice", tenant_id: 42, is_admin: false }),
    ).toString("base64url");
    const fakeJwt = `${header}.${payload}.sig`;
    const formSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: fakeJwt, id: 42 }),
    } as Response);
    await store.login("alice", "pw");
    expect(store.token).toBe(fakeJwt);
    expect(store.user?.username).toBe("alice");
    expect(store.user?.tenant_id).toBe(42);
    expect(localStorage.getItem("bikemaster_token")).toBe(fakeJwt);
    formSpy.mockRestore();
  });

  it("login throws on 401", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const formSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Invalid credentials" }),
    } as Response);
    await expect(store.login("alice", "bad")).rejects.toThrow(
      "Invalid credentials",
    );
    formSpy.mockRestore();
  });

  it("logout clears token, user and localStorage", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.token = "abc";
    store.user = { id: 1, username: "u", is_admin: false, tenant_id: 1 };
    localStorage.setItem("bikemaster_token", "abc");
    await store.logout();
    expect(store.token).toBe("");
    expect(store.user).toBe(null);
    expect(localStorage.getItem("bikemaster_token")).toBe(null);
  });

  it("setJustLoggedIn toggles localStorage flag", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.setJustLoggedIn(true);
    expect(store.justLoggedIn).toBe(true);
    expect(localStorage.getItem("bikemaster_just_logged_in")).toBe("true");
    store.setJustLoggedIn(false);
    expect(store.justLoggedIn).toBe(false);
    expect(localStorage.getItem("bikemaster_just_logged_in")).toBe(null);
  });

  it("isTokenValid false for token with malformed payload", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const payload = Buffer.from("not-json").toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid false at exact exp boundary", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const exp = Math.floor(Date.now() / 1000);
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("parseJWTPayload decodes base64url payload with padding omitted", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const payload = Buffer.from(JSON.stringify({ sub: "x", n: 123 })).toString(
      "base64url",
    );
    const decoded = store.parseJWTPayload(`h.${payload}.s`);
    expect(decoded?.sub).toBe("x");
    expect(decoded?.n).toBe(123);
  });

  it("setOauthError clears token, user and justLoggedIn", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    store.token = "abc";
    store.user = { id: 1, username: "u", is_admin: false, tenant_id: 1 };
    store.setJustLoggedIn(true);
    localStorage.setItem("bikemaster_token", "abc");
    store.setOauthError("oops");
    expect(store.token).toBe("");
    expect(store.user).toBe(null);
    expect(store.justLoggedIn).toBe(false);
    expect(localStorage.getItem("bikemaster_token")).toBe(null);
    expect(localStorage.getItem("bikemaster_login_error")).toBe("oops");
  });

  it("register resolves on success", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1 }),
    } as Response);
    await expect(store.register("bob", "secret")).resolves.toBeDefined();
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );
    spy.mockRestore();
  });

  it("register throws on failure", async () => {
    const { useAuthStore } = await import("./auth");
    const store = useAuthStore();
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({}),
    } as Response);
    await expect(store.register("bob", "secret")).rejects.toThrow(
      "Registration failed",
    );
    spy.mockRestore();
  });
});
