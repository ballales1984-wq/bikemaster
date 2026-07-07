import { ref } from 'vue'
import type { Ride } from '../types/index'
import type * as L from 'leaflet'
import { apiGet, apiPost, apiDelete } from '../utils/api'
import { DEFAULT_RIDE_MAP_CENTER, DEFAULT_RIDE_MAP_ZOOM } from '../constants'

interface GPSPoint {
  lat: number
  lon: number
}

type SummaryResponse = {
  rides?: number
  total?: number
  distance_km?: number
  calories?: number
  avg_speed_kmh?: number
  duration_minutes?: number
  ridesList?: Ride[]
}

export function useRides() {
  const map = ref<L.Map | null>(null)

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

  async function initMap(el: HTMLElement, points: GPSPoint[]) {
    if (map.value) {
      map.value.remove()
      map.value = null
    }
    if (!el) return
    const L = await import('leaflet')
    map.value = L.map(el).setView(DEFAULT_RIDE_MAP_CENTER, DEFAULT_RIDE_MAP_ZOOM)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'OSM contributors',
      maxZoom: 18,
    }).addTo(map.value)
    if (points && points.length) {
      L.polyline(points.map(p => [p.lat, p.lon] as L.LatLngTuple), { color: '#4ecca3', weight: 5, opacity: 0.8 }).addTo(map.value)
    }
  }

  return { fetchSummary, createRide, deleteRide, initMap }
}
