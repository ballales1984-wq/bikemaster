import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useTrackingStore } from "../stores/trackingStore";

describe("trackingStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("initializes with default values", () => {
    const store = useTrackingStore();
    expect(store.isTracking).toBe(false);
    expect(store.isPaused).toBe(false);
    expect(store.distance).toBe(0);
    expect(store.currentSpeed).toBe(0);
    expect(store.avgSpeed).toBe(0);
  });

  it("starts tracking correctly", () => {
    const store = useTrackingStore();
    store.start();
    expect(store.isTracking).toBe(true);
    expect(store.isPaused).toBe(false);
  });

  it("pauses tracking", () => {
    const store = useTrackingStore();
    store.start();
    store.pause();
    expect(store.isPaused).toBe(true);
  });

  it("resumes tracking", () => {
    const store = useTrackingStore();
    store.start();
    store.pause();
    store.resume();
    expect(store.isPaused).toBe(false);
  });

  it("stops tracking", () => {
    const store = useTrackingStore();
    store.start();
    store.stop();
    expect(store.isTracking).toBe(false);
  });

  it("updates metrics correctly", () => {
    const store = useTrackingStore();
    store.updateMetrics({
      distance: 15000,
      currentSpeed: 25.5,
      avgSpeed: 22.0,
      elapsedTime: 3600,
      points: 500,
    });
    expect(store.distance).toBe(15000);
    expect(store.currentSpeed).toBe(25.5);
    expect(store.avgSpeed).toBe(22.0);
    expect(store.elapsedTime).toBe(3600);
    expect(store.points).toBe(500);
  });

  it("adds route points and keeps GPX data", () => {
    const store = useTrackingStore();
    store.addPoint({
      lat: 45.0,
      lon: 7.0,
      altitude: 120,
      timestamp: "2024-06-15T10:00:00Z",
    });
    store.addPoint({
      lat: 45.001,
      lon: 7.001,
      altitude: 130,
      timestamp: "2024-06-15T10:01:00Z",
    });
    expect(store.routePoints).toHaveLength(2);
    expect(store.points).toBe(2);
    expect(store.lastPoint?.lat).toBe(45.001);
    expect(store.toGpx()).toContain("BikeMaster ride");
    expect(store.toGpx()).toContain("BikeMaster-Web");
  });

  it("creates a GPX blob", () => {
    const store = useTrackingStore();
    store.addPoint({
      lat: 45.0,
      lon: 7.0,
      altitude: 120,
      timestamp: "2024-06-15T10:00:00Z",
    });
    store.setGpxBlob(
      new Blob([store.toGpx()], { type: "application/gpx+xml" }),
    );
    expect(store.gpxBlob).toBeInstanceOf(Blob);
  });

  it("formats time correctly", () => {
    const store = useTrackingStore();
    store.elapsedTime = 3661;
    expect(store.formattedTime).toBe("01:01:01");
  });

  it("formats distance correctly", () => {
    const store = useTrackingStore();
    store.distance = 12345;
    expect(store.formattedDistance).toBe("12.35");
  });

  it("resets metrics", () => {
    const store = useTrackingStore();
    store.updateMetrics({ distance: 10000, currentSpeed: 25 });
    store.resetMetrics();
    expect(store.distance).toBe(0);
    expect(store.currentSpeed).toBe(0);
  });

  it("starts and closes activity segments", () => {
    const store = useTrackingStore();
    const segId = store.startSegment();
    expect(store.currentSegment).not.toBeNull();
    expect(store.currentSegment?.id).toBe(segId);

    store.currentSegment?.points.push({
      lat: 45.0,
      lon: 7.0,
      altitude: 120,
      timestamp: new Date().toISOString(),
    });
    store.currentSegment.distanceM = 500;
    store.currentSegment.elevationGainM = 20;

    const closed = store.closeCurrentSegment();
    expect(closed).not.toBeNull();
    expect(closed?.endTime).not.toBeNull();
    expect(store.segments).toHaveLength(1);
    expect(store.currentSegment).toBeNull();
  });

  it("builds daily timeline entries", () => {
    const store = useTrackingStore();
    store.startSegment();
    if (store.currentSegment) {
      store.currentSegment.startTime = Date.now() - 3600000;
      store.currentSegment.distanceM = 5000;
      store.closeCurrentSegment();
    }
    const timeline = store.buildDailyTimeline();
    expect(timeline.length).toBeGreaterThanOrEqual(1);
    expect(timeline[0].totalDistanceKm).toBeGreaterThan(0);
  });

  it("computes activity rings", () => {
    const store = useTrackingStore();
    expect(store.activityRings).toHaveLength(3);
    expect(store.activityRings[0].label).toBe("move");
    expect(store.activityRings[1].label).toBe("exercise");
    expect(store.activityRings[2].label).toBe("stand");
  });

  it("clears all state", () => {
    const store = useTrackingStore();
    store.updateMetrics({ distance: 5000 });
    store.startSegment();
    store.clearAll();
    expect(store.distance).toBe(0);
    expect(store.segments).toHaveLength(0);
    expect(store.currentSegment).toBeNull();
  });
});
