import { vi } from 'vitest'

const enMessages = {
  "nav": { "rides": "Rides", "tracking": "Tracking", "import": "Import", "athlete": "Athlete", "coach": "AI Coach", "knowledge": "Knowledge", "calendar": "Calendar", "granfondo": "Granfondo", "maps": "Maps", "heatmap": "Heatmap", "badges": "Badges", "comparison": "Compare", "weather": "Weather", "admin": "Admin", "logout": "Logout" },
  "tracking": { "title": "GPS Tracking", "start": "Start Tracking", "stop": "Stop Tracking", "pause": "Pause", "resume": "Resume", "inProgress": "In progress", "paused": "Paused" },
  "auth": { "login": "Login", "register": "Register", "username": "Username", "password": "Password" },
  "common": { "loading": "Loading...", "or": "or", "name": "Name", "save": "Save", "cancel": "Cancel", "delete": "Delete", "error": "Error", "success": "Success", "confirm": "Confirm", "close": "Close", "back": "Back", "next": "Next", "submit": "Submit", "search": "Search", "filter": "Filter", "clear": "Clear", "download": "Download", "upload": "Upload", "view": "View", "actions": "Actions", "status": "Status", "date": "Date", "time": "Time", "description": "Description", "type": "Type", "name": "Name", "value": "Value", "total": "Total", "average": "Average", "min": "Min", "max": "Max", "none": "None", "yes": "Yes", "no": "No", "and": "and", "language": "Language", "theme": "Theme", "dark": "Dark", "light": "Light", "auto": "Auto" },
  "coach": { "title": "AI Cycling Coach", "online": "Online", "offline": "Offline", "welcome": "Hi! I'm your AI Coach.", "report": "Full Report", "clear": "New conversation", "send": "Send", "placeholder": "Type a message..." },
  "rides": { "title": "My Rides", "addTitle": "Add Ride", "noRides": "No rides recorded", "distance": "Distance", "duration": "Duration", "avgSpeed": "Avg Speed", "elevation": "Elevation", "calories": "Calories", "date": "Date", "actions": "Actions" },
  "app": { "title": "BikeMaster" },
}

function t(key) {
  const parts = key.split('.')
  let current = enMessages
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = current[part]
    } else {
      return key
    }
  }
  return typeof current === 'string' ? current : key
}

vi.mock('../composables/useI18n', () => ({
  useI18n: () => ({
    locale: { value: 'en' },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}))

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

HTMLElement.prototype.scrollIntoView = vi.fn()

if (typeof atob === 'undefined') {
  globalThis.atob = (str) => Buffer.from(str, 'binary').toString('base64')
}

if (typeof alert === 'undefined') {
  window.alert = vi.fn()
}

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  getImageData: vi.fn(() => ({ data: new Array(4) })),
  putImageData: vi.fn(),
  createImageData: vi.fn(() => []),
  setTransform: vi.fn(),
  drawImage: vi.fn(),
  save: vi.fn(),
  fillText: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  transform: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
}))

if (typeof requestAnimationFrame === 'undefined') {
  globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0)
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id)
}

if (typeof performance === 'undefined' || typeof performance.now !== 'function') {
  globalThis.performance = {
    now: () => Date.now(),
  }
}

