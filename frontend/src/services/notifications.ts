/**
 * Service for managing the application's notifications.
 *
 * Provides functions to fetch the notification list with filters
 * (category, intensity zone, active goals, weather), update
 * the notification preferences and evaluate the relevance score of a
 * notification based on the provided context.
 *
 * Exports: DEFAULT_NOTIFICATION_PREFERENCES, fetchNotifications,
 *           updateNotificationPreferences, evaluateNotification
 */

import { apiGet, apiPost } from "../utils/api";
import type {
  NotificationContextInput,
  NotificationList,
  NotificationPreferences,
  NotificationScore,
} from "../types/notifications";

export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  language: "it",
  quiet_hours_start: 23,
  quiet_hours_end: 7,
  max_background_per_ride: 2,
  allow_voice_coach: true,
  allow_email_summary: true,
  paused: false,
  channel_priority: ["app", "voice", "dashboard", "email"],
  respect_quiet_hours: true,
};

export async function fetchNotifications(
  params: {
    athlete_id?: number;
    category?: string;
    intensity_zone?: number;
    planned_today?: boolean;
    goal_active?: boolean;
    weather_changed?: boolean;
    tsb?: number;
    stopped_min?: number;
    rides_left?: number;
  } = {},
): Promise<NotificationList> {
  const qs: Record<string, string> = {};
  if (params.athlete_id) qs.athlete_id = String(params.athlete_id);
  if (params.category) qs.category = params.category;
  if (params.intensity_zone !== undefined)
    qs.intensity_zone = String(params.intensity_zone);
  if (params.planned_today) qs.planned_today = "1";
  if (params.goal_active) qs.goal_active = "1";
  if (params.weather_changed) qs.weather_changed = "1";
  if (params.tsb !== undefined) qs.tsb = String(params.tsb);
  if (params.stopped_min !== undefined)
    qs.stopped_min = String(params.stopped_min);
  if (params.rides_left !== undefined)
    qs.rides_left = String(params.rides_left);
  return apiGet<NotificationList>("/api/v1/notifications", qs);
}

export async function updateNotificationPreferences(
  prefs: NotificationPreferences,
  athlete_id?: number,
): Promise<{
  athlete_id: number;
  preferences: NotificationPreferences;
  message: string;
}> {
  const path =
    athlete_id != null
      ? `/api/v1/notifications/preferences?athlete_id=${athlete_id}`
      : "/api/v1/notifications/preferences";
  return apiPost<{
    athlete_id: number;
    preferences: NotificationPreferences;
    message: string;
  }>(path, prefs);
}

export async function evaluateNotification(
  context: NotificationContextInput,
  category: string,
): Promise<NotificationScore> {
  return apiPost<NotificationScore>(
    `/api/v1/notifications/evaluate?category=${encodeURIComponent(category)}`,
    context,
  );
}
