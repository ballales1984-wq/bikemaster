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

import BaseChart from "./BaseChart.vue";

const baseConfig = {
  type: "line",
  data: {
    labels: ["a", "b", "c"],
    datasets: [{ label: "x", data: [1, 2, 3] }],
  },
  options: {},
};

describe("BaseChart", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders a canvas element", () => {
    const wrapper = mount(BaseChart, { props: { config: baseConfig } });
    expect(wrapper.find("canvas").exists()).toBe(true);
  });

  it("shows empty label when there is no data", () => {
    const wrapper = mount(BaseChart, {
      props: {
        config: { type: "line", data: { labels: [], datasets: [] }, options: {} },
        emptyLabel: "Nessun dato",
      },
    });
    expect(wrapper.find(".base-chart__empty").text()).toBe("Nessun dato");
  });

  it("hides empty label when datasets contain data", () => {
    const wrapper = mount(BaseChart, { props: { config: baseConfig } });
    expect(wrapper.find(".base-chart__empty").exists()).toBe(false);
  });

  it("respects the height prop", () => {
    const wrapper = mount(BaseChart, {
      props: { config: baseConfig, height: "320px" },
    });
    expect(wrapper.find(".base-chart").attributes("style")).toContain("320px");
  });
});
