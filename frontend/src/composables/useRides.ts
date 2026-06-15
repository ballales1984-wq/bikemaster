import { apiGet, apiPost, apiDelete } from '../utils/api.ts'

export function useRides(emit) {
  let map = null

  async function fetchSummary() {
    try {
      const data = await apiGet('/api/v1/rides')
      const rides = data.rides || []
      const total = data.total || rides.length
      const totalKm = rides.reduce((s, r) => s + (Number(r.distance_km) || 0), 0)
      const totalCal = rides.reduce((s, r) => s + (Number(r.calories) || 0), 0)
      const avgSp = rides.length ? rides.reduce((s, r) => s + (Number(r.avg_speed_kmh) || 0), 0) / rides.length : 0
      const totalMin = rides.reduce((s, r) => s + (Number(r.duration_minutes) || 0), 0)
      return { rides: total, distance_km: totalKm, calories: totalCal, avg_speed_kmh: avgSp, duration_minutes: totalMin, ridesList: rides }
    } catch (e) {
      console.error('fetchSummary', e)
      return { rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0, ridesList: [] }
    }
  }

  async function createRide(formData) {
    await apiPost('/api/v1/rides', formData)
  }

  async function deleteRide(id) {
    await apiDelete(`/api/v1/rides/${id}`)
  }

  function initMap(el, points) {
    if (map) { map.remove(); map = null }
    if (!el) return
    map = L.map(el).setView([45.0, 9.0], 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'OSM contributors',
      maxZoom: 18,
    }).addTo(map)
    if (points && points.length) {
      L.polyline(points.map(p => [p.lat, p.lon]), { color: '#4ecca3', weight: 5, opacity: 0.8 }).addTo(map)
    }
  }

  return { fetchSummary, createRide, deleteRide, initMap }
}
