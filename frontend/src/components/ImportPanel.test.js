import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
const apiPut = vi.hoisted(() => vi.fn());
const apiDelete = vi.hoisted(() => vi.fn());
const apiUpload = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiUpload,
}));

import ImportPanel from "./ImportPanel.vue";

function makeFile(name) {
  return new File(["ride-data"], name, { type: "application/octet-stream" });
}

describe("ImportPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows placeholder text when no files selected", async () => {
    const wrapper = mount(ImportPanel);
    expect(wrapper.find(".upload-placeholder").text()).toContain("Drag files");
  });

  it("displays selected file count after onChange", async () => {
    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    const input = wrapper.find("input").element;
    const event = new Event("change");
    Object.defineProperty(event, "target", {
      value: { files: [makeFile("ride.gpx"), makeFile("second.fit")] },
    });
    input.dispatchEvent(event);
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".upload-placeholder").text()).toContain(
      "2 files selected",
    );
  });

  it("calls onDrop to collect files", async () => {
    const wrapper = mount(ImportPanel);

    wrapper.vm.onDrop({ dataTransfer: { files: [makeFile("drop.gpx")] } });
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.files.length).toBe(1);
  });

  it("disables import button when no files", async () => {
    const wrapper = mount(ImportPanel);

    const button = wrapper.find("button.btn-primary");
    expect(button.attributes("disabled")).toBeDefined();
  });

  it("enables import button after file selection", async () => {
    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    const input = wrapper.find("input").element;
    const event = new Event("change");
    Object.defineProperty(event, "target", {
      value: { files: [makeFile("ride.gpx")] },
    });
    input.dispatchEvent(event);
    await wrapper.vm.$nextTick();

    const button = wrapper.find("button.btn-primary");
    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("imports GPX file via upload method", async () => {
    apiUpload.mockResolvedValue({ id: 1 });

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.gpx")];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(apiUpload).toHaveBeenCalledWith(
      "/api/v1/import/gpx",
      expect.any(File),
    );
    expect(wrapper.text()).toContain("Import completed");
  });

  it("imports FIT file via upload method", async () => {
    apiUpload.mockResolvedValue({ id: 2 });

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.fit")];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(apiUpload).toHaveBeenCalledWith(
      "/api/v1/import/fit",
      expect.any(File),
    );
  });

  it("imports multiple files with progress", async () => {
    apiUpload.mockResolvedValue({ id: 1 });

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [
      makeFile("a.gpx"),
      makeFile("b.fit"),
      makeFile("c.gpx"),
    ];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 200));
    await wrapper.vm.$nextTick();

    expect(apiUpload).toHaveBeenCalledTimes(3);
    expect(wrapper.find(".progress-track").exists()).toBe(true);
  });

  it("shows error on upload failure", async () => {
    apiUpload.mockRejectedValue(new Error("Upload failed"));

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.gpx")];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain("Upload failed");
  });

  it("has Google Fit connect button", async () => {
    const wrapper = mount(ImportPanel);

    expect(wrapper.text()).toContain("Import from Google Fit");
  });

  it("shows upload section title", async () => {
    const wrapper = mount(ImportPanel);

    expect(wrapper.text()).toContain("Import Routes");
    expect(wrapper.text()).toContain("GPX or FIT");
  });

  it("shows importing state during upload", async () => {
    apiUpload.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ id: 1 }), 40)),
    );

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.gpx")];
    await wrapper.vm.$nextTick();

    const uploadPromise = wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 10));
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".btn-primary").text()).toContain("Importing");

    await uploadPromise;
  });

  it("clears files after successful upload", async () => {
    apiUpload.mockResolvedValue({ id: 1 });

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.gpx")];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.files.length).toBe(0);
  });

  it("pickFile triggers file input click", async () => {
    const wrapper = mount(ImportPanel);

    const clickSpy = vi.fn();
    wrapper.vm.fileInput = { click: clickSpy };
    wrapper.vm.pickFile();

    expect(clickSpy).toHaveBeenCalled();
  });

  it("emits summary-change on successful upload", async () => {
    apiUpload.mockResolvedValue({ id: 1 });

    const wrapper = mount(ImportPanel, {
      global: { stubs: { Teleport: true } },
    });

    wrapper.vm.files = [makeFile("ride.gpx")];
    await wrapper.vm.$nextTick();

    await wrapper.vm.upload();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("summary-change")).toBeTruthy();
  });

  it("onChange collects files from event", async () => {
    const wrapper = mount(ImportPanel);

    wrapper.vm.onChange({ target: { files: [makeFile("test.gpx")] } });
    expect(wrapper.vm.files.length).toBe(1);
  });
});
