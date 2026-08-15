import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import ErrorBoundary from "./ErrorBoundary.vue";

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}));

describe("ErrorBoundary", () => {
  it("renders default slot when no error", () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="child">Safe content</div>',
      },
    });
    expect(wrapper.find(".child").exists()).toBe(true);
  });

  it("shows error UI when error is set via wrapper setData", async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="safe">OK</div>',
      },
    });
    expect(wrapper.find(".error-boundary").exists()).toBe(false);

    await wrapper.setData({ error: "boom" });
    await nextTick();
    expect(wrapper.find(".error-boundary").exists()).toBe(true);
    expect(wrapper.text()).toContain("errorBoundary.title");
    expect(wrapper.text()).toContain("boom");

    await wrapper.find("button").trigger("click");
    await nextTick();
    expect(wrapper.find(".error-boundary").exists()).toBe(false);
    expect(wrapper.find(".safe").exists()).toBe(true);
  });
});
