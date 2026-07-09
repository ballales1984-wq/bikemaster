import { registerPlugin } from '@capacitor/core'

export interface TrackingResult {
  gpxPath: string | null
}

export interface PermissionsResult {
  granted: boolean
  fineLocation: boolean
  backgroundLocation: boolean
}

export interface TrackingStateEvent {
  distance: number
  currentSpeed: number
  avgSpeed: number
  elapsedTime: number
  elevation: number
  points: number
  isPaused: boolean
  lastLatitude: number | null
  lastLongitude: number | null
  heartRate: number | null
  cadence: number | null
  power: number | null
}

export interface TrackingStoppedEvent {
  gpxPath: string | null
  error: string | null
}

export interface ReadGpxResult {
  base64: string
}

export const BikeTracking = registerPlugin<{
  startTracking(options?: { outputPath?: string }): Promise<void>
  stopTracking(): Promise<void>
  pauseTracking(): Promise<void>
  resumeTracking(): Promise<void>
  checkPermissions(): Promise<PermissionsResult>
  readGpx(options: { path: string }): Promise<ReadGpxResult>
  addListener(
    eventName: 'trackingState',
    listener: (info: TrackingStateEvent) => void
  ): Promise<{ remove: () => void }>
  addListener(
    eventName: 'trackingStopped',
    listener: (info: TrackingStoppedEvent) => void
  ): Promise<{ remove: () => void }>
  removeAllListeners(): Promise<void>
}>('BikeTracking')
