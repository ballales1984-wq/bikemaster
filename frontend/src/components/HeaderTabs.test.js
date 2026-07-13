import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";
import HeaderTabs from "./HeaderTabs.vue";

const router = createRouter({ history: createWebHistory(), routes: [] });

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}));

describe("HeaderTabs", () => {
  const render = (props = {}) =>
    mount(HeaderTabs, {
      props: { isAdmin: false, ...props },
      global: {
        plugins: [router],
        stubs: {
          RouterLink: {
            template: '<a><slot /></a>',
          },
        },
      },
    });

  it("renders navigation links", () => {
    const wrapper = render({ active: "rides" });

    expect(wrapper.text()).toContain("nav.rides");
  });

  it("shows admin link only for admins", () => {
    const userLinks = render().text();
    const adminLinks = render({ isAdmin: true }).text();

    expect(userLinks).not.toContain("nav.admin");
    expect(adminLinks).toContain("nav.admin");
  });

  it("emits logout and displays current user role", async () => {
    const wrapper = render({ isAdmin: true });

    expect(wrapper.text()).toContain("nav.admin");

    const buttons = wrapper.findAll("button");
    await buttons.at(-1).trigger("click");

    expect(wrapper.emitted().logout).toEqual([[]]);
  });
});
