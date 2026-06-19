declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'leaflet' {
  export function map(element: HTMLElement): Map
  export function tileLayer(url: string, options?: TileLayerOptions): TileLayer
  export function polyline(latlngs: LatLngTuple[], options?: PolylineOptions): Polyline

  export interface Map {
    setView(center: LatLngTuple, zoom: number): Map
    remove(): void
  }

  export interface TileLayer {
    addTo(map: Map): TileLayer
  }

  export interface Polyline {
    addTo(map: Map): Polyline
  }

  export interface TileLayerOptions {
    attribution?: string
    maxZoom?: number
  }

  export interface PolylineOptions {
    color?: string
    weight?: number
    opacity?: number
  }

  export type LatLngTuple = [number, number]
  const L: {
    map: typeof map
    tileLayer: typeof tileLayer
    polyline: typeof polyline
  }
  export default L
}

declare global {
  interface Window {
    BikeTracking: {
      startTracking: () => Promise<void>
      stopTracking: () => Promise<{ gpxPath: string | null }>
      pauseTracking: () => Promise<void>
      resumeTracking: () => Promise<void>
      checkPermissions: () => Promise<{ granted: boolean }>
    }
  }
}
