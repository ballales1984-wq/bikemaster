import { describe, expect, it, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";

vi.mock("./athlete", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./athleteState", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./settings", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./connections", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./apiKeys", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./rides", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./trackingStore", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./ui", () => ({ useUIStore: () => ({ $reset: vi.fn(), setOauthLoading: vi.fn() }) }));
vi.mock("./notifications", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./voiceCommands", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./voiceSystem", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./performance", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./metabolism", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./ble", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./healthConnect", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./itinerary", () => ({ useStore: () => ({ $reset: vi.fn() }) }));
vi.mock("./beck", () => ({ useStore: () => ({ $reset: vi.fn() }) }));

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("isLoggedIn is false initially", () => {
    const store = useAuthStore();
    expect(store.isLoggedIn).toBe(false);
  });

  it("isAdmin is false initially", () => {
    const store = useAuthStore();
    expect(store.isAdmin).toBe(false);
  });

  it("getAuthHeader returns empty object when no token", () => {
    const store = useAuthStore();
    expect(store.getAuthHeader()).toEqual({});
  });

  it("parseJWTPayload handles invalid token", () => {
    const store = useAuthStore();
    expect(store.parseJWTPayload("invalid")).toBe(null);
  });

  it("setAuthFromUrl sets token and user", () => {
    const store = useAuthStore();
    store.setAuthFromUrl("test-token", "test@example.com");
    expect(store.token).toBe("test-token");
    expect(store.user?.username).toBe("test@example.com");
  });

  it("setAuthFromUrl sets justLoggedIn", () => {
    const store = useAuthStore();
    store.setAuthFromUrl("test-token", "test@example.com");
    expect(store.justLoggedIn).toBe(true);
  });

  it("isLoggedIn true when token present", () => {
    const store = useAuthStore();
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isLoggedIn).toBe(true);
  });

  it("getAuthHeader returns bearer when token present", () => {
    const store = useAuthStore();
    store.token = "abc";
    expect(store.getAuthHeader()).toEqual({ Authorization: "Bearer abc" });
  });

  it("parseJWTPayload decodes exp and claims", () => {
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

  it("isTokenValid false when no token", () => {
    const store = useAuthStore();
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid true for future exp", () => {
    const store = useAuthStore();
    const payload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }),
    ).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(true);
  });

  it("isTokenValid false for expired exp", () => {
    const store = useAuthStore();
    const payload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }),
    ).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid true when exp missing", () => {
    const store = useAuthStore();
    const payload = Buffer.from(JSON.stringify({ sub: "u" })).toString(
      "base64url",
    );
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(true);
  });

  it("login stores token and user from response", async () => {
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
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({ access_token: fakeJwt, id: 42, username: "alice" }),
    } as unknown as Response);
    await store.login("alice", "pw");
    expect(store.token).toBe(fakeJwt);
    expect(store.user?.username).toBe("alice");
    expect(store.user?.tenant_id).toBe(42);
    formSpy.mockRestore();
  });

  it("login throws on 401", async () => {
    const store = useAuthStore();
    const formSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Invalid credentials" }),
    } as unknown as Response);
    await expect(store.login("alice", "bad")).rejects.toThrow(
      "Invalid credentials",
    );
    formSpy.mockRestore();
  });

  it("logout clears token and user", async () => {
    const store = useAuthStore();
    store.token = "abc";
    store.user = { id: 1, username: "u", is_admin: false, tenant_id: 1 };
    await store.logout();
    expect(store.token).toBe("");
    expect(store.user).toBe(null);
  });

  it("setJustLoggedIn toggles flag", () => {
    const store = useAuthStore();
    store.setJustLoggedIn(true);
    expect(store.justLoggedIn).toBe(true);
    store.setJustLoggedIn(false);
    expect(store.justLoggedIn).toBe(false);
  });

  it("isTokenValid false for token with malformed payload", () => {
    const store = useAuthStore();
    const payload = Buffer.from("not-json").toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("isTokenValid false at exact exp boundary", () => {
    const store = useAuthStore();
    const exp = Math.floor(Date.now() / 1000);
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    store.token = `h.${payload}.s`;
    expect(store.isTokenValid()).toBe(false);
  });

  it("parseJWTPayload decodes base64url payload with padding omitted", () => {
    const store = useAuthStore();
    const payload = Buffer.from(JSON.stringify({ sub: "x", n: 123 })).toString(
      "base64url",
    );
    const decoded = store.parseJWTPayload(`h.${payload}.s`);
    expect(decoded?.sub).toBe("x");
    expect(decoded?.n).toBe(123);
  });

  it("setOauthError clears token, user and justLoggedIn", () => {
    const store = useAuthStore();
    store.token = "abc";
    store.user = { id: 1, username: "u", is_admin: false, tenant_id: 1 };
    store.setJustLoggedIn(true);
    store.setOauthError("oops");
    expect(store.token).toBe("");
    expect(store.user).toBe(null);
    expect(store.justLoggedIn).toBe(false);
  });

  it("register resolves on success", async () => {
    const store = useAuthStore();
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({ id: 1 }),
    } as unknown as Response);
    await expect(store.register("bob", "secret")).resolves.toBeDefined();
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );
    spy.mockRestore();
  });

  it("register throws on failure", async () => {
    const store = useAuthStore();
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({}),
    } as unknown as Response);
    await expect(store.register("bob", "secret")).rejects.toThrow(
      "Request failed",
    );
    spy.mockRestore();
  });
});
