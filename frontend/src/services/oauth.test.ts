import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";
import { processOAuthToken, hasPendingOAuth } from "./oauth";

export function makeFakeJwt(
  email: string,
  userId: number,
  exp: number = 1893456000,
) {
  const payload = JSON.stringify({
    exp,
    sub: String(userId),
    email,
    user_id: userId,
  });
  const base64 = Buffer.from(payload).toString("base64url");
  return `h.${base64}.s`;
}

function setUrl(href: string) {
  window.history.replaceState({}, "", href);
}

describe("processOAuthToken — duplicate-call benign scenario", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  let logs: string[];

  beforeEach(() => {
    sessionStorage.clear();
    consoleSpy = vi.spyOn(console, "log").mockImplementation((...args) => {
      logs.push(args.join(" "));
    });
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    vi.restoreAllMocks();
  });

  it("main.ts consumes token → guard skips redundant call (no spurious log)", () => {
    setActivePinia(createPinia());
    logs = [];
    const auth = useAuthStore();
    const ui = useUIStore();

    // Simulate OAuth return: token in URL fragment, full page load
    const jwt = makeFakeJwt("user@example.com", 1);
    setUrl(`/#token=${jwt}&email=user@example.com&user_id=1`);

    // --- main.ts:37 — first call (bootstrap) ---
    const tokenProcessed = processOAuthToken();

    // Assert token was consumed
    expect(tokenProcessed).toBe(true);
    const consumedLog = logs.find((l) => l.includes("token consumed from URL"));
    expect(consumedLog).toBeDefined();
    expect(consumedLog).toContain("user@example.com");

    // URL should be cleaned
    expect(window.location.hash).toBe("");
    expect(window.location.search).toBe("");

    // sessionStorage pending should be cleared
    expect(hasPendingOAuth()).toBe(false);

    // Auth state should be set
    expect(auth.isLoggedIn).toBe(true);
    expect(auth.token).toBe(jwt);
    expect(auth.justLoggedIn).toBe(true);

    // oauthLoading should be cleared
    expect(ui.oauthLoading).toBe(false);

    logs = [];

    // --- router/index.ts guard — with the fix: `if (!auth.isLoggedIn)` ---
    if (!auth.isLoggedIn) {
      processOAuthToken();
    }

    // Assert: the guard was SKIPPED (auth.isLoggedIn is true)
    // No "no token found" log should appear
    const noTokenLog = logs.find((l) => l.includes("no token found"));
    expect(noTokenLog).toBeUndefined();
    expect(logs).toHaveLength(0);
  });

  it("without fix (unconditional call) guard would log 'no token found'", () => {
    setActivePinia(createPinia());
    logs = [];
    const auth = useAuthStore();

    // Simulate OAuth return
    const jwt = makeFakeJwt("user@example.com", 1);
    setUrl(`/#token=${jwt}&email=user@example.com&user_id=1`);

    // --- main.ts:37 ---
    processOAuthToken();
    expect(auth.isLoggedIn).toBe(true);

    logs = [];

    // --- OLD guard behavior: unconditional call ---
    processOAuthToken();

    // This WOULD produce the spurious log
    const noTokenLog = logs.find((l) => l.includes("no token found"));
    expect(noTokenLog).toBeDefined();
  });

  it("unauthenticated user (no token anywhere) — guard still calls processOAuthToken", () => {
    setActivePinia(createPinia());
    logs = [];
    const auth = useAuthStore();

    setUrl("/");

    // Main.ts:37 — no token
    const tokenProcessed = processOAuthToken();
    expect(tokenProcessed).toBe(false);

    logs = [];

    // Guard — auth is NOT logged in, so call processOAuthToken()
    if (!auth.isLoggedIn) {
      processOAuthToken();
    }

    // "no token found" is expected for an unauthenticated user
    const noTokenLog = logs.find((l) => l.includes("no token found"));
    expect(noTokenLog).toBeDefined();
  });

  it("sessionStorage recovery path works (reload mid-round-trip)", () => {
    setActivePinia(createPinia());
    logs = [];
    const auth = useAuthStore();

    // Simulate a mid-round-trip reload: token stashed in sessionStorage
    // before main.ts had a chance to consume it from the URL.
    // processOAuthToken already called in a previous (crashed) load →
    // persistPendingOAuth ran but clearPendingOAuth didn't.
    // We simulate by manually stashing:
    const jwt = makeFakeJwt("test@example.com", 42);
    setUrl("/"); // URL has NO token (already cleaned)

    // Manually stash pending OAuth (simulating interrupted previous load)
    sessionStorage.setItem(
      "bikemaster_oauth_pending",
      JSON.stringify({ token: jwt, email: "test@example.com", userId: "42" }),
    );

    expect(hasPendingOAuth()).toBe(true);

    // processOAuthToken should recover from sessionStorage
    const tokenProcessed = processOAuthToken();
    expect(tokenProcessed).toBe(true);

    const recoveredLog = logs.find((l) =>
      l.includes("token recovered from sessionStorage"),
    );
    expect(recoveredLog).toBeDefined();
    expect(auth.isLoggedIn).toBe(true);
    expect(auth.token).toBe(jwt);
    expect(hasPendingOAuth()).toBe(false);
  });
});
