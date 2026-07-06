import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import AthleteSettings from "../components/AthleteSettings.vue";

vi.mock("../utils/api.ts", () => ({
  apiGet: vi.fn().mockResolvedValue({ athletes: [] }),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
}));

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("AthleteSettings", () => {
  it("renders the athlete profile title", async () => {
    const wrapper = mount(AthleteSettings);
    await flush();
    expect(wrapper.find("h2").exists()).toBe(true);
  });

  it("has form fields", async () => {
    const wrapper = mount(AthleteSettings);
    await flush();
    const inputs = wrapper.findAll("input");
    expect(inputs.length).toBeGreaterThanOrEqual(5);
  });

  it("has save button", async () => {
    const wrapper = mount(AthleteSettings);
    await flush();
    const btn = wrapper.find(".btn-primary");
    expect(btn.exists()).toBe(true);
    expect(btn.text()).toBe("Save");
  });
});
