import { describe, expect, it, vi } from "vitest";

describe("notifications service", () => {
  it("fetchNotifications maps query params", async () => {
    vi.resetModules();
    const mockApiGet = vi.fn().mockResolvedValue({
      notifications: [],
      meta: { language: "it" },
    });
    vi.doMock("../utils/api", () => ({
      apiGet: mockApiGet,
      apiPost: vi.fn(),
    }));

    const { fetchNotifications } = await import("./notifications");
    const res = await fetchNotifications({
      athlete_id: 7,
      category: "recovery",
      planned_today: true,
      tsb: -25,
    });
    expect(res.notifications).toEqual([]);
    expect(mockApiGet).toHaveBeenCalledWith(
      "/api/v1/notifications",
      expect.objectContaining({
        athlete_id: "7",
        category: "recovery",
        planned_today: "1",
        tsb: "-25",
      }),
    );
  });

  it("updateNotificationPreferences posts body", async () => {
    vi.resetModules();
    const mockApiPost = vi.fn().mockResolvedValue({
      athlete_id: 1,
      preferences: {},
      message: "ok",
    });
    vi.doMock("../utils/api", () => ({
      apiGet: vi.fn(),
      apiPost: mockApiPost,
    }));

    const { updateNotificationPreferences, DEFAULT_NOTIFICATION_PREFERENCES } =
      await import("./notifications");
    await updateNotificationPreferences(DEFAULT_NOTIFICATION_PREFERENCES, 1);
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/v1/notifications/preferences?athlete_id=1",
      DEFAULT_NOTIFICATION_PREFERENCES,
    );
  });

  it("evaluateNotification posts context with category", async () => {
    vi.resetModules();
    const mockApiPost = vi.fn().mockResolvedValue({
      urgency: 5,
      relevance: 4,
      timeliness: 5,
      score: 4.67,
      should_notify: true,
      reasons: [],
    });
    vi.doMock("../utils/api", () => ({
      apiGet: vi.fn(),
      apiPost: mockApiPost,
    }));

    const { evaluateNotification } = await import("./notifications");
    const score = await evaluateNotification(
      { athlete_state: { tsb: -25 }, intensity_zone: 2 },
      "recovery",
    );
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/v1/notifications/evaluate?category=recovery",
      { athlete_state: { tsb: -25 }, intensity_zone: 2 },
    );
    expect(score.should_notify).toBe(true);
    expect(score.score).toBeCloseTo(4.67, 1);
  });
});
