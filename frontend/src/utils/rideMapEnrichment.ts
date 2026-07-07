import type { GpsPoint, RideSegment } from '../types/index'

export function normalizePoints(points: GpsPoint[] = []): GpsPoint[] {
  return points
    .map((point) => ({
      lat: Number(point.lat),
      lon: Number(point.lon),
      altitude: point.altitude ?? point.elevation ?? point.elevation_m ?? null,
      timestamp: point.timestamp ?? null,
      speed: point.speed ?? null,
    }))
    .filter(
      (point) => Number.isFinite(point.lat) && Number.isFinite(point.lon),
    )
}

export function downsamplePoints(points: GpsPoint[], stride = 3): GpsPoint[] {
  if (points.length <= 200) return points
  return points.filter(
    (_, index) => index % stride === 0 || index === points.length - 1,
  )
}

export function buildSegments(points: GpsPoint[]): RideSegment[] {
  const segments: RideSegment[] = []
  if (points.length < 2) return segments

  let previous = points[0]
  for (let index = 1; index < points.length; index += 1) {
    const current = points[index]
    const distance_m = haversineDistanceM(
      previous.lat,
      previous.lon,
      current.lat,
      current.lon,
    )
    const altitudeA = Number(previous.altitude)
    const altitudeB = Number(current.altitude)
    const elevation_delta_m =
      Number.isFinite(altitudeA) && Number.isFinite(altitudeB)
        ? altitudeB - altitudeA
        : 0
    const grade = distance_m > 0 ? (elevation_delta_m / distance_m) * 100 : 0

    segments.push({
      start: [previous.lat, previous.lon],
      end: [current.lat, current.lon],
      distance_m,
      elevation_delta_m,
      grade,
      risk: 0,
      color: '#4ecca3',
    })
    previous = current
  }
  return segments
}

export function buildDemoSegments(points: GpsPoint[], gradeRiskPercent: (grade: number) => number, riskColor: (risk: number) => string): RideSegment[] {
  const segments = buildSegments(points)
  return segments.map((segment) => {
    const gradeRisk = gradeRiskPercent(segment.grade)
    const risk = Math.round(gradeRisk * 0.7)
    return {
      ...segment,
      risk,
      color: riskColor(risk),
    }
  })
}

export function getCenter(points: GpsPoint[]): { lat: number; lon: number } | null {
  if (!points.length) return null
  const lat = points.reduce((sum, point) => sum + point.lat, 0) / points.length
  const lon = points.reduce((sum, point) => sum + point.lon, 0) / points.length
  return { lat, lon }
}

export function haversineDistanceM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6371000
  const toRad = (value: number) => (value * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(a))
}
