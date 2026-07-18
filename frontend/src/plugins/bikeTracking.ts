/**
 * Plugin Capacitor per il tracking GPS in tempo reale delle uscite ciclistiche.
 *
 * Espone interfacce per avvio/arresto/pausa/ripresa della registrazione,
 * controllo permessi e struttura del risultato (GPX, upload, ID uscita).
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
