<template>
  <div class="google-speed-map">
    <div
ref="mapEl" class="map-canvas" />
    <div
v-if="loading" class="map-loading">Loading speed map...</div>
    <div
v-if="!loading && !error" class="map-speed-legend">
      <div class="legend-title">Speed (km/h)</div>
      <div class="legend-bar">
        <span>{{ maxSpeed.toFixed(1) }}</span>
        <div class="bar-gradient" />
        <span>{{ minSpeed.toFixed(1) }}</span>
      </div>
    </div>
    <div v-if="error" class="map-error">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { apiGet } from "../utils/api";

const props = defineProps({
  rideId: { type: Number, required: true },
  apiKey: { type: String, default: "" },
});

const mapEl = ref(null);
const loading = ref(true);
const error = ref("");
const minSpeed = ref(0);
const maxSpeed = ref(35);

let googleMap = null;
let pathLayer = null;
let infoWindow = null;

function initMap(center, zoom = 14) {
  googleMap = new google.maps.Map(mapEl.value, {
    center,
    zoom,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    zoomControl: true,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: true,
  });

  infoWindow = new google.maps.InfoWindow();

  pathLayer = new google.maps.Data({ map: googleMap });
  pathLayer.setStyle((feature) => ({
    strokeColor: feature.getProperty("color"),
    strokeWeight: 5,
    strokeOpacity: 0.85,
  }));

  pathLayer.addListener("mouseover", (event) => {
    const spd = event.feature.getProperty("speed_kmh");
    if (spd != null && infoWindow) {
      infoWindow.setContent(
        "<div><strong>" + spd.toFixed(1) + " km/h</strong></div>",
      );
      infoWindow.setPosition(event.latLng);
      infoWindow.open(googleMap);
    }
  });

  pathLayer.addListener("mouseout", () => {
    if (infoWindow) infoWindow.close();
  });
}

async function loadSpeedPath() {
  loading.value = true;
  error.value = "";
  try {
    const data = await apiGet("/api/v1/rides/" + props.rideId + "/speed-path");
    minSpeed.value = data.min_speed || 0;
    maxSpeed.value = data.max_speed || 35;
    renderMap(data);
  } catch (err) {
    error.value = err.message || "Unable to load speed path";
  } finally {
    loading.value = false;
  }
}

function renderMap(data) {
  if (!mapEl.value || !data.segments || !data.segments.length) return;

  if (!googleMap) {
    initMap({ lat: data.center.lat, lng: data.center.lon }, 14);

    const first = data.segments[0];
    new google.maps.Marker({
      position: new google.maps.LatLng(first.start[0], first.start[1]),
      map: googleMap,
      label: { text: "S", color: "#fff", fontSize: "12px", fontWeight: "bold" },
      title: "Start",
    });

    const last = data.segments[data.segments.length - 1];
    new google.maps.Marker({
      position: new google.maps.LatLng(last.end[0], last.end[1]),
      map: googleMap,
      label: { text: "E", color: "#fff", fontSize: "12px", fontWeight: "bold" },
      title: "Finish",
    });
  }

  pathLayer.forEach((feature) => pathLayer.remove(feature));

  const features = [];
  data.segments.forEach((seg) => {
    const feature = new google.maps.Data.Feature();
    feature.setGeometry(
      new google.maps.Data.LineString([
        new google.maps.LatLng(seg.start[0], seg.start[1]),
        new google.maps.LatLng(seg.end[0], seg.end[1]),
      ]),
    );
    feature.setProperty("color", seg.color);
    feature.setProperty("speed_kmh", seg.speed_kmh);
    features.push(feature);
  });
  features.forEach((f) => pathLayer.add(f));

  const bounds = new google.maps.LatLngBounds();
  data.segments.forEach((seg) => {
    bounds.extend(new google.maps.LatLng(seg.start[0], seg.start[1]));
    bounds.extend(new google.maps.LatLng(seg.end[0], seg.end[1]));
  });
  googleMap.fitBounds(bounds, 30);
}

onMounted(() => {
  if (!props.apiKey) {
    loading.value = false;
    error.value = "Google Maps API key not configured";
    return;
  }

  const src = "https://maps.googleapis.com/maps/api/js?key=" + props.apiKey;
  const existing = document.querySelector(`script[src="${src}"]`);
  if (existing) {
    if (window.google?.maps) {
      loadSpeedPath();
    } else {
      existing.addEventListener("load", loadSpeedPath, { once: true });
    }
    return;
  }

  const script = document.createElement("script");
  script.src = src;
  script.async = true;
  script.defer = true;
  script.onload = () => loadSpeedPath();
  script.onerror = () => {
    loading.value = false;
    error.value = "Unable to load Google Maps JS API";
  };
  document.head.appendChild(script);
});

onBeforeUnmount(() => {
  if (infoWindow) infoWindow.close();
  googleMap = null;
  pathLayer = null;
  infoWindow = null;
});
</script>

<style scoped>
.google-speed-map {
  position: relative;
  width: 100%;
  height: 500px;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
}

.map-canvas {
  width: 100%;
  height: 100%;
  background: #e5e3df;
}

.map-loading,
.map-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 10px 20px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  color: var(--text-secondary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.map-error {
  color: #e74c3c;
}

.map-speed-legend {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-primary);
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  font-size: 0.8rem;
  min-width: 220px;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.legend-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.bar-gradient {
  flex: 1;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(
    to right,
    #ee3333,
    #ee8800,
    #ddbb00,
    #88cc00,
    #00cc44
  );
}
</style>
