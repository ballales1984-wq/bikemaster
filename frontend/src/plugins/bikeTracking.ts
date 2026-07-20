/**
 * Capacitor plugin for real-time GPS tracking of cycling rides.
 *
 * Exposes interfaces for starting/stopping/pausing/resuming the recording,
 * permission control and the result structure (GPX, upload, ride ID).
 */

import { registerPlugin } from "@capacitor/core";

export interface StartTrackingOptions {
  outputPath?: string;
  authToken?: string;
  apiBaseUrl?: string;
  rideName?: string;
}

export interface TrackingResult {
  gpxPath: string | null;
  activities?: string;
  uploadStatus?: "success" | "error" | "skipped" | "unknown";
  rideId?: number | null;
}

export interface PermissionsResult {
  granted: boolean;
}

export const BikeTracking = registerPlugin<BikeTrackingApi>("BikeTracking");

export interface BikeTrackingApi {
  startTracking(options?: StartTrackingOptions): Promise<void>;
  stopTracking(): Promise<TrackingResult>;
  pauseTracking(): Promise<void>;
  resumeTracking(): Promise<void>;
  checkPermissions(): Promise<PermissionsResult>;
}
