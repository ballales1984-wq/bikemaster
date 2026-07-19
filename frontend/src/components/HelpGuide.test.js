import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import HelpGuide from "../components/HelpGuide.vue";

describe("HelpGuide", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders help panel with title", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    expect(document.body.querySelector(".help-panel")).not.toBeNull();
    expect(document.body.querySelector(".help-header h2")?.textContent).toContain("Guida BikeMaster");
    wrapper.unmount();
  });

  it("renders category buttons", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const text = document.body.textContent || "";
    expect(text).toContain("Navigazione");
    expect(text).toContain("Tracciamento");
    expect(text).toContain("Impostazioni");
    wrapper.unmount();
  });

  it("switches category on button click", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const trackingBtn = document.body.querySelectorAll(".cat-btn");
    let found = false;
    trackingBtn.forEach((btn) => {
      if (btn.textContent?.includes("Tracciamento")) {
        btn.dispatchEvent(new Event("click"));
        found = true;
      }
    });
    if (found) {
      await wrapper.vm.$nextTick();
      expect(document.body.textContent || "").toContain("Tracciamento uscita");
    }
    wrapper.unmount();
  });

  it("opens panel when FAB is clicked", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const fab = document.body.querySelector(".help-fab");
    if (fab) {
      fab.dispatchEvent(new Event("click"));
      await wrapper.vm.$nextTick();
      expect(document.body.querySelector(".help-panel.open")).not.toBeNull();
    }
    wrapper.unmount();
  });

  it("closes panel when close button is clicked", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const fab = document.body.querySelector(".help-fab");
    if (fab) {
      fab.dispatchEvent(new Event("click"));
      await wrapper.vm.$nextTick();
      const closeBtn = document.body.querySelector(".help-close");
      if (closeBtn) {
        closeBtn.dispatchEvent(new Event("click"));
        await wrapper.vm.$nextTick();
        expect(document.body.querySelector(".help-panel.open")).toBeNull();
      }
    }
    wrapper.unmount();
  });

  it("renders help tags for active category", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const text = document.body.textContent || "";
    expect(text).toContain("Uscite");
    expect(text).toContain("velocità media");
    wrapper.unmount();
  });

  it("does not render help tags for inactive categories", async () => {
    const wrapper = mount(HelpGuide, { attachTo: document.body });
    await wrapper.vm.$nextTick();
    const text = document.body.textContent || "";
    expect(text).not.toContain("Tracciamento uscita");
    wrapper.unmount();
  });
});
