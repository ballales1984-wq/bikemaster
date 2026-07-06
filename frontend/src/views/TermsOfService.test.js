import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TermsOfService from "../views/TermsOfService.vue";

describe("TermsOfService", () => {
  it("renders the page title", () => {
    const wrapper = mount(TermsOfService, {
      global: { stubs: { RouterLink: true } },
    });
    expect(wrapper.find("h1").exists()).toBe(true);
  });

  it("has multiple sections", () => {
    const wrapper = mount(TermsOfService, {
      global: { stubs: { RouterLink: true } },
    });
    const sections = wrapper.findAll("h2");
    expect(sections.length).toBeGreaterThanOrEqual(2);
  });

  it("mentions MIT license", () => {
    const wrapper = mount(TermsOfService, {
      global: { stubs: { RouterLink: true } },
    });
    expect(wrapper.text()).toContain("MIT");
  });
});
