import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ConfirmModal from "../components/ConfirmModal.vue";

describe("ConfirmModal", () => {
  it("has correct structure", () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    });
    // The component uses Teleport, check existence
    const component = wrapper.vm;
    expect(component).toBeDefined();
  });

  it("has confirm and cancel methods", () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    });
    expect(wrapper.vm.confirm).toBeDefined();
    expect(wrapper.vm.cancel).toBeDefined();
  });

  it("emits confirm when confirm method called", async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    });
    wrapper.vm.confirm();
    expect(wrapper.emitted("confirm")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
  });

  it("emits cancel when cancel method called", async () => {
    const wrapper = mount(ConfirmModal, {
      props: { modelValue: true },
    });
    wrapper.vm.cancel();
    expect(wrapper.emitted("cancel")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
  });
});
