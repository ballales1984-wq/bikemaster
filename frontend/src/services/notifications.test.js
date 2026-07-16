import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

class MemStore {
  constructor() {
    this.s = new Map();
  }
  getItem(k) {
    return this.s.has(k) ? this.s.get(k) : null;
  }
  setItem(k, v) {
    this.s.set(k, String(v));
  }
  removeItem(k) {
    this.s.delete(k);
  }
}

describe("notifications service", () => {
  let store;

  beforeEach(() => {
    store = new MemStore();
    globalThis.localStorage = store;
    globalThis.window = {
      location: { href: "" },
      speechSynthesis: undefined,
    };
  });

  afterEach(() => {
    if (globalThis.fetch) delete globalThis.fetch;
    delete globalThis.window;
    delete globalThis.localStorage;
  });

  it("fetchNotifications maps query params", async () => {
    const captured = [];
    globalThis.fetch = vi.fn(async (url, init) => {
      captured.push({ url, init });
      return new Response(
        JSON.stringify({ notifications: [], meta: { language: "it" } }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    const { fetchNotifications } = await import("./notifications");
    const res = await fetchNotifications({
      athlete_id: 7,
      category: "recovery",
      planned_today: true,
      tsb: -25,
    });
    expect(res.notifications).toEqual([]);
    const url = captured[0].url;
    expect(url).toContain("athlete_id=7");
    expect(url).toContain("category=recovery");
    expect(url).toContain("planned_today=1");
    expect(url).toContain("tsb=-25");
  });

  it("updateNotificationPreferences posts body", async () => {
    let body = null;
    let url = "";
    globalThis.fetch = vi.fn(async (u, init) => {
      url = u;
      body = init.body;
      return new Response(
        JSON.stringify({ athlete_id: 1, preferences: {}, message: "ok" }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    const { updateNotificationPreferences, DEFAULT_NOTIFICATION_PREFERENCES } =
      await import("./notifications");
    await updateNotificationPreferences(DEFAULT_NOTIFICATION_PREFERENCES, 1);
    expect(url).toContain("athlete_id=1");
    expect(JSON.parse(body).language).toBe("it");
  });

  it("evaluateNotification posts context with category", async () => {
    let url = "";
    let body = null;
    globalThis.fetch = vi.fn(async (u, init) => {
      url = u;
      body = init.body;
      return new Response(
        JSON.stringify({
          urgency: 5,
          relevance: 4,
          timeliness: 5,
          score: 4.67,
          should_notify: true,
          reasons: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    const { evaluateNotification } = await import("./notifications");
    const score = await evaluateNotification(
      { athlete_state: { tsb: -25 }, intensity_zone: 2 },
      "recovery",
    );
    expect(url).toContain("category=recovery");
    expect(score.should_notify).toBe(true);
    expect(JSON.parse(body).intensity_zone).toBe(2);
  });
});
