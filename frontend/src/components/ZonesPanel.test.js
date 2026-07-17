import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("chart.js/auto", () => ({
  default: vi
    .fn()
    .mockImplementation(() => ({
      destroy: vi.fn(),
      update: vi.fn(),
      resize: vi.fn(),
    })),
}));

const zonesPayload = {
  ftp_watts: 250,
  max_hr: 190,
  rides_with_power: 3,
  rides_with_hr: 5,
  power: {
    available: true,
    total_samples: 1200,
    zones: [
      { zone: "Z1", label: "Recovery", lower_w: 137, upper_w: 160, count: 100, pct_time: 8.3, color: "#4ecca3" },
      { zone: "Z2", label: "Endurance", lower_w: 160, upper_w: 185, count: 400, pct_time: 33.3, color: "#90EE90" },
    ],
  },
  hr: {
    available: true,
    total_samples: 2000,
    zones: [
      { zone: "Z1", label: "Recovery", lower_bpm: 104, upper_bpm: 121, count: 300, pct_time: 15, color: "#4ecca3" },
      { zone: "Z2", label: "Endurance", lower_bpm: 121, upper_bpm: 140, count: 700, pct_time: 35, color: "#90EE90" },
    ],
  },
};

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api", () => ({ apiGet }));

import ZonesPanel from "./ZonesPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("ZonesPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the zones heading", async () => {
    apiGet.mockResolvedValue(zonesPayload);
    const wrapper = mount(ZonesPanel);
    await flush();
    expect(wrapper.find(".zones-panel").exists()).toBe(true);
    expect(wrapper.text()).toContain("Zone di Allenamento");
  });

  it("shows FTP and max HR from the payload", async () => {
    apiGet.mockResolvedValue(zonesPayload);
    const wrapper = mount(ZonesPanel);
    await flush();
    expect(wrapper.text()).toContain("FTP 250W");
    expect(wrapper.text()).toContain("FC max 190bpm");
  });

  it("renders two zone charts (power + hr)", async () => {
    apiGet.mockResolvedValue(zonesPayload);
    const wrapper = mount(ZonesPanel);
    await flush();
    expect(wrapper.findAll("canvas")).toHaveLength(2);
  });

  it("shows an error message on failure", async () => {
    apiGet.mockRejectedValue(new Error("boom"));
    const wrapper = mount(ZonesPanel);
    await flush();
    expect(wrapper.text()).toContain("Impossibile caricare");
  });
});
