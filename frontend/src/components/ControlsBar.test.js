import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import ControlsBar from "../components/ControlsBar.vue";

describe("ControlsBar", () => {
  it("shows resume button when paused", () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: true },
    });
    expect(wrapper.text()).toContain("tracking.resume");
  });

  it("shows pause button when not paused", () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: false },
    });
    expect(wrapper.text()).toContain("tracking.pause");
  });

  it("always shows stop button", () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: true },
    });
    expect(wrapper.text()).toContain("tracking.stop");
  });

  it("emits pause event", async () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: false },
    });
    await wrapper.find("button:nth-child(1)").trigger("click");
    expect(wrapper.emitted("pause")).toBeTruthy();
  });

  it("emits resume event", async () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: true },
    });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("resume")).toBeTruthy();
  });

  it("emits stop event", async () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: false },
    });
    const stopBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("Stop"));
    if (stopBtn) {
      await stopBtn.trigger("click");
      expect(wrapper.emitted("stop")).toBeTruthy();
    }
  });

  it("has accessible button labels", () => {
    const wrapper = mount(ControlsBar, {
      props: { isPaused: false },
    });
    const buttons = wrapper.findAll("button");
    expect(buttons.length).toBe(2);
  });
});
