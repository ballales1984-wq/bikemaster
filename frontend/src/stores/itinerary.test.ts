import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useItineraryStore } from "./itinerary";

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("../utils/api", () => ({
  apiGet: (path: string) => mockGet(path),
  apiPost: (path: string, body: unknown) => mockPost(path, body),
}));

vi.mock("../utils/auth", () => ({
  useAuthStore: () => ({ token: "test-token" }),
}));

describe("itinerary store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it("initializes with empty state", () => {
    const store = useItineraryStore();
    expect(store.itineraries).toEqual([]);
    expect(store.current).toBeNull();
    expect(store.loading).toBe(false);
    expect(store.error).toBe("");
    expect(store.totalKm).toBe(0);
  });

  describe("loadList", () => {
    it("fetches and stores itineraries", async () => {
      const mocked = [
        { id: 1, name: "Tour A" },
        { id: 2, name: "Tour B" },
      ];
      mockGet.mockResolvedValue({ itineraries: mocked });
      const store = useItineraryStore();
      await store.loadList();
      expect(mockGet).toHaveBeenCalledWith("/api/v1/itineraries");
      expect(store.itineraries.length).toBe(2);
      expect(store.itineraries[0].name).toBe("Tour A");
    });

    it("stores empty array when API returns no itineraries", async () => {
      mockGet.mockResolvedValue({ itineraries: [] });
      const store = useItineraryStore();
      await store.loadList();
      expect(store.itineraries).toEqual([]);
    });

    it("sets error on failure", async () => {
      mockGet.mockRejectedValue(new Error("Network error"));
      const store = useItineraryStore();
      await store.loadList();
      expect(store.error).toBe("Network error");
      expect(store.itineraries).toEqual([]);
    });
  });

  describe("loadOne", () => {
    it("loads itinerary with stages", async () => {
      const payload = {
        itinerary: { id: 1, name: "Tour" },
        stages: [{ id: 1, title: "Day 1", distance_km: 50 }],
      };
      mockGet.mockResolvedValue(payload);
      const store = useItineraryStore();
      await store.loadOne(1);
      expect(mockGet).toHaveBeenCalledWith("/api/v1/itineraries/1");
      expect(store.current?.itinerary.id).toBe(1);
      expect(store.current?.stages.length).toBe(1);
    });

    it("sets error on failure", async () => {
      mockGet.mockRejectedValue(new Error("Not found"));
      const store = useItineraryStore();
      await store.loadOne(99);
      expect(store.error).toBe("Not found");
      expect(store.current).toBeNull();
    });
  });

  describe("create", () => {
    it("creates itinerary and returns id", async () => {
      mockPost.mockResolvedValueOnce({ id: 42, name: "New" });
      mockGet.mockResolvedValue({ itineraries: [{ id: 42, name: "New" }] });
      const store = useItineraryStore();
      const result = await store.create({ name: "New" });
      expect(mockPost).toHaveBeenCalledWith("/api/v1/itineraries", {
        name: "New",
      });
      expect(result).toBe(42);
    });

    it("returns null on failure", async () => {
      mockPost.mockRejectedValue(new Error("Create failed"));
      const store = useItineraryStore();
      const result = await store.create({ name: "New" });
      expect(result).toBeNull();
      expect(store.error).toBe("Create failed");
    });
  });

  describe("addStage", () => {
    it("posts stage and reloads itinerary", async () => {
      mockGet.mockResolvedValue({
        itinerary: { id: 1, name: "Tour" },
        stages: [],
      });
      const stagePayload = {
        stage_day: 1,
        title: "Start",
        poi_id: 5,
        estimated_km: 50,
      };
      mockPost.mockResolvedValueOnce({ id: 10, ...stagePayload });
      const store = useItineraryStore();
      store.current = {
        itinerary: { id: 1, name: "Tour" },
        stages: [],
      };
      const ok = await store.addStage(1, stagePayload);
      expect(ok).toBe(true);
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/itineraries/1/stages",
        stagePayload,
      );
      expect(mockGet).toHaveBeenCalledWith("/api/v1/itineraries/1");
    });

    it("returns false on failure", async () => {
      mockPost.mockRejectedValue(new Error("Stage failed"));
      const store = useItineraryStore();
      store.current = {
        itinerary: { id: 1, name: "Tour" },
        stages: [],
      };
      const ok = await store.addStage(1, { stage_day: 1 });
      expect(ok).toBe(false);
      expect(store.error).toBe("Stage failed");
    });
  });

  describe("totalKm", () => {
    it("sums stage distances", () => {
      const store = useItineraryStore();
      store.current = {
        itinerary: { id: 1, name: "Tour" },
        stages: [
          { id: 1, itinerary_id: 1, distance_km: 50 },
          { id: 2, itinerary_id: 1, distance_km: 30.5 },
        ],
      };
      expect(store.totalKm).toBe(80.5);
    });

    it("returns 0 when no current itinerary", () => {
      const store = useItineraryStore();
      expect(store.totalKm).toBe(0);
    });
  });
});
