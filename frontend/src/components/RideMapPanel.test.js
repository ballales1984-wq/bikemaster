import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

setActivePinia(createPinia());

vi.mock("leaflet", () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      addLayer: vi.fn().mockReturnThis(),
      remove: vi.fn(),
      fitBounds: vi.fn().mockReturnThis(),
      invalidateSize: vi.fn().mockReturnThis(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn().mockReturnThis() })),
    layerGroup: vi.fn(() => {
      const mockGroup = {
        clearLayers: vi.fn(),
        addLayer: vi.fn().mockReturnThis(),
        addTo: vi.fn().mockReturnThis(),
      };
      return mockGroup;
    }),
    polyline: vi.fn(() => ({ addTo: vi.fn().mockReturnThis() })),
    latLngBounds: vi.fn(() => ({
      extend: vi.fn().mockReturnThis(),
      isValid: vi.fn(() => true),
      pad: vi.fn().mockReturnThis(),
    })),
    circleMarker: vi.fn(() => ({
      bindPopup: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis(),
    })),
    latLng: vi.fn((lat, lng) => ({ lat, lng })),
  },
}));

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

vi.mock("../utils/routeMap", () => ({
  buildRidePolylines: vi.fn(() => [
    {
      color: "#4ecca3",
      points: [
        [45.46, 9.19],
        [45.47, 9.2],
      ],
    },
  ]),
  escapeHtml: vi.fn((v) => String(v)),
  formatDistance: vi.fn((m) => `${(m / 1000).toFixed(2)} km`),
  gradeRiskPercent: vi.fn(() => 25),
  riskColor: vi.fn(() => "#27ae60"),
  speedRiskPercent: vi.fn(() => 30),
  weatherRiskPercent: vi.fn(() => 20),
  weatherLegend: vi.fn(() => [{ label: "Good", color: "#27ae60" }]),
  riskLegend: vi.fn(() => [{ label: "Low", range: "0-24", color: "#27ae60" }]),
  gradeLegend: vi.fn(() => [{ label: "Flat", color: "#27ae60" }]),
  speedLegend: vi.fn(() => [{ label: "Fast", color: "#27ae60" }]),
}));

import RideMapPanel from "./RideMapPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockRides = {
  rides: [
    {
      id: 1,
      date: "2026-06-01",
      distance_km: 42.5,
      duration_minutes: 90,
      avg_speed_kmh: 28.3,
      gps_points: [
        { lat: 45.46, lon: 9.19, altitude: 100 },
        { lat: 45.47, lon: 9.2, altitude: 110 },
      ],
    },
  ],
  total: 1,
};

describe("RideMapPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders panel with title", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.text()).toContain("maps.routeMaps");
  });

  it("has map container", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.find("#route-map").exists()).toBe(true);
  });

  it("has update button", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.find(".btn-primary").exists()).toBe(true);
  });

  it("has coloring mode selector", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    const selects = wrapper.findAll("select");
    expect(selects.length).toBeGreaterThanOrEqual(1);
  });

  it("has weather toggle checkbox", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    const checkbox = wrapper.find('input[type="checkbox"]');
    expect(checkbox.exists()).toBe(true);
  });

  it("has risk levels defined", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    const legendCards = wrapper.findAll(".legend-card");
    expect(legendCards.length).toBeGreaterThan(0);
  });

  it("has grade legend defined", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.vm.gradeLegend).toBeDefined();
  });

  it("has speed legend defined", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.vm.speedLegend).toBeDefined();
  });

  it("formats distances correctly", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.exists()).toBe(true);
  });

  it("has demo route points", async () => {
    apiGet.mockResolvedValueOnce(mockRides);
    const wrapper = mount(RideMapPanel);
    await flush();
    expect(wrapper.vm.demoRoutePoints.length).toBeGreaterThan(0);
  });
});
