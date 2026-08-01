import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useAuthStore } from "../stores/auth";
import AdminPanel from "../components/AdminPanel.vue";

setActivePinia(createPinia());

beforeEach(() => {
  sessionStorage.clear();
});

vi.mock("../utils/api.ts", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

describe("AdminPanel", () => {
  it("renders the admin panel title", () => {
    useAuthStore().user = { username: "admin", is_admin: true };
    const wrapper = mount(AdminPanel);
    expect(wrapper.find("h2").text()).toContain("Administration");
  });

  it("has admin action cards", () => {
    useAuthStore().user = { username: "admin", is_admin: true };
    const wrapper = mount(AdminPanel);
    const cards = wrapper.findAll(".admin-card");
    expect(cards.length).toBeGreaterThanOrEqual(3);
  });

  it("has backup link", () => {
    useAuthStore().user = { username: "admin", is_admin: true };
    const wrapper = mount(AdminPanel);
    const backupLink = wrapper.find(".admin-card");
    expect(backupLink.exists()).toBe(true);
  });
});
