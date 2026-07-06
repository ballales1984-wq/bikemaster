import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import ToastContainer from "../components/ToastContainer.vue";

describe("ToastContainer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders empty container initially", () => {
    const wrapper = mount(ToastContainer);
    expect(wrapper.find(".toast").exists()).toBe(false);
  });

  it("exposes add method and renders toast", async () => {
    const wrapper = mount(ToastContainer);
    const exposed = wrapper.vm.add;
    exposed("Test message", "success");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast-content").text()).toBe("Test message");
    expect(wrapper.find(".toast").classes()).toContain("success");
  });

  it("auto-removes toast after timeout with animation", async () => {
    const wrapper = mount(ToastContainer);
    const exposed = wrapper.vm.add;
    exposed("Fading toast", "info", 1000);
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast").exists()).toBe(true);
    vi.advanceTimersByTime(1000);
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast").classes()).toContain("exiting");
    vi.advanceTimersByTime(300);
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast").exists()).toBe(false);
  });

  it("defaults to info type", async () => {
    const wrapper = mount(ToastContainer);
    const exposed = wrapper.vm.add;
    exposed("Default toast");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast").classes()).toContain("info");
  });

  it("has accessible container", () => {
    const wrapper = mount(ToastContainer);
    expect(wrapper.find("#toast-container").exists()).toBe(true);
    expect(wrapper.find('[role="status"]').exists()).toBe(true);
  });

  it("renders close button", async () => {
    const wrapper = mount(ToastContainer);
    wrapper.vm.add("Closable", "info");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast-close").exists()).toBe(true);
  });

  it("has toast icon", async () => {
    const wrapper = mount(ToastContainer);
    wrapper.vm.add("With icon", "success");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".toast-icon").exists()).toBe(true);
  });
});
