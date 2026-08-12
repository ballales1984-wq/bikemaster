import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import RideDetail from "../components/RideDetail.vue";

setActivePinia(createPinia());

const mockFetchRide = vi.hoisted(() => vi.fn(() => Promise.resolve(null)));
const mockUpdateRide = vi.hoisted(() => vi.fn(() => Promise.resolve(null)));

const apiGet = vi.hoisted(() => vi.fn().mockResolvedValue({}));
const apiPut = vi.hoisted(() => vi.fn().mockResolvedValue({}));

vi.mock("../stores/rides", () => ({
  useRidesStore: () => ({
    fetchRide: mockFetchRide,
    updateRide: mockUpdateRide,
  }),
}));

vi.mock("../utils/api.ts", () => ({
  apiGet,
  apiPut,
}));

vi.mock("../components/SpeedMap.vue", () => ({
  default: { template: '<div class="speed-map-stub" />' },
}));

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    t: (key) => {
      const map = {
        "rideDetail.edit": "Modifica",
        "rideDetail.save": "Salva",
        "rideDetail.cancel": "Annulla",
        "rideDetail.title": "Dettaglio Uscita",
        "rideDetail.date": "Data",
        "rideDetail.distance": "Distanza",
        "rideDetail.duration": "Durata",
        "rideDetail.avgSpeed": "Velocità media",
        "rideDetail.calories": "Calorie",
        "rideDetail.detailAnalysis": "Analisi dettagliata",
        "rideDetail.elevationGain": "Dislivello",
        "rideDetail.maxSpeed": "Velocità max",
        "rideDetail.avgHrLabel": "FC media",
        "rideDetail.fatigue": "Fatica",
        "rideDetail.charts": "Grafici",
        "rideDetail.speedChart": "Grafico velocità",
        "rideDetail.elevationChart": "Grafico elevazione",
        "rideDetail.type": "Tipo",
        "rides.weight": "Peso",
        "rides.source": "Fonte",
        "rides.officialRace": "Gara ufficiale",
        "rides.activityType": "Tipo attività",
        "common.other": "Altro",
        "rideDetail.saving": "Salvataggio...",
        "rideDetail.close": "Chiudi",
        "rideDetail.avgHr": "Frequenza cardiaca media",
        "rideDetail.elevation": "Elevazione",
      };
      return map[key] || key;
    },
  }),
}));

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("RideDetail", () => {
  afterEach(() => vi.clearAllMocks());

  it("does not render when no ride", () => {
    const wrapper = mount(RideDetail, {
      global: { stubs: { SpeedMap: true } },
    });
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("renders ride details when ride is set", async () => {
    const ride = {
      id: 1,
      date: "2026-01-01",
      distance_km: 40,
      duration_minutes: 90,
      avg_speed_kmh: 26.7,
      calories: 400,
    };
    mockFetchRide.mockResolvedValueOnce(ride);

    const wrapper = mount(RideDetail, {
      props: { rideId: 1 },
      global: { stubs: { SpeedMap: true } },
    });
    await flush();

    expect(wrapper.find("h2").exists()).toBe(true);
    expect(wrapper.find(".metrics-grid").exists()).toBe(true);
    expect(wrapper.findAll(".metric-card").length).toBe(4);
  });

  it("formats distance correctly", () => {
    const wrapper = mount(RideDetail, {
      global: { stubs: { SpeedMap: true } },
    });
    expect(wrapper.vm.fmt(40)).toBe("40.0");
    expect(wrapper.vm.fmt(null)).toBe("—");
  });

  it("saves ride edits via PUT including avg_speed_kmh, weight_kg, is_official, source", async () => {
    const ride = {
      id: 42,
      date: "2026-08-01",
      title: "Morning ride",
      distance_km: 40,
      duration_minutes: 90,
      avg_speed_kmh: 22,
      weight_kg: 72,
      calories: 400,
      heart_rate_avg: 150,
      elevation_gain_m: 200,
      activity_type: "ride",
      is_official: true,
      source: "manual",
    };
    mockFetchRide.mockResolvedValueOnce(ride);
    mockUpdateRide.mockResolvedValueOnce({ ...ride, distance_km: 50 });

    const wrapper = mount(RideDetail, {
      props: { rideId: 42 },
      global: { stubs: { SpeedMap: true } },
    });
    await flush();

    await wrapper.find('[aria-label="Modifica"]').trigger("click");
    await flush();

    await wrapper.find(".save-btn").trigger("click");
    await flush();

    expect(mockUpdateRide).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        distance_km: 40,
        heart_rate_avg: 150,
        elevation_gain_m: 200,
        avg_speed_kmh: 22,
        weight_kg: 72,
        is_official: true,
        source: "manual",
      })
    );
  });
});
