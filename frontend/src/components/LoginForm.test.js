import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import LoginForm from "../components/LoginForm.vue";

vi.mock("../composables/useI18n", () => ({
  useI18n: () => ({
    locale: { value: "en" },
    t: (key) => key,
    setLocale: vi.fn(),
  }),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders login and register tabs", () => {
    const wrapper = mount(LoginForm);
    expect(wrapper.text()).toContain("auth.login");
    expect(wrapper.text()).toContain("auth.register");
  });

  it("switches between login and register modes", async () => {
    const wrapper = mount(LoginForm);
    const registerBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("auth.register"));
    if (registerBtn) {
      await registerBtn.trigger("click");
      expect(
        wrapper.find('input[type="password"]').attributes("placeholder"),
      ).toContain("min 6 characters");
    }
  });

  it("validates username length on submit", async () => {
    const wrapper = mount(LoginForm);
    await wrapper.find('input[type="text"]').setValue("ab");
    await wrapper.find("form").trigger("submit.prevent");
    expect(wrapper.text()).toContain("Min 3 characters");
  });

  it("validates password length in register mode", async () => {
    const wrapper = mount(LoginForm);
    const registerBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("auth.register"));
    if (registerBtn) {
      await registerBtn.trigger("click");
    }
    await wrapper.find('input[type="text"]').setValue("validuser");
    await wrapper.find('input[type="password"]').setValue("123");
    await wrapper.find("form").trigger("submit.prevent");
    expect(wrapper.text()).toContain("Min 6 characters");
  });

  it("emits login event with correct credentials", async () => {
    const wrapper = mount(LoginForm);
    await wrapper.find('input[type="text"]').setValue("rider");
    await wrapper.find('input[type="password"]').setValue("secret");
    await wrapper.find("form").trigger("submit.prevent");
    expect(wrapper.emitted("login")).toBeTruthy();
    expect(wrapper.emitted("login")[0][0]).toEqual({
      username: "rider",
      password: "secret",
    });
  });

  it("emits error event from Google login failure", async () => {
    window.fetch = vi.fn().mockRejectedValue(new Error("Network error"));
    const wrapper = mount(LoginForm);
    const googleBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("Google"));
    if (googleBtn) {
      await googleBtn.trigger("click");
      expect(wrapper.emitted("error")).toBeTruthy();
    }
  });

  it("toggles password visibility", async () => {
    const wrapper = mount(LoginForm);
    const passwordInput = wrapper.find('input[type="password"]');
    expect(passwordInput.exists()).toBe(true);
    const toggleBtn = wrapper.find(".password-toggle");
    await toggleBtn.trigger("click");
    const textInput = wrapper.find('input[type="text"]');
    expect(textInput.exists()).toBe(true);
  });

  it("disables submit when form is invalid", async () => {
    const wrapper = mount(LoginForm);
    const btn = wrapper.find('button[type="submit"]');
    expect(btn.attributes("disabled")).toBeDefined();
  });

  it("enables submit when form is valid", async () => {
    const wrapper = mount(LoginForm);
    await wrapper.find('input[type="text"]').setValue("validuser");
    await wrapper.find('input[type="password"]').setValue("secret");
    const btn = wrapper.find('button[type="submit"]');
    expect(btn.attributes("disabled")).toBeUndefined();
  });

  it("has accessible form labels and attributes", () => {
    const wrapper = mount(LoginForm);
    expect(wrapper.find("#username").exists()).toBe(true);
    expect(wrapper.find("#password").exists()).toBe(true);
    expect(wrapper.find('[role="tablist"]').exists()).toBe(true);
    expect(wrapper.find("form[novalidate]").exists()).toBe(true);
  });
});
