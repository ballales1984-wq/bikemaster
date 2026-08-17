<!-- Route map panel: Leaflet map of GPS routes colored by risk (slope/weather/speed) or AetherMap 3D globe.
     Props: nessuna. Eventi: nessuno (usa /api/v1/rides e /api/v1/weather). Selettori stile mappa, colorazione, POI e route famose;
     replay animato del GPS. UI: toolbar, replay bar, mappa 560px, KPI e legende rischio/pendenza/meteo/velocita. -->
<template>
  <section class="panel">
    <div class="map-header">
      <div>
        <h2>{{ t("maps.routeMaps") }}</h2>
        <p class="map-subtitle">
          GPS segments are colored by gradient, weather conditions, or combined
          risk.
        </p>
      </div>
      <button class="btn btn-primary" :disabled="loading" @click="loadRides">
        {{ loading ? t("maps.updating") : t("maps.updateMap") }}
      </button>
      <button class="btn btn-secondary" @click="toggleAetherMap">
        {{ useAetherMap ? "Mappa 2D" : "Globo 3D" }}
      </button>
    </div>

    <div v-if="!useAetherMap" class="map-toolbar">
      <label class="control">
        <span>Map</span>
        <select id="map-style" v-model="mapStyle" class="form-input">
          <option v-for="(cfg, key) in MAP_STYLES" :key="key" :value="key">
            {{ cfg.label }}
          </option>
        </select>
      </label>

      <label class="control">
        <span>{{ t("maps.route") }}</span>
        <select id="map-route" v-model="selectedRideId" class="form-input">
          <option :value="null">All routes</option>
          <option v-for="ride in ridesWithGps" :key="ride.id" :value="ride.id">
            {{ ride.date }} · {{ formatDistance(ride.distance_m) }}
          </option>
        </select>
      </label>

      <label class="control">
        <span>{{ t("maps.coloring") }}</span>
        <select id="map-coloring" v-model="colorMode" class="form-input">
          <option value="combined">Grade + weather</option>
          <option value="slope">Grade only</option>
          <option value="weather">Weather only</option>
          <option value="speed">Speed</option>
        </select>
      </label>

      <label class="checkbox-control">
        <input id="weather-enabled" v-model="weatherEnabled" type="checkbox" />
        <span>{{ t("maps.includeWeather") }}</span>
      </label>

      <label class="checkbox-control">
        <input
          id="show-famous-routes"
          v-model="showFamousRoutes"
          type="checkbox"
        />
        <span>{{ t("maps.famousRoutes") }}</span>
      </label>

      <label class="checkbox-control">
        <input id="show-pois" v-model="showPois" type="checkbox" />
        <span>{{ t("maps.showPois") }}</span>
      </label>
    </div>

    <!-- Replay controls: animate the selected ride's GPS track over time. -->
    <div
      v-if="!useAetherMap && selectedRideId && replayPoints.length > 1"
      class="replay-bar"
    >
      <button class="btn btn-sm" @click="toggleReplay">
        {{ replaying ? "⏸ " + t("maps.pause") : "▶ " + t("maps.play") }}
      </button>
      <input
        v-model.number="replayIndex"
        class="replay-slider"
        type="range"
        min="0"
        :max="replayPoints.length - 1"
        @input="onReplayScrub"
      />
      <span class="replay-label"
        >{{ replayIndex + 1 }} / {{ replayPoints.length }}</span
      >
    </div>

    <div v-if="loading && !enrichedRides.length" class="loading-text">
      <span class="spinner" /> Caricamento percorsi...
    </div>

    <div id="route-map" ref="mapContainer" class="route-map">
      <AetherMapViewer
        v-if="useAetherMap"
        :ride-ids="visibleRideIds"
        :color-by-speed="true"
      />
      <template v-else>
        <div v-if="!ridesWithGps.length" class="empty-map-overlay">
          <div class="empty-map-content">
            <span class="empty-icon"></span>
            <p>No routes available</p>
            <p class="empty-hint">
              Import GPX/FIT or add a ride with GPS points to view your routes
            </p>
          </div>
        </div>
      </template>
    </div>

    <div v-if="!useAetherMap && ridesWithGps.length" class="map-kpis">
      <div class="kpi">
        <strong>{{ visibleRides.length }}</strong>
        <span>{{ visibleRides.length === 1 ? "route" : "routes" }}</span>
      </div>
      <div class="kpi">
        <strong>{{ totalGpsPoints }}</strong>
        <span>GPS points</span>
      </div>
      <div class="kpi">
        <strong>{{ averageRisk }}</strong>
        <span>average risk</span>
      </div>
      <div class="kpi">
        <strong>{{ worstRide }}</strong>
        <span>worst segment</span>
      </div>
    </div>

    <div v-if="!useAetherMap" class="legend-grid">
      <div class="legend-card">
        <h4>Combined Risk</h4>
        <div v-for="level in riskLevels" :key="level.label" class="legend-row">
          <span class="legend-swatch" :style="{ background: level.color }" />
          <span>{{ level.label }} · {{ level.range }}</span>
        </div>
      </div>

      <div class="legend-card">
        <h4>Gradients</h4>
        <div v-for="item in gradeLegend" :key="item.label" class="legend-row">
          <span class="legend-swatch" :style="{ background: item.color }" />
          <span>{{ item.label }}</span>
        </div>
      </div>

      <div v-if="weatherEnabled" class="legend-card">
        <h4>Weather</h4>
        <div v-for="item in weatherLegend" :key="item.label" class="legend-row">
          <span class="legend-swatch" :style="{ background: item.color }" />
          <span>{{ item.label }}</span>
        </div>
        <p v-if="weatherUnavailableCount" class="legend-note">
          {{ weatherUnavailableCount }}
          {{ weatherUnavailableCount === 1 ? "route" : "routes" }} without
          weather: weather risk set to 50/100.
        </p>
      </div>

      <div v-if="colorMode === 'speed'" class="legend-card">
        <h4>Speed</h4>
        <div v-for="item in speedLegend" :key="item.label" class="legend-row">
          <span class="legend-swatch" :style="{ background: item.color }" />
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import "leaflet/dist/leaflet.css";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useI18n } from "../composables/useI18n";
import { useUIStore } from "../stores/ui";
import { storeToRefs } from "pinia";
import L from "leaflet";
import { apiGet } from "../utils/api";
import {
  buildRidePolylines,
  escapeHtml,
  formatDistance,
  gradeRiskPercent,
  riskColor,
  speedRiskPercent,
  weatherRiskPercent,
} from "../utils/routeMap";
import { famousItalianRoutes } from "../data/italianRoutes";
import {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  RISK_COLORS,
  GRADE_COLORS,
  SPEED_COLORS,
} from "../constants";
import {
  normalizePoints,
  downsamplePoints,
  buildSegments,
  getCenter,
} from "../utils/rideMapEnrichment";
import type { EnrichedRide, GpsPoint, Ride, RideSegment } from "../types/index";
import AetherMapViewer from "./AetherMapViewer.vue";

const { t } = useI18n();
const uiStore = useUIStore();
const { useAetherMap } = storeToRefs(uiStore);

function toggleAetherMap() {
  useAetherMap.value = !useAetherMap.value;
}

const mapContainer = ref<HTMLElement | null>(null);
const loading = ref(false);
const enrichedRides = ref<EnrichedRide[]>([]);
const selectedRideId = ref<number | null>(null);
const colorMode = ref<string>("combined");
const weatherEnabled = ref(true);
const showFamousRoutes = ref(false);
const showPois = ref(true);
const mapStyle = ref<keyof typeof MAP_STYLES>(
  (localStorage.getItem("mapStyle") as keyof typeof MAP_STYLES) || "standard",
);

const weatherLegend = computed(() => [
  { label: "Good", color: RISK_COLORS.LOW },
  { label: "Fair", color: RISK_COLORS.MEDIUM },
  { label: "Poor", color: RISK_COLORS.SEVERE },
]);

const riskLevels = computed(() => [
  { label: "Low", range: "0-24", color: RISK_COLORS.LOW },
  { label: "Medium", range: "25-49", color: RISK_COLORS.MEDIUM },
  { label: "High", range: "50-74", color: RISK_COLORS.HIGH },
  { label: "Severe", range: "75-100", color: RISK_COLORS.SEVERE },
]);

const gradeLegend = computed(() => [
  { label: "Flat", color: GRADE_COLORS.FLAT },
  { label: "Moderate", color: GRADE_COLORS.MODERATE },
  { label: "Steep", color: GRADE_COLORS.STEEP },
  { label: "Very steep", color: GRADE_COLORS.VERY_STEEP },
]);

const speedLegend = computed(() => [
  { label: "Fast", color: SPEED_COLORS.FAST },
  { label: "Medium", color: SPEED_COLORS.MEDIUM },
  { label: "Slow", color: SPEED_COLORS.SLOW },
]);

const MAP_STYLES = {
  standard: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    label: "Standard (OSM)",
  },
  cyclosm: {
    url: "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="https://cyclosm.org">CyclOSM</a>',
    maxZoom: 20,
    label: "CyclOSM (Cycling)",
  },
  topo: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
    maxZoom: 17,
    label: "Topographic",
  },
};

let map: L.Map | null = null;
let layerGroup: L.LayerGroup | null = null;
let tileLayer: L.TileLayer | null = null;
let famousRoutesLayer: L.LayerGroup | null = null;

function createTileLayer(styleKey: keyof typeof MAP_STYLES) {
  const cfg = MAP_STYLES[styleKey] || MAP_STYLES.standard;
  return L.tileLayer(cfg.url, {
    attribution: cfg.attribution,
    maxZoom: cfg.maxZoom,
  });
}

function switchTileLayer(styleKey: keyof typeof MAP_STYLES) {
  if (!map) return;
  if (tileLayer) {
    map.removeLayer(tileLayer);
  }
  tileLayer = createTileLayer(styleKey);
  tileLayer.addTo(map);
}

async function renderMap() {
  if (useAetherMap.value) return;
  if (!mapContainer.value) return;

  if (!map) {
    map = L.map(mapContainer.value as HTMLElement, {
      preferCanvas: true,
    }).setView(DEFAULT_MAP_CENTER as [number, number], DEFAULT_MAP_ZOOM);
    tileLayer = createTileLayer(mapStyle.value);
    tileLayer.addTo(map);
    layerGroup = L.layerGroup().addTo(map);
    famousRoutesLayer = L.layerGroup().addTo(map);
  } else {
    switchTileLayer(mapStyle.value);
  }

  layerGroup?.clearLayers();
  const bounds = L.latLngBounds([]);

  const ridesToRender = visibleRides.value;

  for (const ride of ridesToRender) {
    const rideLayer = L.layerGroup();

    buildRidePolylines(ride).forEach((polylineData) => {
      const polyline = L.polyline(polylineData.points, {
        color: polylineData.color,
        weight: 5,
        opacity: 0.8,
        dashArray: undefined,
        lineCap: "round",
        lineJoin: "round",
      });
      polyline.addTo(rideLayer);
      polylineData.points.forEach((point) => {
        bounds.extend(point as L.LatLngExpression);
      });
    });

    if (ride.center) {
      const centerMarker = L.circleMarker(
        L.latLng(ride.center.lat, ride.center.lon),
        {
          radius: 6,
          color: riskColor(ride.overallRisk),
          fillColor: riskColor(ride.overallRisk),
          fillOpacity: 0.9,
          weight: 2,
        },
      );
      centerMarker.bindPopup(ridePopup(ride));
      centerMarker.addTo(rideLayer);
    }

    if (layerGroup) {
      layerGroup.addLayer(rideLayer);
    }

    if (ridesToRender.length > 3) {
      await new Promise((r) => setTimeout(r, 0));
    }
  }

  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.1));
  }
  map.invalidateSize();
}

const ridesWithGps = computed(() =>
  enrichedRides.value.filter((ride) => ride.gps_points.length > 1),
);

const visibleRides = computed(() => {
  if (selectedRideId.value) {
    const selected = ridesWithGps.value.find(
      (ride) => ride.id === selectedRideId.value,
    );
    if (selected) return [selected];
  }
  return ridesWithGps.value;
});

const visibleRideIds = computed(() => visibleRides.value.map((r) => r.id));

// --- Replay (animated track of the selected ride) ---
const replayPoints = ref<Array<{ lat: number; lon: number }>>([]);
const replayIndex = ref(0);
const replaying = ref(false);
let replayTimer: number | null = null;
let replayMarker: L.CircleMarker | null = null;
let replayPath: L.Polyline | null = null;

const POI_COLORS: Record<string, string> = {
  cafe: "#b45309",
  bakery: "#b45309",
  restaurant: "#dc2626",
  water: "#2563eb",
  viewpoint: "#7c3aed",
  bike_shop: "#059669",
  emergency: "#dc2626",
  other: "#64748b",
};
let poiLayer: L.LayerGroup | null = null;

function loadReplayPoints() {
  stopReplay();
  const ride = visibleRides.value.find((r) => r.id === selectedRideId.value);
  replayPoints.value = (ride?.gps_points || []).filter(
    (p) => Number.isFinite(p.lat) && Number.isFinite(p.lon),
  );
  replayIndex.value = 0;
  _prevReplayIndex = -1;
  drawReplay();
}

let _prevReplayIndex = -1;

function drawReplay() {
  if (!map) return;
  const targetIndex = replayIndex.value;
  const points = replayPoints.value;

  if (targetIndex !== _prevReplayIndex + 1 || replayPath === null) {
    if (replayPath) {
      map.removeLayer(replayPath);
      replayPath = null;
    }
    if (replayMarker) {
      map.removeLayer(replayMarker);
      replayMarker = null;
    }
    if (points.length >= 2 && targetIndex >= 0) {
      const pts = points
        .slice(0, targetIndex + 1)
        .map((p) => [p.lat, p.lon] as [number, number]);
      replayPath = L.polyline(pts, {
        color: "#4ecca3",
        weight: 5,
        opacity: 0.9,
      }).addTo(map);
    }
    const cur = points[targetIndex];
    if (cur) {
      replayMarker = L.circleMarker([cur.lat, cur.lon], {
        radius: 7,
        color: "#4ecca3",
        fillColor: "#4ecca3",
        fillOpacity: 1,
        weight: 3,
      }).addTo(map);
    }
    _prevReplayIndex = targetIndex;
    return;
  }

  if (replayPath && targetIndex < points.length) {
    replayPath.addLatLng([points[targetIndex].lat, points[targetIndex].lon]);
  }
  if (points[targetIndex]) {
    if (replayMarker) {
      replayMarker.setLatLng([
        points[targetIndex].lat,
        points[targetIndex].lon,
      ]);
    } else {
      replayMarker = L.circleMarker(
        [points[targetIndex].lat, points[targetIndex].lon],
        {
          radius: 7,
          color: "#4ecca3",
          fillColor: "#4ecca3",
          fillOpacity: 1,
          weight: 3,
        },
      ).addTo(map);
    }
  }
  _prevReplayIndex = targetIndex;
}

function toggleReplay() {
  if (replaying.value) {
    stopReplay();
  } else {
    if (replayIndex.value >= replayPoints.value.length - 1)
      replayIndex.value = 0;
    replaying.value = true;
    replayTimer = window.setInterval(() => {
      if (replayIndex.value >= replayPoints.value.length - 1) {
        stopReplay();
        return;
      }
      replayIndex.value += 1;
      drawReplay();
    }, 120);
  }
}

function stopReplay() {
  replaying.value = false;
  if (replayTimer !== null) {
    clearInterval(replayTimer);
    replayTimer = null;
  }
}

function onReplayScrub() {
  stopReplay();
  drawReplay();
}

async function loadPois() {
  if (!poiLayer && map) {
    poiLayer = L.layerGroup().addTo(map);
  }
  if (!poiLayer) return;
  poiLayer.clearLayers();
  if (!showPois.value) return;
  const targets =
    replayPoints.value.length > 1
      ? [replayPoints.value[Math.floor(replayPoints.value.length / 2)]]
      : visibleRides.value
          .map((r) => r.center)
          .filter((c): c is { lat: number; lon: number } => !!c);
  for (const center of targets.slice(0, 3)) {
    try {
      const data = await apiGet<{
        pois: Array<{
          name: string;
          lat: number;
          lon: number;
          type?: string;
          description?: string;
        }>;
      }>("/api/v1/maps/pois/nearby", {
        lat: String(center.lat),
        lon: String(center.lon),
        radius: "5",
      });
      for (const poi of data.pois || []) {
        if (!Number.isFinite(poi.lat) || !Number.isFinite(poi.lon)) continue;
        const color = POI_COLORS[poi.type || "other"] || POI_COLORS.other;
        L.circleMarker([poi.lat, poi.lon], {
          radius: 6,
          color,
          fillColor: color,
          fillOpacity: 0.9,
          weight: 2,
        })
          .addTo(poiLayer)
          .bindPopup(
            `<strong>${poi.name}</strong><br>${poi.type || ""}${poi.description ? "<br>" + poi.description : ""}`,
          );
      }
    } catch {
      /* POIs optional */
    }
  }
}

const totalGpsPoints = computed(() =>
  visibleRides.value.reduce((sum, ride) => sum + ride.gps_points.length, 0),
);

const averageRisk = computed(() => {
  const risks = visibleRides.value.flatMap((ride) =>
    ride.segments.map((segment) => segment.risk),
  );
  if (!risks.length) return "—";
  return `${Math.round(risks.reduce((sum, value) => sum + value, 0) / risks.length)}/100`;
});

const worstRide = computed(() => {
  const risks = visibleRides.value.flatMap((ride) =>
    ride.segments.map((segment) => segment.risk),
  );
  if (!risks.length) return "—";
  return `${Math.max(...risks)}/100`;
});

const weatherUnavailableCount = computed(
  () => enrichedRides.value.filter((ride) => ride.weatherUnavailable).length,
);

watch(mapStyle, () => {
  localStorage.setItem("mapStyle", mapStyle.value);
  void renderMap();
});

watch(colorMode, () => {
  enrichedRides.value = enrichedRides.value.map((ride) => applyRideRisk(ride));
  void renderMap();
});

watch(weatherEnabled, () => {
  loadRides();
});

watch(selectedRideId, () => {
  void renderMap();
  loadReplayPoints();
  void loadPois();
});

watch(showPois, () => {
  void loadPois();
});

watch(showFamousRoutes, () => {
  renderFamousRoutes();
});

watch(
  () => useAetherMap.value,
  (val) => {
    if (val) {
      destroyMap();
    } else {
      void renderMap();
    }
  },
);

function renderFamousRoutes() {
  if (!famousRoutesLayer) return;
  famousRoutesLayer.clearLayers();
  if (!showFamousRoutes.value) return;

  famousItalianRoutes.forEach((route) => {
    const color = route.color || "#3498db";
    const polyline = L.polyline(route.coords, {
      color,
      weight: 5,
      opacity: 0.85,
      dashArray: "8,6",
      lineCap: "round",
      lineJoin: "round",
    });
    polyline.bindPopup(`
         <strong style="font-size:1.05em">${escapeHtml(route.name)}</strong><br>
         <em>${escapeHtml(route.region)}</em><br><br>
         ${escapeHtml(route.description)}<br>
         <span style="color:#777">Distance: ${escapeHtml(route.distanceKm)} km · Elevation: +${escapeHtml(String(route.elevationGain))} m · ${escapeHtml(route.difficulty)}</span>
       `);
    if (famousRoutesLayer) {
      polyline.addTo(famousRoutesLayer);
    }
  });
}

function destroyMap() {
  if (map) {
    map.remove();
    map = null;
    layerGroup = null;
    tileLayer = null;
    famousRoutesLayer = null;
  }
}

async function loadRides() {
  loading.value = true;
  try {
    const data = await apiGet<{ rides: Ride[] }>("/api/v1/rides", {
      page: "1",
      page_size: "100",
      sort: "date",
    });
    const rides = (data.rides || []).filter(
      (ride): ride is Ride & { gps_points: GpsPoint[] } =>
        Array.isArray(ride.gps_points) && ride.gps_points.length > 0,
    );

    const BATCH = 10;
    const enriched: EnrichedRide[] = [];
    for (let i = 0; i < rides.length; i += BATCH) {
      const batch = rides.slice(i, i + BATCH);
      enriched.push(...batch.map((ride) => enrichRide(ride)));
      if (i + BATCH < rides.length) {
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    await Promise.allSettled(
      enriched
        .filter((ride) => weatherEnabled.value && ride.gps_points.length > 1)
        .map((ride) => loadWeather(ride)),
    );

    enriched.forEach((ride) => applyRideRisk(ride));
    enrichedRides.value = enriched;
    if (
      selectedRideId.value &&
      !enriched.some((ride) => ride.id === selectedRideId.value)
    ) {
      selectedRideId.value = null;
    }
    await nextTick();
    await renderMap();
    if (selectedRideId.value) loadReplayPoints();
    void loadPois();
  } catch (error) {
    console.error("ride map load failed", error);
    enrichedRides.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadWeather(ride: EnrichedRide): Promise<void> {
  try {
    if (!ride.center) {
      ride.weatherUnavailable = true;
      return;
    }
    const weatherData = await apiGet<{ score?: number; description?: string }>(
      "/api/v1/weather",
      {
        lat: String(Number(ride.center.lat.toFixed(5))),
        lon: String(Number(ride.center.lon.toFixed(5))),
        date: ride.date,
      },
    );
    ride.weather = weatherData;
    const wScore = weatherData.score;
    ride.weatherScore = wScore != null && Number.isFinite(wScore) ? wScore : 5;
    ride.weatherUnavailable = false;
  } catch (error: unknown) {
    ride.weather = null;
    ride.weatherScore = 5;
    ride.weatherUnavailable = true;
    ride.weatherError = error instanceof Error ? error.message : String(error);
  }
}

function enrichRide(ride: Ride & { gps_points: GpsPoint[] }): EnrichedRide {
  const gps_points = downsamplePoints(normalizePoints(ride.gps_points));
  const center = getCenter(gps_points);
  const segments = buildSegments(gps_points);
  const distance_m = segments.reduce(
    (sum, segment) => sum + segment.distance_m,
    0,
  );
  const elevation_gain_computed_m = segments.reduce(
    (sum, segment) => sum + Math.max(0, segment.elevation_delta_m),
    0,
  );

  return {
    ...ride,
    gps_points,
    center,
    segments,
    distance_m,
    elevation_gain_computed_m,
    weather: null,
    weatherScore: 5,
    weatherUnavailable: false,
    weatherError: "",
    overallRisk: 0,
    maxRisk: 0,
  };
}

function applyRideRisk(ride: EnrichedRide): EnrichedRide {
  const weatherScore = Number.isFinite(ride.weatherScore)
    ? ride.weatherScore
    : 5;
  ride.segments = ride.segments.map((segment) => {
    const gradeRisk = gradeRiskPercent(segment.grade);
    const weatherRisk = weatherRiskPercent(weatherScore);
    const speedRisk = speedRiskPercent(segment.speed ?? 0);
    let risk = 0;

    if (colorMode.value === "slope") {
      risk = gradeRisk;
    } else if (colorMode.value === "weather") {
      risk = weatherEnabled.value ? weatherRisk : 0;
    } else if (colorMode.value === "speed") {
      risk = speedRisk;
    } else {
      risk = Math.round((gradeRisk + weatherRisk) / 2);
    }

    return {
      ...segment,
      risk,
      color: riskColor(risk),
      gradeRisk,
      weatherRisk,
      speedRisk,
    };
  });

  const risks = ride.segments.map((segment) => segment.risk);
  ride.overallRisk = risks.length
    ? Math.round(risks.reduce((sum, value) => sum + value, 0) / risks.length)
    : 0;
  ride.maxRisk = risks.length ? Math.max(...risks) : 0;
  return ride;
}

function _segmentPopup(ride: EnrichedRide, segment: RideSegment): string {
  const gradeText =
    segment.grade >= 0
      ? `+${segment.grade.toFixed(1)}%`
      : `${segment.grade.toFixed(1)}%`;
  const weatherText = weatherEnabled.value
    ? `Weather: ${escapeHtml(segment.weatherRisk)}/100 · score ${escapeHtml(ride.weatherScore)}/10`
    : "Weather: disabled";
  return `
     <strong>${escapeHtml(ride.date)}</strong><br>
     Grade: ${escapeHtml(gradeText)}<br>
     Grade risk: ${escapeHtml(segment.gradeRisk)}/100<br>
     ${weatherText}<br>
     Segment risk: ${escapeHtml(segment.risk)}/100
   `;
}

function ridePopup(ride: EnrichedRide): string {
  const weatherLabel = ride.weatherUnavailable
    ? "unavailable"
    : `${ride.weatherScore}/10`;
  const weatherDescription = ride.weather?.description || "";
  const weatherText = weatherEnabled.value
    ? `Weather: ${escapeHtml(weatherLabel)} · ${escapeHtml(weatherDescription)}`
    : "Weather: disabled";
  return `
     <strong>Ride ${escapeHtml(ride.date)}</strong><br>
     Distance: ${escapeHtml(formatDistance(ride.distance_m))}<br>
     Elevation gain: ${escapeHtml(`${Math.round(ride.elevation_gain_computed_m)} m`)}<br>
     Average risk: ${escapeHtml(ride.overallRisk)}/100<br>
     ${weatherText}
   `;
}

onMounted(() => {
  loadRides();
});

onBeforeUnmount(() => {
  destroyMap();
});
</script>

<style scoped>
.map-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.map-subtitle {
  margin: 6px 0 0;
  color: var(--text-secondary);
  max-width: 760px;
}

.map-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(180px, 220px) auto;
  gap: 12px;
  align-items: end;
  margin-bottom: 14px;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.checkbox-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
}

.checkbox-control input {
  width: 16px;
  height: 16px;
}

.map-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.route-map {
  height: 560px;
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-secondary);
  position: relative;
}

@media (max-width: 768px) {
  .map-toolbar {
    grid-template-columns: 1fr;
  }

  .map-kpis {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }

  .route-map {
    height: 320px;
  }
}

.replay-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.replay-slider {
  flex: 1;
  accent-color: var(--accent);
}

.replay-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  min-width: 70px;
  text-align: right;
}
</style>
