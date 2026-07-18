/**
 * Composable GPS a basso consumo energetico.
 * Fornisce uno scheduling adattivo della geolocalizzazione: l'intervallo di
 * campionamento e l'accuratezza variano in base alla velocità rilevata e alla
 * presenza di movimento, riducendo il drain della batteria quando fermi o con
 * il risparmio attivo. Espone lo stato reattivo `isWaiting`/`isMoving` e i
 * controlli `start`, `stop`, `pause`, `resume`.
 */
import { ref } from 'vue'
import { haversineDistanceMeters as haversineMeters } from '../utils/geo'

export interface BatteryGpsOptions {
  onPosition: (position: GeolocationPosition) => void
  onError: (error: GeolocationPositionError) => void
  onWaiting?: () => void
  onFirstFix?: () => void
  onActivityChange?: (moving: boolean) => void
  batterySaver?: () => boolean
}

const SPEED_STATIONARY = 0.6
const SPEED_MODERATE = 4
const SPEED_FAST = 8

const INTERVAL_FIRST_FIX = 1000
const INTERVAL_FAST = 2000
const INTERVAL_MEDIUM_FAST = 3000
const INTERVAL_MEDIUM = 4000
const INTERVAL_SLOW = 8000
const INTERVAL_STATIONARY = 15000
const INTERVAL_SAVER = 12000

const NO_MOVEMENT_TIMEOUT = 20000
const MIN_MOVEMENT_METERS = 1.5
const ERROR_BACKOFF = 20000

export function useBatteryEfficientGps(options: BatteryGpsOptions) {
  const isWaiting = ref(false)
  const isMoving = ref(false)

  let timerId: number | null = null
  let lastPosition: GeolocationPosition | null = null
  let lastMovementAt = 0
  let firstFix = true
  let paused = false
  let stopped = true

  function currentSpeed(): number {
    return lastPosition?.coords.speed ?? 0
  }

  function highAccuracy(): boolean {
    if (options.batterySaver?.()) return false
    const speed = currentSpeed()
    return firstFix || speed >= SPEED_STATIONARY
  }

  function nextInterval(): number {
    if (options.batterySaver?.()) return INTERVAL_SAVER
    if (firstFix) return INTERVAL_FIRST_FIX
    const speed = currentSpeed()
    if (speed >= SPEED_FAST) return INTERVAL_FAST
    if (speed >= SPEED_MODERATE) return INTERVAL_MEDIUM_FAST
    if (speed >= SPEED_STATIONARY) return INTERVAL_MEDIUM
    if (Date.now() - lastMovementAt > NO_MOVEMENT_TIMEOUT) return INTERVAL_STATIONARY
    return INTERVAL_SLOW
  }

  function schedule(delay?: number) {
    if (stopped || paused) return
    if (timerId !== null) clearTimeout(timerId)
    timerId = window.setTimeout(tick, delay ?? nextInterval())
  }

  function setMoving(moving: boolean) {
    if (isMoving.value === moving) return
    isMoving.value = moving
    options.onActivityChange?.(moving)
  }

  function tick() {
    if (stopped || paused) return
    const useHighAccuracy = highAccuracy()
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (stopped || paused) return
        const moved =
          !lastPosition ||
          haversineMeters(
            lastPosition.coords.latitude,
            lastPosition.coords.longitude,
            position.coords.latitude,
            position.coords.longitude
          ) > MIN_MOVEMENT_METERS
        if (moved) lastMovementAt = Date.now()
        setMoving(moved && currentSpeed() >= SPEED_STATIONARY)
        lastPosition = position
        if (firstFix) {
          firstFix = false
          isWaiting.value = false
          options.onFirstFix?.()
        }
        options.onPosition(position)
        schedule()
      },
      (error) => {
        if (stopped || paused) return
        if (firstFix) {
          firstFix = false
          isWaiting.value = false
        }
        options.onError(error)
        schedule(INTERVAL_SLOW)
        void error
      },
      {
        enableHighAccuracy: useHighAccuracy,
        maximumAge: useHighAccuracy ? 1000 : 5000,
        timeout: 10000,
      }
    )
  }

  function start() {
    stopped = false
    paused = false
    firstFix = true
    lastPosition = null
    lastMovementAt = Date.now()
    setMoving(false)
    isWaiting.value = true
    options.onWaiting?.()
    tick()
  }

  function pause() {
    paused = true
    if (timerId !== null) {
      clearTimeout(timerId)
      timerId = null
    }
  }

  function resume() {
    if (!stopped && paused) {
      paused = false
      isWaiting.value = false
      schedule(INTERVAL_FIRST_FIX)
    }
  }

  function stop() {
    stopped = true
    paused = false
    if (timerId !== null) {
      clearTimeout(timerId)
      timerId = null
    }
    isWaiting.value = false
    setMoving(false)
  }

  return { start, stop, pause, resume, isWaiting, isMoving }
}
