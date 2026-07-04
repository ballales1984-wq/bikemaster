import type { Ride } from '../types/index'
import { apiGet, apiPost, apiDelete } from '../utils/api'
import * as L from 'leaflet'

interface GPSPoint {
  lat: number
  lon: number
}

type SummaryResponse {
  rides?: number
  total?: number
  distance_km?: number
  calories?: number
  avg_speed_kmh?: number
  duration_minutes?: number
  ridesList?: Ride[]
}

export function useRides() {
  let map: L.Map | null = null

  async function fetchSummary(): Promise<SummaryResponse> {
    try {
      const data = await apiGet('/api/v1/rides') as SummaryResponse
      const rides = data.ridesList || data.rides || []
      const ridesArray = Array.isArray(rides) ? rides : []
      const total = data.total || ridesArray.length
      const totalKm = ridesArray.reduce((s: number, r: Ride) => s + (Number(r.distance_km) || 0), 0)
      const totalCal = ridesArray.reduce((s: number, r: Ride) => s + (Number(r.calories) || 0), 0)
      const avgSp = ridesArray.length ? ridesArray.reduce((s: number, r: Ride) => s + (Number(r.avg_speed_kmh) || 0), 0) / ridesArray.length : 0
      const totalMin = ridesArray.reduce((s: number, r: Ride) => s + (Number(r.duration_minutes) || 0), 0)
      return { rides: total, distance_km: totalKm, calories: totalCal, avg_speed_kmh: avgSp, duration_minutes: totalMin, ridesList: ridesArray }
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
