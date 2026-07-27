/** Tipi per il Proactive Assistant (notifiche, contesto, voice coach). */

export type NotificationChannel = "app" | "voice" | "dashboard" | "email";

export type NotificationCategory =
  "training" | "recovery" | "performance" | "safety" | "goal" | "batch";

export interface NotificationScore {
  urgency: number;
  relevance: number;
  timeliness: number;
  score: number;
  should_notify: boolean;
  reasons: string[];
}

export interface Notification {
  id: string;
  category: NotificationCategory;
  channel: NotificationChannel;
  title: string;
  message: string;
  tts_text?: string | null;
  score: number;
  priority: number;
  language: string;
  created_at?: string | null;
}

export interface NotificationList {
  notifications: Notification[];
  meta: Record<string, unknown>;
}

export interface NotificationPreferences {
  language: "it" | "en";
  quiet_hours_start: number;
  quiet_hours_end: number;
  max_background_per_ride: number;
  allow_voice_coach: boolean;
  allow_email_summary: boolean;
  paused: boolean;
  channel_priority: NotificationChannel[];
  respect_quiet_hours: boolean;
}

export interface NotificationContextInput {
  athlete_state?: Record<string, unknown>;
  plan?: Record<string, unknown> | null;
  current_ride?: Record<string, unknown> | null;
  weather?: Record<string, unknown> | null;
  now?: string | null;
  intensity_zone?: number | null;
}

export type VoiceCommand = "stop" | "pause" | "resume" | "status" | "unknown";

export interface ParsedVoiceCommand {
  command: VoiceCommand;
  raw: string;
  language: string;
}
