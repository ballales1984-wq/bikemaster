<template>
  <section class="panel">
    <div class="map-header">
      <div>
        <h2>{{ t("poi.title") }}</h2>
        <p class="map-subtitle">
          {{ t("poi.subtitle") }}
        </p>
      </div>
      <button
        class="btn"
        :class="addMode ? 'btn-danger' : 'btn-primary'"
        :disabled="submitting"
        @click="toggleAddMode"
      >
        {{ addMode ? t("poi.cancel") : "➕ " + t("poi.addPoi") }}
      </button>
    </div>

    <div class="map-toolbar">
      <div class="type-filter">
        <button
          v-for="type in poiTypes"
          :key="type"
          class="type-chip"
          :class="{
            active: activeTypes.includes(type),
            muted: !activeTypes.includes(type),
          }"
          :style="{ '--chip': poiMeta[type].color }"
          @click="toggleType(type)"
        >
          <span class="chip-icon">{{ poiMeta[type].icon }}</span>
          {{ t("poi.type_" + type) }}
        </button>
      </div>

      <label class="control itinerary-control">
        <span>{{ t("poi.itinerary") }}</span>
        <select
          id="poi-itinerary"
          v-model="selectedItineraryId"
          class="form-input"
        >
          <option :value="null">{{ t("poi.noItinerary") }}</option>
          <option
v-for="ride in rides" :key="ride.id"
:value="ride.id"
>
            {{ ride.date }} · {{ formatDistanceKm(ride.distance_km) }}
          </option>
        </select>
      </label>
    </div>

    <div
v-if="addMode" class="add-hint">📍 {{ t("poi.clickMapHint") }}</div>

    <div
id="poi-map" ref="mapContainer"
class="poi-map"
/>

    <transition name="slide">
      <div
v-if="addMode && draft" class="poi-form"
>
        <h3>{{ t("poi.addPoi") }}</h3>
        <label class="form-label">
          {{ t("poi.name") }}
          <input
            id="poi-name"
            v-model.trim="form.name"
            class="form-input"
            maxlength="120"
          />
        </label>
        <label class="form-label">
          {{ t("poi.type") }}
          <select
            id="poi-type"
            v-model="form.type"
            class="form-input"
          >
            <option
v-for="type in poiTypes" :key="type"
:value="type"
>
              {{ poiMeta[type].icon }} {{ t("poi.type_" + type) }}
            </option>
          </select>
        </label>
        <label class="form-label">
          {{ t("poi.description") }}
          <textarea
            id="poi-description"
            v-model.trim="form.description"
            class="form-input"
            rows="3"
            maxlength="2000"
          />
        </label>
        <label class="form-label">
          {{ t("poi.photos") }}
          <input
            id="poi-photos"
            v-model.trim="form.photos"
            class="form-input"
            placeholder="https://..."
          >
        </label>
        <label class="form-label">
          {{ t("poi.videoUrl") }}
          <input
            id="poi-video-url"
            v-model.trim="form.video_url"
            class="form-input"
            placeholder="https://..."
          >
        </label>
        <label class="form-label">
          {{ t("poi.difficultyNote") }}
          <input
            id="poi-difficulty-note"
            v-model.trim="form.difficulty_note"
            class="form-input"
            maxlength="500"
          >
        </label>
        <label class="form-label">
          {{ t("poi.tags") }}
          <input
            id="poi-tags"
            v-model.trim="form.tags"
            class="form-input"
            placeholder="panorama, ombra"
          >
        </label>
        <div class="form-actions">
          <button
            class="btn btn-primary"
            :disabled="!canSubmit || submitting"
            @click="submitPoi"
          >
            {{ submitting ? t("poi.saving") : t("poi.save") }}
          </button>
          <button
class="btn btn-danger" @click="cancelDraft"
>
            {{ t("poi.cancel") }}
          </button>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
v-if="selectedPoi" class="modal-overlay"
@click.self="closeDetail"
>
        <div class="poi-modal">
          <button
class="modal-close" aria-label="close"
@click="closeDetail"
>
            ×
          </button>
          <div
            class="poi-modal-badge"
            :style="{ background: poiMeta[selectedPoi.type]?.color }"
          >
            {{ poiMeta[selectedPoi.type]?.icon }}
          </div>
          <h3>{{ selectedPoi.name }}</h3>
          <span class="poi-type-tag">{{
            t("poi.type_" + selectedPoi.type)
          }}</span>
          <p class="poi-desc">
            {{ selectedPoi.description }}
          </p>

          <div
            v-if="selectedPoi.photos && selectedPoi.photos.length"
            class="poi-photos"
          >
            <img
              v-for="(photo, i) in selectedPoi.photos"
              :key="i"
              :src="safeHttpUrl(photo)"
              :alt="selectedPoi.name"
              loading="lazy"
            />
          </div>

          <p
v-if="selectedPoi.video_url" class="poi-video"
>
            🎥
            <a
              :href="safeHttpUrl(selectedPoi.video_url)"
              target="_blank"
              rel="noopener"
              >Video</a
            >
          </p>
          <p
v-if="selectedPoi.difficulty_note" class="poi-note"
>
            ⚙️ {{ selectedPoi.difficulty_note }}
          </p>
          <div
            v-if="selectedPoi.tags && selectedPoi.tags.length"
            class="poi-tags"
          >
            <span
v-for="tag in selectedPoi.tags" :key="tag" class="poi-tag"
              >#{{ tag }}</span
            >
          </div>

          <div class="poi-meta">
            <span v-if="selectedPoi.distance_m != null">📏 {{ formatDistanceM(selectedPoi.distance_m) }}</span>
            <span>🧭 {{ selectedPoi.lat.toFixed(4) }},
              {{ selectedPoi.lon.toFixed(4) }}</span>
          </div>

          <button
            v-if="canDelete(selectedPoi)"
            class="btn btn-danger poi-delete"
            @click="removePoi(selectedPoi)"
          >
            🗑️ {{ t("poi.delete") }}
          </button>
          <p
v-else-if="selectedPoi.created_by" class="poi-owner-note"
>
            {{ t("poi.notOwner") }}
          </p>
        </div>
      </div>
    </transition>
  </section>
</template>

<script setup>
import "leaflet/dist/leaflet.css";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import { useAuthStore } from "../stores/auth";
import { useToast } from "../composables/useToast";
import L from "leaflet";
import { apiGet, apiPost, apiDelete, ApiError } from "../utils/api";
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from "../constants";

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();

const poiTypes = [
  "vista",
  "fontana",
  "ristoro",
  "bivio",
  "pericolo",
  "culturale",
  "tecnico",
];

const poiMeta = {
  vista: { color: "#2e86de", icon: "🌄" },
  fontana: { color: "#00b894", icon: "⛲" },
  ristoro: { color: "#e17055", icon: "🍝" },
  bivio: { color: "#fdcb6e", icon: "🛣️" },
  pericolo: { color: "#d63031", icon: "⚠️" },
  culturale: { color: "#9b59b6", icon: "🏛️" },
  tecnico: { color: "#636e72", icon: "🔧" },
};

const mapContainer = ref(null);
const pois = ref([]);
const rides = ref([]);
const activeTypes = ref([...poiTypes]);
const addMode = ref(false);
const draft = ref(null);
const submitting = ref(false);
const selectedPoi = ref(null);
const selectedItineraryId = ref(null);

const form = ref({
  name: "",
  description: "",
  type: "vista",
  photos: "",
  video_url: "",
  difficulty_note: "",
  tags: "",
});

let map = null;
let poiLayer = null;
let routeLayer = null;
let draftMarker = null;

const canSubmit = computed(
  () =>
    draft.value &&
    form.value.name.length >= 3 &&
    form.value.description.length > 0,
);

function formatDistanceKm(km) {
  if (!km) return "—";
  return `${Number(km).toFixed(1)} km`;
}
function formatDistanceM(m) {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`;
}
function safeHttpUrl(url) {
  if (typeof url !== "string") return "";
  return /^https?:\/\//i.test(url.trim()) ? url.trim() : "";
}

function markerIcon(type, highlighted = false) {
  const meta = poiMeta[type] || poiMeta.vista;
  return L.divIcon({
    className: "poi-div-icon",
    html: `<div class="poi-marker ${highlighted ? "poi-marker--hl" : ""}" style="background:${meta.color}">${meta.icon}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function createTileLayer() {
  return L.tileLayer(
    "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="http://cyclosm.org">CyclOSM</a>',
      maxZoom: 20,
    },
  );
}

function initMap() {
  if (!mapContainer.value) return;
  map = L.map(mapContainer.value, { preferCanvas: true }).setView(
    DEFAULT_MAP_CENTER,
    DEFAULT_MAP_ZOOM,
  );
  createTileLayer().addTo(map);
  poiLayer = L.layerGroup().addTo(map);
  routeLayer = L.layerGroup().addTo(map);
  routeLayer = L.layerGroup().addTo(map);
  map.on("click", onMapClick);
}

function renderPois() {
  if (!poiLayer) return;
  poiLayer.clearLayers();
  const itineraryId = selectedItineraryId.value;
  pois.value
    .filter((p) => activeTypes.value.includes(p.type))
    .forEach((p) => {
      const highlighted = itineraryId != null && p.itinerary_id === itineraryId;
      const marker = L.marker([p.lat, p.lon], {
        icon: markerIcon(p.type, highlighted),
      });
      marker.on("click", () => openDetail(p));
      marker.addTo(poiLayer);
    });
  if (map) map.invalidateSize();
}

async function loadPois() {
  try {
    const data = await apiGet("/api/v1/maps/pois");
    pois.value = data.pois || [];
    renderPois();
  } catch (err) {
    console.error("poi load failed", err);
  }
}

async function loadRides() {
  try {
    const data = await apiGet("/api/v1/rides", {
      page: 1,
      page_size: 100,
      sort: "date",
    });
    rides.value = (data.rides || []).filter(
      (r) => r.gps_points && r.gps_points.length > 1,
    );
  } catch (err) {
    console.error("rides load failed", err);
  }
}

function onMapClick(e) {
  if (!addMode.value) return;
  const { lat, lng } = e.latlng;
  draft.value = { lat, lon: lng };
  if (draftMarker) {
    draftMarker.setLatLng([lat, lng]);
  } else {
    draftMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: "poi-div-icon",
        html: '<div class="poi-marker poi-marker--draft">📍</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      }),
    }).addTo(map);
  }
}

function toggleAddMode() {
  addMode.value = !addMode.value;
  if (!addMode.value) cancelDraft();
}

function cancelDraft() {
  draft.value = null;
  if (draftMarker) {
    draftMarker.remove();
    draftMarker = null;
  }
  form.value = {
    name: "",
    description: "",
    type: "vista",
    photos: "",
    video_url: "",
    difficulty_note: "",
    tags: "",
  };
}

function toggleType(type) {
  const idx = activeTypes.value.indexOf(type);
  if (idx >= 0) activeTypes.value.splice(idx, 1);
  else activeTypes.value.push(type);
  renderPois();
}

async function submitPoi() {
  if (!canSubmit.value || !draft.value) return;
  submitting.value = true;
  const payload = {
    name: form.value.name,
    description: form.value.description,
    lat: draft.value.lat,
    lon: draft.value.lon,
    type: form.value.type,
    photos: form.value.photos
      ? form.value.photos
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [],
    video_url: form.value.video_url || null,
    difficulty_note: form.value.difficulty_note || null,
    tags: form.value.tags
      ? form.value.tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [],
    itinerary_id: selectedItineraryId.value || null,
  };
  try {
    const created = await apiPost("/api/v1/maps/pois", payload);
    pois.value.unshift(created);
    toast.success(t("poi.save") + " ✓");
    cancelDraft();
    addMode.value = false;
    renderPois();
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : "Errore";
    toast.error(msg);
  } finally {
    submitting.value = false;
  }
}

function openDetail(poi) {
  selectedPoi.value = poi;
}
function closeDetail() {
  selectedPoi.value = null;
}

function canDelete(poi) {
  return auth.user && (poi.created_by === auth.user.id || auth.isAdmin);
}

async function removePoi(poi) {
  if (!window.confirm(t("poi.confirmDelete"))) return;
  try {
    await apiDelete(`/api/v1/maps/pois/${poi.id}`);
    pois.value = pois.value.filter((p) => p.id !== poi.id);
    toast.success("POI eliminato");
    closeDetail();
    renderPois();
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : "Errore";
    toast.error(msg);
  }
}

function drawRoute() {
  if (!routeLayer) return;
  routeLayer.clearLayers();
  if (selectedItineraryId.value == null) return;
  const ride = rides.value.find((r) => r.id === selectedItineraryId.value);
  if (!ride || !ride.gps_points || ride.gps_points.length < 2) return;
  const points = ride.gps_points
    .map((p) => [
      Number(p.lat ?? p.latitude),
      Number(p.lon ?? p.lng ?? p.longitude),
    ])
    .filter(([la, lo]) => Number.isFinite(la) && Number.isFinite(lo));
  if (!points.length) return;
  const polyline = L.polyline(points, {
    color: "#1abc9c",
    weight: 5,
    opacity: 0.9,
  });
  polyline.addTo(routeLayer);
  if (map) map.fitBounds(polyline.getBounds().pad(0.1));
}

onMounted(async () => {
  initMap();
  await Promise.allSettled([loadPois(), loadRides()]);
});

onBeforeUnmount(() => {
  if (map) {
    map.off();
    map.remove();
    map = null;
    poiLayer = null;
    routeLayer = null;
    draftMarker = null;
  }
});

watch(selectedItineraryId, () => {
  drawRoute();
  renderPois();
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
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 14px;
}

.type-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--chip, var(--border));
  background: color-mix(
    in srgb,
    var(--chip, var(--border)) 16%,
    var(--bg-secondary)
  );
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.15s;
}

.type-chip.muted {
  opacity: 0.4;
  filter: grayscale(0.6);
}

.chip-icon {
  font-size: 1rem;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.itinerary-control {
  min-width: 220px;
}

.add-hint {
  background: var(--accent-gradient);
  color: var(--text-primary);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.poi-map {
  height: 560px;
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-secondary);
  position: relative;
  z-index: 0;
}

.poi-form {
  margin-top: 14px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.poi-form h3 {
  grid-column: 1 / -1;
  margin: 0 0 4px;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.form-input {
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  font: inherit;
}

.form-actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 10px;
}

.btn {
  padding: 9px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  transition: all 0.15s;
}

.btn-primary {
  background: var(--accent-gradient);
  border-color: transparent;
}

.btn-danger {
  background: var(--color-alert-bg, rgba(255, 51, 102, 0.18));
  border-color: var(--error, #ff3366);
  color: var(--error, #ff3366);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

:deep(.poi-marker) {
  width: 30px;
  height: 30px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
}

:deep(.poi-marker > *) {
  transform: rotate(45deg);
}

:deep(.poi-marker--hl) {
  outline: 3px solid #1abc9c;
  outline-offset: 2px;
}

:deep(.poi-marker--draft) {
  background: #f1c40f !important;
  outline: 3px solid #fff;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.poi-modal {
  position: relative;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  max-width: 460px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
}

.modal-close {
  position: absolute;
  top: 10px;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.6rem;
  cursor: pointer;
  line-height: 1;
}

.poi-modal-badge {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  margin-bottom: 10px;
}

.poi-type-tag {
  display: inline-block;
  font-size: 0.78rem;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 3px 10px;
  border-radius: 999px;
  margin-bottom: 10px;
}

.poi-desc {
  color: var(--text-primary);
  line-height: 1.5;
}

.poi-photos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
  margin: 12px 0;
}

.poi-photos img {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.poi-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}

.poi-tag {
  font-size: 0.78rem;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  padding: 3px 9px;
  border-radius: 999px;
}

.poi-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.poi-delete {
  margin-top: 16px;
}

.poi-owner-note {
  margin-top: 14px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .poi-form {
    grid-template-columns: 1fr;
  }
  .poi-map {
    height: 360px;
  }
}
</style>
