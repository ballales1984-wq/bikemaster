import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

import WeatherPanel from "./WeatherPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("WeatherPanel", () => {
  afterEach(() => {
    apiGet.mockReset();
    vi.clearAllMocks();
  });

  it("renders weather form with default values", () => {
    const wrapper = mount(WeatherPanel);
    expect(wrapper.find("#weather-lat").exists()).toBe(true);
    expect(wrapper.find("#weather-lon").exists()).toBe(true);
    expect(wrapper.find("#weather-date").exists()).toBe(true);
    expect(wrapper.find(".btn-primary").exists()).toBe(true);
  });

  it("has correct lat/lon default values", () => {
    const wrapper = mount(WeatherPanel);
    expect(wrapper.vm.lat).toBe(45.4642);
    expect(wrapper.vm.lon).toBe(9.19);
  });

  it("calls apiGet with weather endpoint", async () => {
    apiGet.mockResolvedValueOnce({
      location: { city: "Milan" },
      temperature: 22,
      feels_like: 20,
      humidity: 65,
      wind_speed: 3.5,
      pressure: 1013,
      score: 7,
      description: "Partly cloudy",
      advice: "Good weather",
    });
    const wrapper = mount(WeatherPanel);
    await wrapper.find("button").trigger("click");
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/weather",
      expect.objectContaining({
        lat: expect.any(Number),
        lon: expect.any(Number),
      }),
    );
  });

  it("displays weather after successful fetch", async () => {
    apiGet.mockResolvedValueOnce({
      location: { city: "Milan" },
      temperature: 22,
      feels_like: 20,
      humidity: 65,
      wind_speed: 3.5,
      pressure: 1013,
      score: 7,
      description: "Partly cloudy",
      advice: "Good weather",
    });
    const wrapper = mount(WeatherPanel);
    await wrapper.find("button").trigger("click");
    await flush();
    expect(wrapper.vm.weather).not.toBe(null);
    expect(wrapper.vm.weather.location.city).toBe("Milan");
  });

  it("shows error on failed fetch", async () => {
    apiGet.mockRejectedValueOnce(new Error("Network error"));
    const wrapper = mount(WeatherPanel);
    await wrapper.find("button").trigger("click");
    await flush();
    expect(wrapper.vm.weatherError).toBe("Network error");
  });

  it("has forecast loading state initially false", () => {
    const wrapper = mount(WeatherPanel);
    expect(wrapper.vm.forecastLoading).toBe(false);
  });

  it("shows loading after fetch completes", async () => {
    apiGet.mockResolvedValueOnce({
      location: { city: "Milan" },
      temperature: 22,
      feels_like: 20,
      humidity: 65,
      wind_speed: 3.5,
      pressure: 1013,
      score: 7,
      description: "OK",
      advice: "Good",
    });
    const wrapper = mount(WeatherPanel);
    await wrapper.find("button").trigger("click");
    await flush();
    expect(wrapper.vm.loading).toBe(false);
  });

  it("shows 7-Day Forecast heading", () => {
    const wrapper = mount(WeatherPanel);
    expect(wrapper.text()).toContain("7-Day Forecast");
  });
});
