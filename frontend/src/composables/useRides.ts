import type { Ride } from '../types/index'
import { apiGet, apiPost, apiDelete } from '../utils/api'
import * as L from 'leaflet'

interface GPSPoint {
  lat: number
  lon: number
}

type EmitFn = (event: string, data?: unknown) => void

interface SummaryResponse {
  rides?: number
  total?: number
  distance_km?: number
  calories?: number
  avg_speed_kmh?: number
  duration_minutes?: number
  ridesList?: Ride[]
}

export function useRides(emit: EmitFn) {
  let map: L.Map | null = null

  async function fetchSummary(): Promise<SummaryResponse> {
    try {
      const data = await apiGet('/api/v1/rides') as SummaryResponse
      const rides = data.rides || []
      const total = data.total || rides.length
      const totalKm = rides.reduce((s: number, r: Ride) => s + (Number(r.distance_km) || 0), 0)
      const totalCal = rides.reduce((s: number, r: Ride) => s + (Number(r.calories) || 0), 0)
      const avgSp = rides.length ? rides.reduce((s: number, r: Ride) => s + (Number(r.avg_speed_kmh) || 0), 0) / rides.length : 0
      const totalMin = rides.reduce((s: number, r: Ride) => s + (Number(r.duration_minutes) || 0), 0)
      return { rides: total, distance_km: totalKm, calories: totalCal, avg_speed_kmh: avgSp, duration_minutes: totalMin, ridesList: rides }
    } catch {
      return { rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0, ridesList: [] }
    }
  }

  async function createRide(formData: FormData) {
    await apiPost('/api/v1/rides', formData)
  }

  async function deleteRide(id: number) {
    await apiDelete(`/api/v1/rides/${id}`)
  }

  function initMap(el: HTMLElement, points: GPSPoint[]) {
    if (map) {
      map.remove()
      map = null
    }
    if (!el) return
    map = L.map(el).setView([45.0, 9.0], 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'OSM contributors',
      maxZoom: 18,
    }).addTo(map)
    if (points && points.length) {
      L.polyline(points.map(p => [p.lat, p.lon] as L.LatLngTuple), { color: '#4ecca3', weight: 5, opacity: 0.8 }).addTo(map)
    }
  }

  return { fetchSummary, createRide, deleteRide, initMap }
}
