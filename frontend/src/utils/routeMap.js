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

export function formatDistance(meters = 0) {
  return `${(meters / 1000).toFixed(2)} km`
}
