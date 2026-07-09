import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import LiveMap from "../components/LiveMap.vue";

vi.mock("leaflet", () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      remove: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn().mockReturnThis() })),
    polyline: vi.fn(() => ({ addTo: vi.fn().mockReturnThis(), setLatLngs: vi.fn() })),
    circleMarker: vi.fn(() => ({ addTo: vi.fn().mockReturnThis(), setLatLng: vi.fn() })),
    latLng: vi.fn((lat, lon) => ({ lat, lng: lon })),
  },
}));

describe("LiveMap", () => {
  it("renders map container", () => {
    const wrapper = mount(LiveMap);
    expect(wrapper.find(".live-map").exists()).toBe(true);
  });

  it("exposes addPoint method", () => {
    const wrapper = mount(LiveMap);
    expect(wrapper.vm.addPoint).toBeDefined();
    expect(typeof wrapper.vm.addPoint).toBe("function");
  });

  it("exposes clear method", () => {
    const wrapper = mount(LiveMap);
    expect(wrapper.vm.clear).toBeDefined();
    expect(typeof wrapper.vm.clear).toBe("function");
  });
});
