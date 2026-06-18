import { computed, defineStore, ref } from 'pinia'

export const useTrackingStore = defineStore('tracking', () => {
  const isTracking = ref(false)
  const isPaused = ref(false)
  const distance = ref(0)
  const currentSpeed = ref(0)
  const avgSpeed = ref(0)
  const elapsedTime = ref(0)
  const elevation = ref(0)
  const points = ref(0)
  const heartRate = ref<number | null>(null)
  const cadence = ref<number | null>(null)
  const power = ref<number | null>(null)
  const gpxPath = ref<string | null>(null)

  function start() {
    isTracking.value = true
    isPaused.value = false
    resetMetrics()
  }

  function pause() {
    isPaused.value = true
  }

  function resume() {
    isPaused.value = false
  }

  function stop() {
    isTracking.value = false
    isPaused.value = false
  }

  function updateMetrics(payload: {
    distance?: number
    currentSpeed?: number
    avgSpeed?: number
    elapsedTime?: number
    elevation?: number
    points?: number
    heartRate?: number | null
    cadence?: number | null
    power?: number | null
  }) {
    if (payload.distance !== undefined) distance.value = payload.distance
    if (payload.currentSpeed !== undefined) currentSpeed.value = payload.currentSpeed
    if (payload.avgSpeed !== undefined) avgSpeed.value = payload.avgSpeed
    if (payload.elapsedTime !== undefined) elapsedTime.value = payload.elapsedTime
    if (payload.elevation !== undefined) elevation.value = payload.elevation
    if (payload.points !== undefined) points.value = payload.points
    if (payload.heartRate !== undefined) heartRate.value = payload.heartRate
    if (payload.cadence !== undefined) cadence.value = payload.cadence
    if (payload.power !== undefined) power.value = payload.power
  }

  function setGpxPath(path: string) {
    gpxPath.value = path
  }

  function resetMetrics() {
    distance.value = 0
    currentSpeed.value = 0
    avgSpeed.value = 0
    elapsedTime.value = 0
    elevation.value = 0
    points.value = 0
    heartRate.value = null
    cadence.value = null
    power.value = null
  }

  const formattedTime = computed(() => {
    const totalSeconds = Math.floor(elapsedTime.value)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  })

  const formattedDistance = computed(() => {
    return (distance.value / 1000).toFixed(2)
  })

  return {
    isTracking,
    isPaused,
    distance,
    currentSpeed,
    avgSpeed,
    elapsedTime,
    elevation,
    points,
    heartRate,
    cadence,
    power,
    gpxPath,
    start,
    pause,
    resume,
    stop,
    updateMetrics,
    setGpxPath,
    resetMetrics,
    formattedTime,
    formattedDistance,
  }
})