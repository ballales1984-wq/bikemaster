import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockApiGet = vi.hoisted(() => vi.fn());
vi.mock("./notifications", async () => {
  const actual = await vi.importActual("./notifications");
  return {
    ...actual,
    fetchNotifications: vi.fn(),
  };
});

describe("notifications service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchNotifications maps query params", async () => {
    const { fetchNotifications } = await import("./notifications");
    fetchNotifications.mockResolvedValue({
      notifications: [],
      meta: { language: "it" },
    });
    const res = await fetchNotifications({
      athlete_id: 7,
      category: "recovery",
      planned_today: true,
      tsb: -25,
    });
    expect(res.notifications).toEqual([]);
    expect(fetchNotifications).toHaveBeenCalledWith({
      athlete_id: 7,
      category: "recovery",
      planned_today: true,
      tsb: -25,
    });
  });

  it("updateNotificationPreferences posts body", async () => {
    const { updateNotificationPreferences, DEFAULT_NOTIFICATION_PREFERENCES } =
      await import("./notifications");
    const mockApiPost = vi.fn().mockResolvedValue({
      athlete_id: 1,
      preferences: {},
      message: "ok",
    });
    vi.mock("../utils/api", () => ({
      apiPost: mockApiPost,
    }));
    await updateNotificationPreferences(DEFAULT_NOTIFICATION_PREFERENCES, 1);
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/v1/notifications/preferences?athlete_id=1",
      DEFAULT_NOTIFICATION_PREFERENCES,
    );
  });

  it("evaluateNotification posts context with category", async () => {
    const { evaluateNotification } = await import("./notifications");
    const mockApiPost = vi.fn().mockResolvedValue({
      urgency: 5,
      relevance: 4,
      timeliness: 5,
      score: 4.67,
      should_notify: true,
      reasons: [],
    });
    vi.mock("../utils/api", () => ({
      apiPost: mockApiPost,
    }));
    const score = await evaluateNotification(
      { athlete_state: { tsb: -25 }, intensity_zone: 2 },
      "recovery",
    );
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/v1/notifications/evaluate?category=recovery",
      { athlete_state: { tsb: -25 }, intensity_zone: 2 },
    );
    expect(score.should_notify).toBe(true);
    expect(score.intensity_zone).toBe(2);
  });
});
