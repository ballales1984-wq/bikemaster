import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import PWAInstallPrompt from "../components/PWAInstallPrompt.vue";

vi.mock("../composables/usePWA", () => ({
  usePWA: () => ({
    showPrompt: { value: true },
    deferredPrompt: {
      value: { prompt: vi.fn().mockResolvedValue({ outcome: "accepted" }) },
    },
    prompt: vi.fn(),
  }),
}));

describe("PWAInstallPrompt", () => {
  it("renders when showPrompt is true", () => {
    const wrapper = mount(PWAInstallPrompt);
    expect(wrapper.find(".pwa-banner").exists()).toBe(true);
  });

  it("has install button", () => {
    const wrapper = mount(PWAInstallPrompt);
    expect(wrapper.find(".btn-primary").exists()).toBe(true);
  });

  it("has dismiss button", () => {
    const wrapper = mount(PWAInstallPrompt);
    const closeBtn = wrapper.find(".pwa-banner-close");
    expect(closeBtn.exists()).toBe(true);
  });
});
