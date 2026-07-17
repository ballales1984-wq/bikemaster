import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet }));

const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock("../composables/useToast", () => ({
  useToast: () => ({ success: toastSuccess, error: toastError }),
}));

vi.mock("../db/localDb", () => ({
  initLocalDb: vi.fn(async () => {}),
  isLocalDbReady: vi.fn(() => false),
}));

vi.mock("../utils/userKeys", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, parseBulkKeys: vi.fn((input) => ({ garmin: input })) };
});

import ConnectionsView from "./ConnectionsView.vue";

function mountView() {
  return mount(ConnectionsView, { global: { plugins: [createPinia()] } });
}

describe("ConnectionsView", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders a card for each known service", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    expect(wrapper.findAll(".connection-card").length).toBe(5);
    expect(wrapper.text()).toContain("Strava");
    expect(wrapper.text()).toContain("Garmin Connect");
  });

  it("renders connect button for oauth services", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    const oauthButtons = wrapper
      .findAll(".connection-card.oauth button.btn-primary");
    expect(oauthButtons.length).toBeGreaterThan(0);
  });

  it("shows apikey form for garmin", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".apikey-form").exists()).toBe(true);
    expect(wrapper.find("input.text-input").exists()).toBe(true);
  });

  it("importBulkKeys reports status from parsed keys", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const { parseBulkKeys } = await import("../utils/userKeys");
    parseBulkKeys.mockReturnValue({ garmin: "abc123" });

    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    wrapper.vm.bulkInput = "garmin=abc123";
    await wrapper.vm.importBulkKeys();
    await wrapper.vm.$nextTick();

    expect(parseBulkKeys).toHaveBeenCalledWith("garmin=abc123");
    expect(wrapper.vm.bulkStatusClass).toBe("ok");
  });

  it("importBulkKeys shows error when no keys found", async () => {
    apiGet.mockResolvedValue({ connections: [] });
    const { parseBulkKeys } = await import("../utils/userKeys");
    parseBulkKeys.mockReturnValue({});

    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    wrapper.vm.bulkInput = "nothing";
    await wrapper.vm.importBulkKeys();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.bulkStatusClass).toBe("err");
  });

  it("saveApiKey stores a draft value", async () => {
    setActivePinia(createPinia());
    apiGet.mockResolvedValue({ connections: [] });
    const wrapper = mountView();
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    wrapper.vm.apikeyDrafts["garmin"] = "secret";
    await wrapper.vm.saveApiKey("garmin");
    await wrapper.vm.$nextTick();

    expect(toastSuccess).toHaveBeenCalled();
  });
});
