import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useUIStore } from "../stores/ui";

describe("UIStore - AetherMap feature flag", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("useAetherMap is false by default", () => {
    const store = useUIStore();
    expect(store.useAetherMap).toBe(false);
  });
});
