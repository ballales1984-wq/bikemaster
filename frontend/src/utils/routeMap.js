export function buildRidePolylines(ride) {
  const groups = []
  let current = null

  for (const segment of ride.segments || []) {
    if (!current || current.color !== segment.color) {
      current = {
        color: segment.color,
        points: [segment.start],
      }
      groups.push(current)
    }
    current.points.push(segment.end)
  }

  return groups.map(group => ({ color: group.color, points: group.points }))
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]))
}

export function riskColor(risk) {
  if (risk < 25) return '#27ae60'
  if (risk < 50) return '#f1c40f'
  if (risk < 75) return '#e67e22'
  return '#e74c3c'
}

export function gradeRiskPercent(grade) {
  const absGrade = Math.abs(grade)
  if (absGrade < 3) return 15
  if (absGrade < 6) return 35
  if (absGrade < 10) return 65
  return 90
}

export function weatherRiskPercent(score) {
  if (!Number.isFinite(score)) return 50
  if (score >= 8) return 10
  if (score >= 5) return 45
  return 85
}

export function speedRiskPercent(speed) {
  const spd = Number(speed) || 0
  if (spd >= 25) return 15
  if (spd >= 15) return 45
  return 85
}

export function formatDistance(meters = 0) {
  return `${(meters / 1000).toFixed(2)} km`
}

export function speedColor(ride, index) {
  const points = ride.gps_points || []
  if (index < points.length) {
    const speed = points[index].speed ?? null
    if (speed === null) return '#4488ff'
    const speeds = points.map(p => p.speed).filter(s => s !== null)
    if (!speeds.length) return '#4488ff'
    const minSpd = Math.min(...speeds)
    const maxSpd = Math.max(...speeds)
    if (maxSpd === minSpd) return '#ffff00'
    const ratio = (speed - minSpd) / (maxSpd - minSpd)
    if (ratio < 0.5) {
      const r = 255
      const g = Math.round(255 * ratio * 2)
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}00`
    }
    const r = Math.round(255 * (1 - (ratio - 0.5) * 2))
    const g = 255
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}00`
  }
  return '#4488ff'
}
