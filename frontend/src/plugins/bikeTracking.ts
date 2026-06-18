import { registerPlugin } from '@capacitor/core'

export interface TrackingResult {
  gpxPath: string | null
}

export interface PermissionsResult {
  granted: boolean
}

export const BikeTracking = registerPlugin<BikeTrackingApi>('BikeTracking')

export interface BikeTrackingApi {
  startTracking(): Promise<void>
  stopTracking(): Promise<TrackingResult>
  pauseTracking(): Promise<void>
  resumeTracking(): Promise<void>
  checkPermissions(): Promise<PermissionsResult>
}