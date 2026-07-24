import { vi } from "vitest";

// Mock Leaflet globally — jsdom cannot run canvas/WebGL APIs used by Leaflet.
// Without this mock, any component that imports Leaflet throws
// "latLng is not a function" during test collection.
vi.mock("leaflet", () => {
  const noop = () => ({});
  const leafletMock = {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      addLayer: vi.fn().mockReturnThis(),
      removeLayer: vi.fn().mockReturnThis(),
      remove: vi.fn(),
      on: vi.fn().mockReturnThis(),
      off: vi.fn().mockReturnThis(),
      fitBounds: vi.fn().mockReturnThis(),
      getBounds: vi.fn(() => ({
        getNorthEast: vi.fn(),
        getSouthWest: vi.fn(),
      })),
      getZoom: vi.fn(() => 10),
      panTo: vi.fn().mockReturnThis(),
      setZoom: vi.fn().mockReturnThis(),
      invalidateSize: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    marker: vi.fn(() => ({ addTo: vi.fn(), bindPopup: vi.fn().mockReturnThis(), remove: vi.fn() })),
    polyline: vi.fn(() => ({ addTo: vi.fn(), remove: vi.fn(), getBounds: vi.fn() })),
    circle: vi.fn(() => ({ addTo: vi.fn(), remove: vi.fn() })),
    latLng: vi.fn((lat, lng) => ({ lat, lng })),
    latLngBounds: vi.fn(() => ({ extend: vi.fn().mockReturnThis(), isValid: vi.fn(() => true) })),
    icon: vi.fn(noop),
    divIcon: vi.fn(noop),
    LayerGroup: vi.fn(() => ({ addTo: vi.fn(), addLayer: vi.fn(), clearLayers: vi.fn(), remove: vi.fn() })),
    layerGroup: vi.fn(() => ({ addTo: vi.fn(), addLayer: vi.fn(), clearLayers: vi.fn(), remove: vi.fn() })),
    Control: { Layers: vi.fn(() => ({ addTo: vi.fn() })) },
    control: { layers: vi.fn(() => ({ addTo: vi.fn() })) },
    default: {},
  };
  return { default: leafletMock, ...leafletMock };
});

vi.mock("chart.js/auto", () => ({
  default: vi
    .fn()
    .mockImplementation(() => ({
      destroy: vi.fn(),
      update: vi.fn(),
      resize: vi.fn(),
    })),
}));

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

HTMLElement.prototype.scrollIntoView = vi.fn();

if (typeof atob === "undefined") {
  globalThis.atob = (str) => Buffer.from(str, "binary").toString("base64");
}

if (typeof window !== "undefined") {
  window.alert = vi.fn();
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
}));

if (typeof requestAnimationFrame === "undefined") {
  globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
}

if (
  typeof performance === "undefined" ||
  typeof performance.now !== "function"
) {
  globalThis.performance = {
    now: () => Date.now(),
  };
}
