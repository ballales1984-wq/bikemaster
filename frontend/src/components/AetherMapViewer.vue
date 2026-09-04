<!-- Visualizzatore AetherMap: rendering WebGL2 di un globo cube-sphere con terrain, illuminazione e percorsi GPS.
      Props: points (list of lat/lon/speed), rideIds (ride IDs to load via API), colorBySpeed (color by speed).
      Events: none. UI: full-size canvas + HUD with statistics and mouse controls (drag/scroll). -->
<template>
  <div class="aethermap-viewer">
    <canvas ref="canvasRef" class="aethermap-canvas" />
    <div class="aethermap-hud">
      <b>AetherMap</b> · WebGL2 cube-sphere + terrain<br />
      trascina per ruotare · rotella per zoom · spazio = auto-rotazione<br />
      FPS: {{ fps }}<br />
      <template v-if="rideIds && rideIds.length">
        <span v-if="loading">carico scena…</span>
        <span v-else-if="error" class="aethermap-warn"
          >scena non disponibile</span
        >
        <template v-else-if="scene && scene.statistics">
          dist: {{ Math.round(scene.statistics.total_distance_m) }} m · avg:
          {{ scene.statistics.avg_speed_km_h }} km/h · &Delta;h:
          {{ Math.round(scene.statistics.total_elevation_gain_m) }} m
        </template>
      </template>
      <br />linea = percorso · verde = start · rosso = end · giallo = stats
      <div v-if="geoLayers.length" class="aethermap-layers">
        <span class="aethermap-layers-title">Layer:</span>
        <label
          v-for="layer in geoLayers"
          :key="layer.id"
          class="aethermap-layer-toggle"
        >
          <input
            type="checkbox"
            :checked="layer.visible"
            @change="toggleGeoLayer(layer.id)"
          />
          <span
            class="aethermap-layer-dot"
            :style="{ backgroundColor: layer.color }"
          ></span>
          {{ layer.name }}
          <span v-if="layer.loading" class="aethermap-layer-loading">…</span>
          <span v-else-if="layer.error" class="aethermap-warn">!</span>
          <span v-else-if="layer.data" class="aethermap-layer-count">
            {{ layer.data.features?.length ?? 0 }}
          </span>
        </label>
      </div>
      <div
        v-if="props.terrainEnriched && !firstRideId"
        class="aethermap-terrain"
      >
        <span class="aethermap-warn"
          >Seleziona una singola ride per il terrain enrichment</span
        >
      </div>
      <template v-else-if="props.terrainEnriched && terrain.loading">
        <span>carico terrain…</span>
      </template>
      <span
        v-else-if="props.terrainEnriched && terrain.error"
        class="aethermap-warn"
        >terrain non disponibile</span
      >
      <template v-else-if="props.terrainEnriched && terrainPoints.length">
        <br />terrain: slope avg {{ avgSlope }}% · ombra {{ shadePct }}% ·
        traffico {{ avgTraffic }}
      </template>

      <div v-if="activeRoutePoints.length > 1" class="aethermap-profile-overlay">
        <div class="aethermap-profile-header">
          <span>Profilo Altimetrico 3D</span>
          <span v-if="activeHoverPoint" class="aethermap-profile-meta">
            Alt: {{ Math.round(activeHoverPoint.altitude || 0) }} m
            <template v-if="activeHoverPoint.speed"> · {{ activeHoverPoint.speed.toFixed(1) }} km/h</template>
          </span>
        </div>
        <svg
          class="aethermap-profile-svg"
          viewBox="0 0 300 40"
          preserveAspectRatio="none"
          @mousemove="onProfileMouseMove"
          @mouseleave="internalHoverIndex = null"
        >
          <polyline :points="profileSvgPoints" fill="none" stroke="#00f3ff" stroke-width="2" />
          <circle
            v-if="activeHoverSvgCoords"
            :cx="activeHoverSvgCoords.x"
            :cy="activeHoverSvgCoords.y"
            r="4"
            fill="#00f3ff"
          />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import {
  useAetherMap,
  hexToRgb,
  type AetherScene,
} from "../composables/useAetherMap";
import { useAetherMapGeo } from "../composables/useAetherMapGeo";
import { useAetherMapTerrain } from "../composables/useAetherMapTerrain";
import { apiGet } from "../utils/api";

interface MapPoint {
  lat: number;
  lon: number;
  speed?: number;
  altitude?: number;
}

const DEMO_POINTS: MapPoint[] = [
  { lat: 45.0, lon: 9.0, speed: 20, altitude: 120 },
  { lat: 45.001, lon: 9.002, speed: 25, altitude: 122 },
  { lat: 45.002, lon: 9.004, speed: 30, altitude: 125 },
  { lat: 45.003, lon: 9.006, speed: 28, altitude: 123 },
];

const props = withDefaults(
  defineProps<{
    points?: MapPoint[];
    rideIds?: number[];
    colorBySpeed?: boolean;
    terrainEnriched?: boolean;
    demSource?: "auto" | "procedural" | "copernicus" | "lidar" | "osm";
    cameraMode?: "orbit" | "topDown" | "follow";
    sunHour?: number;
    verticalExaggeration?: number;
    wireframe?: boolean;
    hoverProgress?: number | null;
  }>(),
  {
    colorBySpeed: false,
    terrainEnriched: false,
    demSource: "auto",
    cameraMode: "orbit",
    sunHour: 12,
    verticalExaggeration: 1.0,
    wireframe: false,
    hoverProgress: null,
  },
);

const DEG = Math.PI / 180;
const EARTH_R = 6371000.0;
const GLOBE_RADIUS = 1.0;
const TERRAIN_SCALE = 1.0 / EARTH_R;
const SKIRT_HEIGHT = 0.0003;
const CAM_DIST = 2.7;
const CAM_DIST_MIN = 1.3;
const CAM_DIST_MAX = 8.0;
const CAM_FOV = (50 * Math.PI) / 180;
const CAM_NEAR = 0.1;
const CAM_FAR = 100.0;

type Vec3 = [number, number, number];

const canvasRef = ref<HTMLCanvasElement | null>(null);
let gl: WebGL2RenderingContext | null = null;
let rafId: number | null = null;
let resizeObserver: ResizeObserver | null = null;
let mounted = true;
let isVisible = true;
let observer: IntersectionObserver | null = null;
let onVisibilityChange: () => void = () => {};

const fps = ref(0);

let globePosBuf: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let globeNormBuf: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let globeIdxBuf: WebGLBuffer | null = null;
let globeIdxCount = 0;
let routeBuffer: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let pointBuffer: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let markerBuffer: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let riderMarkerBuffer: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let terrainBuffer: {
  buf: WebGLBuffer;
  count: number;
  mode: number;
  stride: number;
} | null = null;
let earthTexture: WebGLTexture | null = null;
let useEarthTexture = false;

let cachedProj = new Float32Array(16);
let cachedView = new Float32Array(16);
let cachedAspect = 0;
let cachedCamDist = -1;
let cachedYaw = 0;
let cachedPitch = 0;

let camDist = CAM_DIST;
let targetYaw = 0.6;
let targetPitch = 0.35;
let targetCamDist = CAM_DIST;
let animatingCamera = false;
let followIndex = 0;
let currentLOD = -1;
let globePending = false;

const firstRideId = computed(() => props.rideIds?.[0] ?? null);
const terrain = useAetherMapTerrain(
  firstRideId,
  computed(() => props.terrainEnriched ?? false),
);
const terrainPoints = computed(() => terrain.points.value);

const rideIdsRef = computed(() => props.rideIds ?? []);
const { scene, loading, error } = useAetherMap(rideIdsRef);
const { layers, visibleLayers, toggleLayer } = useAetherMapGeo();

const activeRoutePoints = computed<MapPoint[]>(() => {
  if (scene.value?.entities?.length) {
    const pts: MapPoint[] = [];
    for (const ent of scene.value.entities) {
      if (ent.tipo === "segment" && ent.pts?.length) {
        for (const p of ent.pts) {
          if (p.length >= 2) {
            pts.push({ lat: p[0], lon: p[1], speed: 20, altitude: p[2] ?? 0 });
          }
        }
      }
    }
    if (pts.length) return pts;
  }
  if (props.points && props.points.length) return props.points;
  return DEMO_POINTS;
});

const internalHoverIndex = ref<number | null>(null);
const activeHoverIndex = computed<number | null>(() => {
  if (props.hoverProgress != null && activeRoutePoints.value.length) {
    return Math.min(
      activeRoutePoints.value.length - 1,
      Math.max(
        0,
        Math.floor(props.hoverProgress * (activeRoutePoints.value.length - 1)),
      ),
    );
  }
  return internalHoverIndex.value;
});

const activeHoverPoint = computed<MapPoint | null>(() => {
  const idx = activeHoverIndex.value;
  if (idx == null || !activeRoutePoints.value[idx]) return null;
  return activeRoutePoints.value[idx];
});

const profileSvgPoints = computed(() => {
  const pts = activeRoutePoints.value;
  if (pts.length < 2) return "";
  let minElev = Infinity,
    maxElev = -Infinity;
  for (const p of pts) {
    const alt = p.altitude || 0;
    if (alt < minElev) minElev = alt;
    if (alt > maxElev) maxElev = alt;
  }
  const span = Math.max(1, maxElev - minElev);
  return pts
    .map((p, i) => {
      const x = ((i / (pts.length - 1)) * 300).toFixed(1);
      const y = (36 - (((p.altitude || 0) - minElev) / span) * 32).toFixed(1);
      return `${x},${y}`;
    })
    .join(" ");
});

const activeHoverSvgCoords = computed(() => {
  const idx = activeHoverIndex.value;
  const pts = activeRoutePoints.value;
  if (idx == null || pts.length < 2) return null;
  let minElev = Infinity,
    maxElev = -Infinity;
  for (const p of pts) {
    const alt = p.altitude || 0;
    if (alt < minElev) minElev = alt;
    if (alt > maxElev) maxElev = alt;
  }
  const span = Math.max(1, maxElev - minElev);
  const p = pts[idx];
  const x = (idx / (pts.length - 1)) * 300;
  const y = 36 - (((p.altitude || 0) - minElev) / span) * 32;
  return { x, y };
});

function onProfileMouseMove(e: MouseEvent) {
  const svg = e.currentTarget as SVGElement;
  const rect = svg.getBoundingClientRect();
  if (rect.width <= 0) return;
  const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  internalHoverIndex.value = Math.floor(
    pct * (activeRoutePoints.value.length - 1),
  );
}

const geoLayers = computed<
  Array<{
    id: string;
    name: string;
    type: "roads" | "cities" | "peaks" | "natural-earth";
    data: { type: "FeatureCollection"; features: any[] } | null;
    loading: boolean;
    error: string | null;
    visible: boolean;
    color: string;
  }>
>(() => Array.from(layers.value.values()));

const geoBufferMap: Map<
  string,
  { buf: WebGLBuffer; count: number; mode: number; stride: number }
> = new Map();

let _prevPointsKey = "";
let _geoDebounce: number | null = null;

class LRUCache<K, V> {
  private map = new Map<K, V>();
  constructor(private max: number) {}
  get(k: K): V | undefined {
    if (!this.map.has(k)) return undefined;
    const v = this.map.get(k)!;
    this.map.delete(k);
    this.map.set(k, v);
    return v;
  }
  set(k: K, v: V) {
    this.map.delete(k);
    this.map.set(k, v);
    while (this.map.size > this.max)
      this.map.delete(this.map.keys().next().value!);
  }
  clear() {
    this.map.clear();
  }
}

const terrainTileCache = new LRUCache<string, { h: Float32Array; ts: number }>(
  300,
);
const TILE_CACHE_TTL = 60 * 60 * 1000;

function geodeticToDirection(
  lat: number,
  lon: number,
): [number, number, number] {
  const la = lat * DEG;
  const lo = lon * DEG;
  const cl = Math.cos(la);
  return [cl * Math.cos(lo), cl * Math.sin(lo), Math.sin(la)];
}

function toDir(p: number[]): Vec3 {
  if (p.length >= 3 && Math.abs(p[0]) > 1e5) {
    const n = Math.hypot(p[0], p[1], p[2]) || 1;
    return [p[0] / n, p[1] / n, p[2] / n];
  }
  return geodeticToDirection(p[0], p[1]);
}

function slerpDir(a: Vec3, b: Vec3, t: number): Vec3 {
  let d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  d = Math.max(-1, Math.min(1, d));
  const theta = Math.acos(d);
  if (theta < 1e-5) return [a[0], a[1], a[2]];
  const s = Math.sin(theta);
  const w1 = Math.sin((1 - t) * theta) / s;
  const w2 = Math.sin(t * theta) / s;
  const v: Vec3 = [
    a[0] * w1 + b[0] * w2,
    a[1] * w1 + b[1] * w2,
    a[2] * w1 + b[2] * w2,
  ];
  const n = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / n, v[1] / n, v[2] / n];
}

function pushArc(arr: number[], a: Vec3, b: Vec3, col: Vec3): void {
  const d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const theta = Math.acos(Math.max(-1, Math.min(1, d)));
  const steps = Math.max(1, Math.min(64, Math.ceil(theta / (2 * DEG))));
  for (let k = 0; k <= steps; k++) {
    const pt = slerpDir(a, b, k / steps);
    arr.push(pt[0], pt[1], pt[2], col[0], col[1], col[2]);
  }
}

function speedColor(speed: number | undefined): [number, number, number] {
  if (speed == null) return [0.4, 40 / 255, 1.0];
  if (speed >= 35) return [0.0, 0.8, 0.27];
  if (speed >= 25) return [0.53, 0.8, 0.0];
  if (speed >= 15) return [0.87, 0.73, 0.0];
  if (speed >= 5) return [0.93, 0.53, 0.0];
  return [0.93, 0.2, 0.2];
}

function markerColor(tipo: string): [number, number, number] {
  if (tipo === "start") return [0.2, 0.9, 0.3];
  if (tipo === "end") return [0.95, 0.3, 0.3];
  return [1.0, 0.85, 0.2];
}

function toggleGeoLayer(id: string): void {
  toggleLayer(id);
  updateGeoBuffers();
}

function updateRiderMarkerBuffer(p: MapPoint | null) {
  if (riderMarkerBuffer && gl) {
    gl.deleteBuffer(riderMarkerBuffer.buf);
    riderMarkerBuffer = null;
  }
  if (!p || !gl) return;
  const dir = geodeticToDirection(p.lat, p.lon);
  const elev =
    (p.altitude || 0) * TERRAIN_SCALE * (props.verticalExaggeration ?? 1.0);
  const r = GLOBE_RADIUS + elev + 0.003;
  const col: Vec3 = [0.0, 1.0, 0.95];
  const data = [dir[0] * r, dir[1] * r, dir[2] * r, col[0], col[1], col[2]];
  riderMarkerBuffer = makeBuffer(new Float32Array(data), gl.POINTS, 6);
}

watch(activeHoverPoint, (pt) => {
  updateRiderMarkerBuffer(pt);
});

function focusOnRoute(): void {
  const pts = activeRoutePoints.value;
  if (!pts.length) return;
  let minLat = 90,
    maxLat = -90,
    minLon = 180,
    maxLon = -180;
  let sumLat = 0,
    sumLon = 0;
  for (const p of pts) {
    minLat = Math.min(minLat, p.lat);
    maxLat = Math.max(maxLat, p.lat);
    minLon = Math.min(minLon, p.lon);
    maxLon = Math.max(maxLon, p.lon);
    sumLat += p.lat;
    sumLon += p.lon;
  }
  const avgLat = sumLat / pts.length;
  const avgLon = sumLon / pts.length;
  const latSpan = Math.abs(maxLat - minLat);
  const lonSpan = Math.abs(maxLon - minLon);
  const maxSpan = Math.max(latSpan, lonSpan);

  targetCamDist = Math.max(
    CAM_DIST_MIN,
    Math.min(CAM_DIST_MAX, 1.4 + maxSpan * 10.0),
  );
  targetYaw = (avgLon * Math.PI) / 180 + Math.PI / 2;
  targetPitch = Math.max(-1.4, Math.min(1.4, (avgLat * Math.PI) / 180));
  animatingCamera = true;
}

defineExpose({ focusOnRoute });

const avgSlope = computed(() => {
  const pts = terrainPoints.value;
  if (!pts.length) return 0;
  return (pts.reduce((s, p) => s + (p.slope_pct || 0), 0) / pts.length).toFixed(
    1,
  );
});
const shadePct = computed(() => {
  const pts = terrainPoints.value;
  if (!pts.length) return 0;
  const shaded = pts.filter((p) => p.shade).length;
  return ((shaded / pts.length) * 100).toFixed(0);
});
const avgTraffic = computed(() => {
  const pts = terrainPoints.value;
  if (!pts.length) return 0;
  return (
    pts.reduce((s, p) => s + (p.traffic_level || 0), 0) / pts.length
  ).toFixed(2);
});

watch(
  () => props.demSource,
  () => {
    terrainTileCache.clear();
    currentLOD = -1;
  },
);

watch(
  () => props.terrainEnriched,
  (val) => {
    if (val && firstRideId.value) terrain.reload();
  },
);

function normalize3(v: Vec3): Vec3 {
  const n = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / n, v[1] / n, v[2] / n];
}
function sub3(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}
function cross3(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[2],
  ];
}
function dot3(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
function camEye(yaw: number, pitch: number): Vec3 {
  const cy = Math.cos(yaw),
    sy = Math.sin(yaw);
  const cp = Math.cos(pitch),
    sp = Math.sin(pitch);
  return [camDist * cy * cp, camDist * sp, camDist * sy * cp];
}
function mat4Perspective(
  fov: number,
  aspect: number,
  near: number,
  far: number,
): Float32Array {
  const f = 1 / Math.tan(fov / 2);
  const nf = 1 / (near - far);
  return new Float32Array([
    f / aspect,
    0,
    0,
    0,
    0,
    f,
    0,
    0,
    0,
    0,
    (far + near) * nf,
    -1,
    0,
    0,
    2 * far * near * nf,
    0,
  ]);
}
function mat4LookAt(eye: Vec3, center: Vec3, up: Vec3): Float32Array {
  const z = normalize3(sub3(eye, center));
  const x = normalize3(cross3(up, z));
  const y = cross3(z, x);
  return new Float32Array([
    x[0],
    y[0],
    z[0],
    0,
    x[1],
    y[1],
    z[1],
    0,
    x[2],
    y[2],
    z[2],
    0,
    -dot3(x, eye),
    -dot3(y, eye),
    -dot3(z, eye),
    1,
  ]);
}

function faceDir(f: number, u: number, v: number): Vec3 {
  let d: Vec3;
  if (f === 0) d = [1, u, v];
  else if (f === 1) d = [-1, u, v];
  else if (f === 2) d = [u, 1, v];
  else if (f === 3) d = [u, -1, v];
  else if (f === 4) d = [u, v, 1];
  else d = [u, v, -1];
  const n = Math.hypot(d[0], d[1], d[2]) || 1;
  return [d[0] / n, d[1] / n, d[2] / n];
}

function makeBuffer(
  data: ArrayBufferView,
  mode: number,
  stride: number,
): { buf: WebGLBuffer; count: number; mode: number; stride: number } | null {
  if (!gl) return null;
  const b = gl.createBuffer();
  if (!b) return null;
  gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  const byteStride = stride * 4;
  return {
    buf: b,
    count: data.byteLength / byteStride,
    mode,
    stride: byteStride,
  };
}

function makeIndexBuffer(data: Uint32Array): WebGLBuffer | null {
  if (!gl) return null;
  const b = gl.createBuffer();
  if (!b) return null;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, data, gl.STATIC_DRAW);
  return b;
}

function draw(
  buf: { buf: WebGLBuffer; count: number; mode: number; stride: number },
  posLoc: number,
  colorLoc: number,
) {
  if (!gl) return;
  gl.bindBuffer(gl.ARRAY_BUFFER, buf.buf);
  gl.enableVertexAttribArray(posLoc);
  gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, buf.stride, 0);
  if (buf.stride >= 24) {
    gl.enableVertexAttribArray(colorLoc);
    gl.vertexAttribPointer(colorLoc, 3, gl.FLOAT, false, buf.stride, 12);
  } else {
    gl.disableVertexAttribArray(colorLoc);
  }
  gl.drawArrays(buf.mode, 0, buf.count);
}

function drawIndexed(idxBuf: WebGLBuffer, count: number, mode: number) {
  if (!gl) return;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
  gl.drawElements(mode, count, gl.UNSIGNED_INT, 0);
}

function updateDynamicBuffers(points: MapPoint[], colorBySpeed: boolean) {
  if (routeBuffer && gl) {
    gl.deleteBuffer(routeBuffer.buf);
    routeBuffer = null;
  }
  if (pointBuffer && gl) {
    gl.deleteBuffer(pointBuffer.buf);
    pointBuffer = null;
  }
  if (markerBuffer && gl) {
    gl.deleteBuffer(markerBuffer.buf);
    markerBuffer = null;
  }
  if (!gl) return;

  const routeData: number[] = [];
  const pointData: number[] = [];
  let prev: Vec3 | null = null;
  for (const p of points) {
    const dir = geodeticToDirection(p.lat, p.lon);
    const col: Vec3 = colorBySpeed ? speedColor(p.speed) : [0.95, 0.85, 0.25];
    const elev = (p.altitude || 0) * TERRAIN_SCALE;
    const r = GLOBE_RADIUS + elev;
    pointData.push(dir[0] * r, dir[1] * r, dir[2] * r, col[0], col[1], col[2]);
    if (prev)
      pushArc(routeData, prev, [dir[0] * r, dir[1] * r, dir[2] * r], col);
    prev = [dir[0] * r, dir[1] * r, dir[2] * r];
  }
  if (routeData.length)
    routeBuffer = makeBuffer(new Float32Array(routeData), gl.LINE_STRIP, 6);
  if (pointData.length)
    pointBuffer = makeBuffer(new Float32Array(pointData), gl.POINTS, 6);
}

function updateSceneBuffers(sc: AetherScene) {
  if (routeBuffer && gl) {
    gl.deleteBuffer(routeBuffer.buf);
    routeBuffer = null;
  }
  if (pointBuffer && gl) {
    gl.deleteBuffer(pointBuffer.buf);
    pointBuffer = null;
  }
  if (markerBuffer && gl) {
    gl.deleteBuffer(markerBuffer.buf);
    markerBuffer = null;
  }
  if (!gl) return;

  const routeData: number[] = [];
  const markerData: number[] = [];
  for (const ent of sc.entities) {
    if (ent.tipo === "segment") {
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        const segColor = ent.colors && ent.colors[i] ? ent.colors[i] : ent.char;
        const col = hexToRgb(segColor);
        const h0 =
          (ent.pts[i] && ent.pts[i].length >= 3 ? ent.pts[i][2] || 0 : 0) *
          TERRAIN_SCALE;
        const h1 =
          (ent.pts[i + 1] && ent.pts[i + 1].length >= 3
            ? ent.pts[i + 1][2] || 0
            : 0) * TERRAIN_SCALE;
        const a = [
          pts[i][0] * (GLOBE_RADIUS + h0),
          pts[i][1] * (GLOBE_RADIUS + h0),
          pts[i][2] * (GLOBE_RADIUS + h0),
        ];
        const b = [
          pts[i + 1][0] * (GLOBE_RADIUS + h1),
          pts[i + 1][1] * (GLOBE_RADIUS + h1),
          pts[i + 1][2] * (GLOBE_RADIUS + h1),
        ];
        pushArc(routeData, a as Vec3, b as Vec3, col);
      }
    } else if (
      ent.tipo === "start" ||
      ent.tipo === "end" ||
      ent.tipo === "stats"
    ) {
      const p = ent.pts[0];
      if (!p) continue;
      const rel = toDir(p);
      const h = (p.length >= 3 ? p[2] || 0 : 0) * TERRAIN_SCALE;
      const r = GLOBE_RADIUS + h;
      markerData.push(
        rel[0] * r,
        rel[1] * r,
        rel[2] * r,
        ...markerColor(ent.tipo),
      );
    } else {
      const col = hexToRgb(ent.char);
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        const h0 =
          (ent.pts[i] && ent.pts[i].length >= 3 ? ent.pts[i][2] || 0 : 0) *
          TERRAIN_SCALE;
        const h1 =
          (ent.pts[i + 1] && ent.pts[i + 1].length >= 3
            ? ent.pts[i + 1][2] || 0
            : 0) * TERRAIN_SCALE;
        const a = [
          pts[i][0] * (GLOBE_RADIUS + h0),
          pts[i][1] * (GLOBE_RADIUS + h0),
          pts[i][2] * (GLOBE_RADIUS + h0),
        ];
        const b = [
          pts[i + 1][0] * (GLOBE_RADIUS + h1),
          pts[i + 1][1] * (GLOBE_RADIUS + h1),
          pts[i + 1][2] * (GLOBE_RADIUS + h1),
        ];
        pushArc(routeData, a as Vec3, b as Vec3, col);
      }
    }
  }
  if (routeData.length)
    routeBuffer = makeBuffer(new Float32Array(routeData), gl.LINE_STRIP, 6);
  if (markerData.length)
    markerBuffer = makeBuffer(new Float32Array(markerData), gl.POINTS, 6);
}

function geoColorForType(tipo: string): Vec3 {
  if (tipo === "strada") return [0.95, 0.78, 0.22];
  if (tipo === "citta") return [0.28, 0.92, 0.42];
  if (tipo === "montagna") return [0.92, 0.32, 0.28];
  if (tipo === "costa") return [0.15, 0.55, 0.95];
  if (tipo === "confine") return [0.6, 0.55, 0.5];
  return [0.8, 0.8, 0.8];
}

function normalizeGeoColor(raw: unknown, fallback: Vec3): Vec3 {
  if (Array.isArray(raw) && raw.length >= 3) {
    return [Number(raw[0]), Number(raw[1]), Number(raw[2])];
  }
  if (typeof raw === "string") {
    return hexToRgb(raw);
  }
  return fallback;
}

async function updateGeoBuffers() {
  if (!mounted || !gl) return;
  for (const [, buf] of geoBufferMap) {
    if (buf && gl) gl.deleteBuffer(buf.buf);
  }
  geoBufferMap.clear();
  if (!gl) return;

  const BATCH = 500;
  for (let l = 0; l < visibleLayers.value.length; l++) {
    if (!mounted || !gl) return;
    const layer = visibleLayers.value[l];
    if (!layer.data) continue;
    const features = layer.data.features || [];
    const lineData: number[] = [];
    const pointData: number[] = [];

    for (let i = 0; i < features.length; i += BATCH) {
      if (!mounted || !gl) return;
      const batch = features.slice(i, i + BATCH);
      for (const feature of batch) {
        const geom = feature.geometry;
        if (!geom) continue;
        const coords = geom.coordinates as unknown[] | undefined;
        if (!coords || !coords.length) continue;

        if (geom.type === "LineString") {
          const pts: Vec3[] = [];
          for (const c of coords) {
            const coord = c as number[];
            if (!Array.isArray(coord) || coord.length < 2) continue;
            const d = geodeticToDirection(coord[1], coord[0]);
            const h = (coord[2] || 0) * TERRAIN_SCALE;
            const r = GLOBE_RADIUS + h;
            pts.push([d[0] * r, d[1] * r, d[2] * r]);
          }
          if (pts.length >= 2) {
            const col: Vec3 = normalizeGeoColor(
              feature.properties?.color,
              geoColorForType(
                (feature.properties?.tipo as string | undefined) || layer.type,
              ),
            );
            for (let j = 0; j + 1 < pts.length; j++) {
              pushArc(lineData, pts[j], pts[j + 1], col);
            }
          }
        } else if (geom.type === "Point") {
          if (!Array.isArray(coords) || coords.length < 2) continue;
          const coord = coords as number[];
          const d = geodeticToDirection(coord[1], coord[0]);
          const h = (coord[2] || 0) * TERRAIN_SCALE;
          const r = GLOBE_RADIUS + h;
          const col: Vec3 = normalizeGeoColor(
            feature.properties?.color,
            geoColorForType(
              (feature.properties?.tipo as string | undefined) || layer.type,
            ),
          );
          pointData.push(d[0] * r, d[1] * r, d[2] * r, ...col);
        } else if (geom.type === "Polygon" || geom.type === "MultiPolygon") {
          const rings: number[][][] = [];
          if (geom.type === "Polygon") {
            const ringsRaw = coords as number[][][];
            for (const ring of ringsRaw) {
              if (Array.isArray(ring) && ring.length) rings.push(ring);
            }
          } else {
            const polysRaw = coords as number[][][][];
            for (const poly of polysRaw) {
              if (Array.isArray(poly) && poly.length)
                rings.push(poly[0] as number[][]);
            }
          }
          const col: Vec3 = normalizeGeoColor(
            feature.properties?.color,
            [0.18, 0.45, 0.18],
          );
          for (const ring of rings) {
            const pts: Vec3[] = [];
            for (const c of ring) {
              if (!Array.isArray(c) || c.length < 2) continue;
              const d = geodeticToDirection(c[1], c[0]);
              const h = ((c[2] || 0) * TERRAIN_SCALE) + 0.002;
              const r = GLOBE_RADIUS + h;
              pts.push([d[0] * r, d[1] * r, d[2] * r]);
            }
            for (let j = 0; j + 1 < pts.length; j++) {
              pushArc(lineData, pts[j], pts[j + 1], col);
            }
            if (pts.length >= 3) {
              for (let j = 1; j + 1 < pts.length; j++) {
                const a = pts[0];
                const b = pts[j];
                const c = pts[j + 1];
                const fillCol: Vec3 = [
                  col[0] * 0.85,
                  col[1] * 0.85,
                  col[2] * 0.85,
                ];
                const cxv = (a[0] + b[0] + c[0]) / 3;
                const cyv = (a[1] + b[1] + c[1]) / 3;
                const czv = (a[2] + b[2] + c[2]) / 3;
                pointData.push(cxv, cyv, czv, fillCol[0], fillCol[1], fillCol[2]);
              }
            }
          }
        }
      }
      if (i + BATCH < features.length) {
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    if (lineData.length) {
      const buf = makeBuffer(new Float32Array(lineData), gl.LINE_STRIP, 6);
      if (buf) geoBufferMap.set(`line-${layer.id}`, buf);
    }
    if (pointData.length) {
      const buf = makeBuffer(new Float32Array(pointData), gl.POINTS, 6);
      if (buf) geoBufferMap.set(`point-${layer.id}`, buf);
    }

    if (l + 1 < visibleLayers.value.length) {
      await new Promise((r) => setTimeout(r, 0));
    }
  }
}

async function fetchTerrainTile(
  minLat: number,
  maxLat: number,
  minLon: number,
  maxLon: number,
  resolution: number,
  face: number = -1,
): Promise<Float32Array | null> {
  const source = props.demSource || "auto";
  const key = `${face}_${source}_${minLat.toFixed(1)}_${maxLat.toFixed(1)}_${minLon.toFixed(1)}_${maxLon.toFixed(1)}_${resolution}`;
  const cached = terrainTileCache.get(key);
  if (cached && Date.now() - cached.ts < TILE_CACHE_TTL) {
    return cached.h;
  }
  try {
    const data = await apiGet<{ heights: number[] }>(
      "/api/v1/aethermap/terrain",
      {
        min_lat: String(minLat),
        max_lat: String(maxLat),
        min_lon: String(minLon),
        max_lon: String(maxLon),
        resolution: String(resolution),
        source: source,
      },
      { timeoutMs: 1500 },
    );
    const heights = new Float32Array(data.heights);
    terrainTileCache.set(key, { h: heights, ts: Date.now() });
    return heights;
  } catch {
    return null;
  }
}

function sampleTerrainTile(
  tileHeights: Float32Array,
  resolution: number,
  u: number,
  v: number,
): number {
  const x = u * (resolution - 1);
  const y = v * (resolution - 1);
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const x1 = Math.min(x0 + 1, resolution - 1);
  const y1 = Math.min(y0 + 1, resolution - 1);
  const fx = x - x0;
  const fy = y - y0;
  const h00 = tileHeights[y0 * resolution + x0] || 0;
  const h10 = tileHeights[y0 * resolution + x1] || 0;
  const h01 = tileHeights[y1 * resolution + x0] || 0;
  const h11 = tileHeights[y1 * resolution + x1] || 0;
  const h0 = h00 + (h10 - h00) * fx;
  const h1 = h01 + (h11 - h01) * fx;
  return h0 + (h1 - h0) * fy;
}

function faceLatLonBounds(face: number): {
  minLat: number;
  maxLat: number;
  minLon: number;
  maxLon: number;
} {
  const corners = [
    faceDir(face, -1, -1),
    faceDir(face, 1, -1),
    faceDir(face, -1, 1),
    faceDir(face, 1, 1),
  ];
  let minLat = Infinity,
    maxLat = -Infinity;
  const lons: number[] = [];
  for (const c of corners) {
    const { lat, lon } = latLonFromDir(c);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    lons.push(lon);
  }

  if (maxLat - minLat < 1e-3) {
    return {
      minLat: face === 5 ? -90 : minLat,
      maxLat: face === 4 ? 90 : maxLat,
      minLon: -180,
      maxLon: 180,
    };
  }

  const unwrapped = [lons[0]];
  for (let i = 1; i < lons.length; i++) {
    let diff = lons[i] - unwrapped[i - 1];
    if (diff > 180) unwrapped.push(lons[i] - 360);
    else if (diff < -180) unwrapped.push(lons[i] + 360);
    else unwrapped.push(lons[i]);
  }
  let minLon = Math.min(...unwrapped);
  let maxLon = Math.max(...unwrapped);
  if (minLon < -180) {
    minLon += 360;
    maxLon += 360;
  } else if (maxLon > 180) {
    minLon -= 360;
    maxLon -= 360;
  }
  return { minLat, maxLat, minLon, maxLon };
}

function latLonFromDir(dir: Vec3): { lat: number; lon: number } {
  const n = Math.hypot(dir[0], dir[1], dir[2]) || 1;
  const x = dir[0] / n,
    y = dir[1] / n,
    z = dir[2] / n;
  const lat = Math.asin(Math.max(-1, Math.min(1, z))) / DEG;
  const lon = Math.atan2(y, x) / DEG;
  return { lat, lon };
}

function buildTerrainMesh(
  tiles: (Float32Array | null)[],
  N: number,
): {
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
  vertexCount: number;
} {
  const verts: Vec3[][][] = [];
  const skirtVerts: Vec3[][][] = [];

  for (let f = 0; f < 6; f++) {
    verts[f] = [];
    skirtVerts[f] = [];
    const bounds = faceLatLonBounds(f);
    const tile = tiles[f];
    for (let i = 0; i <= N; i++) {
      verts[f][i] = [];
      skirtVerts[f][i] = [];
      for (let j = 0; j <= N; j++) {
        const u = (i / N) * 2 - 1;
        const v = (j / N) * 2 - 1;
        const dir = faceDir(f, u, v);
        const { lat, lon } = latLonFromDir(dir);
        let terrainH = 0;
        if (tile) {
          let wrappedLon = lon;
          const span = bounds.maxLon - bounds.minLon;
          while (wrappedLon < bounds.minLon) wrappedLon += 360;
          while (wrappedLon > bounds.minLon + span) wrappedLon -= 360;
          const tileU = (wrappedLon - bounds.minLon) / span;
          const tileV =
            1.0 - (lat - bounds.minLat) / (bounds.maxLat - bounds.minLat);
          const clampedU = Math.max(0, Math.min(1, tileU));
          const clampedV = Math.max(0, Math.min(1, tileV));
          terrainH = sampleTerrainTile(tile, N, clampedU, clampedV);
        }
        const scaledH = terrainH * TERRAIN_SCALE;
        const r = GLOBE_RADIUS + scaledH;
        const pos: Vec3 = [dir[0] * r, dir[1] * r, dir[2] * r];
        verts[f][i][j] = pos;

        if (i === 0 || i === N || j === 0 || j === N) {
          const sk: Vec3 = [
            dir[0] * (r + SKIRT_HEIGHT),
            dir[1] * (r + SKIRT_HEIGHT),
            dir[2] * (r + SKIRT_HEIGHT),
          ];
          skirtVerts[f][i][j] = sk;
        } else {
          skirtVerts[f][i][j] = pos;
        }
      }
    }
  }

  const positions: number[] = [];
  const normals: number[] = [];
  const indices: number[] = [];
  let vertexCount = 0;

  function addVertex(pos: Vec3, norm: Vec3) {
    positions.push(pos[0], pos[1], pos[2]);
    normals.push(norm[0], norm[1], norm[2]);
    return vertexCount++;
  }

  for (let f = 0; f < 6; f++) {
    const faceVerts: number[][] = [];
    const faceSkirt: number[][] = [];

    for (let i = 0; i <= N; i++) {
      faceVerts[i] = [];
      faceSkirt[i] = [];
      for (let j = 0; j <= N; j++) {
        const pos = verts[f][i][j];
        const sk = skirtVerts[f][i][j];
        faceVerts[i][j] = addVertex(pos, normalize3(pos));
        faceSkirt[i][j] = addVertex(sk, normalize3(pos));
      }
    }

    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const a = faceVerts[i][j];
        const b = faceVerts[i + 1][j];
        const c = faceVerts[i][j + 1];
        const d = faceVerts[i + 1][j + 1];
        indices.push(a, b, c, b, d, c);
      }
    }

    for (let i = 0; i < N; i++) {
      const a = faceVerts[i][0];
      const b = faceVerts[i + 1][0];
      const sa = faceSkirt[i][0];
      const sb = faceSkirt[i + 1][0];
      indices.push(a, sa, b, b, sa, sb);
      const c = faceVerts[i][N];
      const d = faceVerts[i + 1][N];
      const sc = faceSkirt[i][N];
      const sd = faceSkirt[i + 1][N];
      indices.push(c, sc, d, d, sc, sd);
    }
    for (let j = 0; j < N; j++) {
      const a = faceVerts[0][j];
      const b = faceVerts[0][j + 1];
      const sa = faceSkirt[0][j];
      const sb = faceSkirt[0][j + 1];
      indices.push(a, sa, b, b, sa, sb);
      const c = faceVerts[N][j];
      const d = faceVerts[N][j + 1];
      const sc = faceSkirt[N][j];
      const sd = faceSkirt[N][j + 1];
      indices.push(c, sc, d, d, sc, sd);
    }
  }

  return {
    positions: new Float32Array(positions),
    normals: new Float32Array(normals),
    indices: new Uint32Array(indices),
    vertexCount,
  };
}

function buildProceduralGlobeBuffers(N: number) {
  return buildTerrainMesh(
    Array.from({ length: 6 }, () => null),
    N,
  );
}

async function buildGlobeBuffers(N: number): Promise<{
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
  vertexCount: number;
}> {
  const tilePromises = Array.from({ length: 6 }, (_, f) => {
    const bounds = faceLatLonBounds(f);
    return fetchTerrainTile(
      bounds.minLat,
      bounds.maxLat,
      bounds.minLon,
      bounds.maxLon,
      N,
      f,
    );
  });
  const tiles = await Promise.all(tilePromises);
  return buildTerrainMesh(tiles, N);
}

const isMobileDevice = (): boolean => {
  if (typeof navigator === "undefined") return false;
  return /Android|iPhone|iPad|iPod|Opera Mini|IEMobile|WPDesktop/i.test(
    navigator.userAgent,
  );
};

const MOBILE_LOD_OFFSET = isMobileDevice() ? 2 : 0;

function getLODResolution(camDist: number): number {
  let res = 0;
  if (camDist < 2.0) res = 48;
  else if (camDist < 3.5) res = 32;
  else if (camDist < 5.0) res = 20;
  else if (camDist < 6.5) res = 12;
  else res = 8;
  return Math.max(8, res - MOBILE_LOD_OFFSET);
}

const VS = `#version 300 es
in vec3 aPosition;
in vec3 aNormal;
in vec3 aColor;
uniform mat4 uProj;
uniform mat4 uView;
uniform vec3 uEyePos;
uniform float uPointSize;
uniform bool uUseVertexColor;
out vec3 vNormal;
out vec3 vViewPos;
out vec2 vLatLon;
out float vElevation;
out vec3 vColor;
void main() {
  vec4 viewPos = uView * vec4(aPosition, 1.0);
  gl_Position = uProj * viewPos;
  gl_PointSize = uPointSize;
  vNormal = aNormal;
  vViewPos = viewPos.xyz;
  vec3 n = normalize(aPosition);
  vLatLon = vec2(degrees(asin(clamp(n.z, -1.0, 1.0))), degrees(atan(n.y, n.x)));
  vElevation = clamp((length(aPosition) - 1.0) * 1600.0, 0.0, 1.0);
  vColor = aColor;
}`;

const FS = `#version 300 es
precision mediump float;
in vec3 vNormal;
in vec3 vViewPos;
in vec2 vLatLon;
in float vElevation;
in vec3 vColor;
uniform vec3 uSunDir;
uniform vec3 uEyePos;
uniform bool uUseVertexColor;
uniform sampler2D uEarthTexture;
uniform bool uUseEarthTexture;
out vec4 outColor;
void main() {
  vec3 baseColor;
  if (uUseEarthTexture) {
    float u = (vLatLon.y + 180.0) / 360.0;
    float v = (90.0 - vLatLon.x) / 180.0;
    baseColor = texture(uEarthTexture, vec2(u, v)).rgb;
  } else {
    baseColor = vColor;
  }
  vec3 n = normalize(vNormal);
  vec3 sun = normalize(uSunDir);
  float d = max(dot(n, sun), 0.0);
  float ambient = 0.25;
  vec3 lit = baseColor * (ambient + d * 0.75);
  vec3 viewDir = normalize(-vViewPos);
  float rim = 1.0 - max(dot(viewDir, n), 0.0);
  rim = pow(rim, 3.5);
  lit += vec3(0.2, 0.4, 0.8) * rim * 0.25;
  outColor = vec4(lit, 1.0);
}`;

async function loadEarthTexture(glCtx: WebGL2RenderingContext) {
  try {
    const resp = await fetch("/api/v1/aethermap/earth-texture.png", {
      headers: { Accept: "image/png" },
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const bitmap = await createImageBitmap(blob);
    if (earthTexture) glCtx.deleteTexture(earthTexture);
    earthTexture = glCtx.createTexture();
    glCtx.bindTexture(glCtx.TEXTURE_2D, earthTexture);
    glCtx.texParameteri(glCtx.TEXTURE_2D, glCtx.TEXTURE_WRAP_S, glCtx.REPEAT);
    glCtx.texParameteri(
      glCtx.TEXTURE_2D,
      glCtx.TEXTURE_WRAP_T,
      glCtx.CLAMP_TO_EDGE,
    );
    glCtx.texParameteri(
      glCtx.TEXTURE_2D,
      glCtx.TEXTURE_MIN_FILTER,
      glCtx.LINEAR,
    );
    glCtx.texParameteri(
      glCtx.TEXTURE_2D,
      glCtx.TEXTURE_MAG_FILTER,
      glCtx.LINEAR,
    );
    glCtx.texImage2D(
      glCtx.TEXTURE_2D,
      0,
      glCtx.RGBA,
      glCtx.RGBA,
      glCtx.UNSIGNED_BYTE,
      bitmap,
    );
    useEarthTexture = true;
  } catch {
    useEarthTexture = false;
  }
}

onMounted(async () => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const canvasEl = canvas as HTMLCanvasElement;

  resizeObserver?.disconnect();

  const glCtx = canvasEl.getContext("webgl2", { antialias: true });
  if (!glCtx) {
    console.error("WebGL2 non disponibile in questo browser.");
    return;
  }
  gl = glCtx;
  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);
  gl.cullFace(gl.BACK);
  gl.enable(gl.POLYGON_OFFSET_FILL);
  gl.polygonOffset(1.0, 1.0);

  function compile(type: number, src: string): WebGLShader {
    const s = gl!.createShader(type)!;
    gl!.shaderSource(s, src);
    gl!.compileShader(s);
    if (!gl!.getShaderParameter(s, gl!.COMPILE_STATUS)) {
      throw new Error(gl!.getShaderInfoLog(s) ?? "shader compile failed");
    }
    return s;
  }

  const prog = gl!.createProgram()!;
  gl!.attachShader(prog, compile(gl!.VERTEX_SHADER, VS));
  gl!.attachShader(prog, compile(gl!.FRAGMENT_SHADER, FS));
  gl!.linkProgram(prog);
  if (!gl!.getProgramParameter(prog, gl!.LINK_STATUS)) {
    throw new Error(gl!.getProgramInfoLog(prog) ?? "program link failed");
  }
  gl!.useProgram(prog);

  const U = {
    proj: gl!.getUniformLocation(prog, "uProj")!,
    view: gl!.getUniformLocation(prog, "uView")!,
    sunDir: gl!.getUniformLocation(prog, "uSunDir")!,
    eyePos: gl!.getUniformLocation(prog, "uEyePos")!,
    pointSize: gl!.getUniformLocation(prog, "uPointSize")!,
    useVertexColor: gl!.getUniformLocation(prog, "uUseVertexColor")!,
    earthTexture: gl!.getUniformLocation(prog, "uEarthTexture")!,
    useEarthTexture: gl!.getUniformLocation(prog, "uUseEarthTexture")!,
  };
  const A_p = gl!.getAttribLocation(prog, "aPosition");
  const A_n = gl!.getAttribLocation(prog, "aNormal");
  const A_c = gl!.getAttribLocation(prog, "aColor");

  loadEarthTexture(gl);

  const globeData = buildProceduralGlobeBuffers(getLODResolution(camDist));
  currentLOD = getLODResolution(camDist);
  globePosBuf = makeBuffer(globeData.positions, gl!.TRIANGLES, 3);
  globeNormBuf = makeBuffer(globeData.normals, gl!.TRIANGLES, 3);
  globeIdxBuf = makeIndexBuffer(globeData.indices);
  globeIdxCount = globeData.indices.length;

  buildGlobeBuffers(getLODResolution(camDist)).then((data) => {
    if (!mounted || !gl) return;
    if (globePosBuf) gl.deleteBuffer(globePosBuf.buf);
    if (globeNormBuf) gl.deleteBuffer(globeNormBuf.buf);
    if (globeIdxBuf) gl.deleteBuffer(globeIdxBuf);
    globePosBuf = makeBuffer(data.positions, gl.TRIANGLES, 3);
    globeNormBuf = makeBuffer(data.normals, gl.TRIANGLES, 3);
    globeIdxBuf = makeIndexBuffer(data.indices);
    globeIdxCount = data.indices.length;
  });

  const hasScene = scene.value != null;
  const hasPoints = props.points && props.points.length > 0;

  if (hasScene) {
    updateSceneBuffers(scene.value as AetherScene);
  } else if (hasPoints) {
    updateDynamicBuffers(props.points!, props.colorBySpeed || false);
  } else {
    updateDynamicBuffers(DEMO_POINTS, true);
  }

  let yaw = 0.6;
  let pitch = 0.35;
  let vyaw = 0;
  let vpitch = 0;
  let dragging = false;
  let lx = 0;
  let ly = 0;
  let autoRotate = false;

  async function rebuildGlobeIfNeeded(camDist: number) {
    const targetN = getLODResolution(camDist);
    if (targetN === currentLOD || globePending || !mounted) return;
    globePending = true;
    currentLOD = targetN;
    const data = await buildGlobeBuffers(targetN);
    if (!mounted || !gl) return;
    if (globePosBuf) gl.deleteBuffer(globePosBuf.buf);
    if (globeNormBuf) gl.deleteBuffer(globeNormBuf.buf);
    if (globeIdxBuf) gl.deleteBuffer(globeIdxBuf);
    globePosBuf = makeBuffer(data.positions, gl.TRIANGLES, 3);
    globeNormBuf = makeBuffer(data.normals, gl.TRIANGLES, 3);
    globeIdxBuf = makeIndexBuffer(data.indices);
    globeIdxCount = data.indices.length;
    globePending = false;
  }

  canvasEl.addEventListener("pointerdown", (e: PointerEvent) => {
    dragging = true;
    autoRotate = false;
    vyaw = 0;
    vpitch = 0;
    lx = e.clientX;
    ly = e.clientY;
    canvasEl.setPointerCapture(e.pointerId);
  });
  canvasEl.addEventListener("pointerup", () => {
    dragging = false;
  });
  canvasEl.addEventListener("pointermove", (e: PointerEvent) => {
    if (!dragging) return;
    const dYaw = (e.clientX - lx) * 0.005;
    const dPitch = (e.clientY - ly) * 0.005;
    yaw += dYaw;
    pitch += dPitch;
    pitch = Math.max(-1.5, Math.min(1.5, pitch));
    vyaw = dYaw;
    vpitch = dPitch;
    lx = e.clientX;
    ly = e.clientY;
  });
  canvasEl.addEventListener(
    "wheel",
    (e: WheelEvent) => {
      e.preventDefault();
      camDist *= Math.exp(e.deltaY * 0.001);
      camDist = Math.max(CAM_DIST_MIN, Math.min(CAM_DIST_MAX, camDist));
    },
    { passive: false },
  );
  canvasEl.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.code === "Space") {
      autoRotate = !autoRotate;
      e.preventDefault();
    }
  });
  canvasEl.tabIndex = 0;

  function applyResize(width: number, height: number) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasEl.width = Math.floor(width * dpr);
    canvasEl.height = Math.floor(height * dpr);
  }
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      applyResize(entry.contentRect.width, entry.contentRect.height);
    }
  });
  resizeObserver.observe(canvasEl.parentElement!);
  requestAnimationFrame(() => {
    applyResize(
      canvasEl.parentElement!.clientWidth,
      canvasEl.parentElement!.clientHeight,
    );
  });

  const sunDir = normalize3([0.6, 0.8, 0.4]);
  void sunDir;

  let lastTime = performance.now();
  let frameCount = 0;
  let lastCheckedCamDist = camDist;

  observer = new IntersectionObserver(
    (entries) => {
      isVisible = entries[0].isIntersecting;
      if (isVisible && !rafId) {
        rafId = requestAnimationFrame(frame);
      }
    },
    { threshold: 0 },
  );
  observer.observe(canvasEl);

  onVisibilityChange = () => {
    if (document.hidden) return;
    if (isVisible && !rafId) {
      rafId = requestAnimationFrame(frame);
    }
  };
  document.addEventListener("visibilitychange", onVisibilityChange);

  function frame() {
    if (!gl || !isVisible) {
      rafId = null;
      return;
    }
    const now = performance.now();
    frameCount++;
    if (now - lastTime >= 1000) {
      fps.value = frameCount;
      frameCount = 0;
      lastTime = now;
    }

    gl.viewport(0, 0, canvasEl.width, canvasEl.height);
    gl.clearColor(0.02, 0.03, 0.06, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    if (!dragging && autoRotate) {
      yaw += 0.003;
    } else if (!dragging) {
      yaw += vyaw;
      pitch += vpitch;
      pitch = Math.max(-1.5, Math.min(1.5, pitch));
      vyaw *= 0.92;
      vpitch *= 0.92;
      if (Math.abs(vyaw) < 1e-4) vyaw = 0;
      if (Math.abs(vpitch) < 1e-4) vpitch = 0;
    }

    if (props.cameraMode === "topDown") {
      pitch = 1.45;
    } else if (props.cameraMode === "follow" && activeRoutePoints.value.length) {
      followIndex = (followIndex + 0.3) % activeRoutePoints.value.length;
      const pt = activeRoutePoints.value[Math.floor(followIndex)];
      if (pt) {
        targetYaw = (pt.lon * Math.PI) / 180 + Math.PI / 2;
        targetPitch = Math.max(-1.4, Math.min(1.4, (pt.lat * Math.PI) / 180));
        targetCamDist = 1.6;
        animatingCamera = true;
        updateRiderMarkerBuffer(pt);
      }
    }

    if (animatingCamera) {
      yaw += (targetYaw - yaw) * 0.08;
      pitch += (targetPitch - pitch) * 0.08;
      camDist += (targetCamDist - camDist) * 0.08;
      if (
        Math.abs(targetYaw - yaw) < 1e-4 &&
        Math.abs(targetPitch - pitch) < 1e-4 &&
        Math.abs(targetCamDist - camDist) < 1e-4
      ) {
        animatingCamera = false;
      }
    }

    const aspect = canvasEl.width / Math.max(canvasEl.height, 1);
    const eye = camEye(yaw, pitch);

    if (camDist !== lastCheckedCamDist) {
      lastCheckedCamDist = camDist;
      rebuildGlobeIfNeeded(camDist).catch(() => {});
    }

    if (
      aspect !== cachedAspect ||
      camDist !== cachedCamDist ||
      yaw !== cachedYaw ||
      pitch !== cachedPitch
    ) {
      cachedAspect = aspect;
      cachedCamDist = camDist;
      cachedYaw = yaw;
      cachedPitch = pitch;
      cachedProj.set(mat4Perspective(CAM_FOV, aspect, CAM_NEAR, CAM_FAR));
      cachedView.set(mat4LookAt(eye, [0, 0, 0], [0, 1, 0]));
    }

    const sHour = props.sunHour ?? 12;
    const sunAngle = ((sHour - 6) / 24) * Math.PI * 2;
    const currentSunDir = normalize3([
      Math.cos(sunAngle),
      0.7,
      Math.sin(sunAngle),
    ]);

    gl.uniformMatrix4fv(U.proj, false, cachedProj);
    gl.uniformMatrix4fv(U.view, false, cachedView);
    gl.uniform3fv(U.sunDir, currentSunDir);
    gl.uniform3fv(U.eyePos, eye);
    gl.uniform1f(U.pointSize, 6.0);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, earthTexture);
    gl.uniform1i(U.earthTexture, 0);
    gl.uniform1i(U.useEarthTexture, useEarthTexture ? 1 : 0);

    if (globePosBuf && globeNormBuf && globeIdxBuf) {
      gl.disable(gl.POLYGON_OFFSET_FILL);
      gl.uniform1i(U.useVertexColor, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, globePosBuf.buf);
      gl.enableVertexAttribArray(A_p);
      gl.vertexAttribPointer(A_p, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, globeNormBuf.buf);
      gl.enableVertexAttribArray(A_n);
      gl.vertexAttribPointer(A_n, 3, gl.FLOAT, false, 0, 0);
      gl.disableVertexAttribArray(A_c);
      gl.vertexAttrib3f(A_c, 1.0, 1.0, 1.0);
      const drawMode = props.wireframe ? gl.LINES : gl.TRIANGLES;
      drawIndexed(globeIdxBuf, globeIdxCount, drawMode);
      gl.enable(gl.POLYGON_OFFSET_FILL);
    }

    gl.uniform1i(U.useVertexColor, 1);
    if (routeBuffer) draw(routeBuffer, A_p, A_c);
    if (pointBuffer) draw(pointBuffer, A_p, A_c);
    if (markerBuffer) draw(markerBuffer, A_p, A_c);
    if (terrainBuffer) draw(terrainBuffer, A_p, A_c);
    if (riderMarkerBuffer) {
      gl.uniform1f(U.pointSize, 12.0);
      draw(riderMarkerBuffer, A_p, A_c);
      gl.uniform1f(U.pointSize, 6.0);
    }

    for (const [, buf] of geoBufferMap) {
      draw(buf, A_p, A_c);
    }

    rafId = requestAnimationFrame(frame);
  }

  rafId = requestAnimationFrame(frame);
});

watch(
  () => [props.points, props.colorBySpeed],
  () => {
    if (!gl) return;
    if (!scene.value) {
      const pts =
        props.points && props.points.length > 0 ? props.points : DEMO_POINTS;
      const cb = props.colorBySpeed || false;
      const key = `${cb}:${pts
        .map(
          (p) =>
            `${p.lat.toFixed(5)},${p.lon.toFixed(5)},${(p.speed ?? 0).toFixed(2)},${(p.altitude ?? 0).toFixed(1)}`,
        )
        .join("|")}`;
      if (key === _prevPointsKey) return;
      _prevPointsKey = key;
      updateDynamicBuffers(pts, cb);
    }
  },
);

watch(
  scene,
  (sc) => {
    if (!gl) return;
    if (sc) updateSceneBuffers(sc);
    else
      updateDynamicBuffers(
        props.points && props.points.length > 0 ? props.points : DEMO_POINTS,
        props.colorBySpeed || false,
      );
  },
  { deep: false },
);

watch(
  () => visibleLayers.value.map((l) => l.id),
  () => {
    if (!gl) return;
    if (_geoDebounce) clearTimeout(_geoDebounce);
    _geoDebounce = window.setTimeout(() => {
      _geoDebounce = null;
      updateGeoBuffers();
    }, 150);
  },
);

watch(terrainPoints, () => {
  if (!gl) return;
  if (terrainBuffer) {
    gl.deleteBuffer(terrainBuffer.buf);
    terrainBuffer = null;
  }
  const data: number[] = [];
  for (const pt of terrainPoints.value) {
    const dir = geodeticToDirection(pt.lat, pt.lon);
    const elev = (pt.altitude || 0) * TERRAIN_SCALE;
    const r = GLOBE_RADIUS + elev;
    const slope = pt.slope_pct || 0;
    const col: Vec3 =
      slope > 8
        ? [0.93, 0.2, 0.2]
        : slope > 4
          ? [0.93, 0.53, 0.0]
          : [0.0, 0.8, 0.27];
    data.push(dir[0] * r, dir[1] * r, dir[2] * r, col[0], col[1], col[2]);
  }
  if (data.length)
    terrainBuffer = makeBuffer(new Float32Array(data), gl.POINTS, 6);
});

onBeforeUnmount(() => {
  mounted = false;
  if (rafId != null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (_geoDebounce) {
    clearTimeout(_geoDebounce);
    _geoDebounce = null;
  }
  observer?.disconnect();
  document.removeEventListener("visibilitychange", onVisibilityChange);
  if (gl) {
    if (globePosBuf) gl.deleteBuffer(globePosBuf.buf);
    if (globeNormBuf) gl.deleteBuffer(globeNormBuf.buf);
    if (globeIdxBuf) gl.deleteBuffer(globeIdxBuf);
    if (routeBuffer) gl.deleteBuffer(routeBuffer.buf);
    if (pointBuffer) gl.deleteBuffer(pointBuffer.buf);
    if (markerBuffer) gl.deleteBuffer(markerBuffer.buf);
    if (terrainBuffer) gl.deleteBuffer(terrainBuffer.buf);
    for (const [, buf] of geoBufferMap) {
      if (buf && gl) gl.deleteBuffer(buf.buf);
    }
    geoBufferMap.clear();
  }
  resizeObserver?.disconnect();
});
</script>
<style scoped>
.aethermap-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  background: #0a0c14;
  overflow: hidden;
}
.aethermap-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  outline: none;
}
.aethermap-canvas:active {
  cursor: grabbing;
}
.aethermap-hud {
  position: absolute;
  left: 10px;
  top: 10px;
  color: #7fd;
  font-size: 12px;
  line-height: 1.5;
  background: rgba(0, 0, 0, 0.35);
  padding: 8px 10px;
  border-radius: 6px;
  pointer-events: none;
}
.aethermap-hud b {
  color: #fff;
}
.aethermap-warn {
  color: #ff8888;
}
.aethermap-layers {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(127, 255, 221, 0.15);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.aethermap-layers-title {
  color: #fff;
  font-weight: bold;
  margin-right: 4px;
}
.aethermap-layer-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  pointer-events: auto;
  color: #7fd;
}
.aethermap-layer-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.aethermap-layer-loading {
  color: #ff8888;
  font-size: 10px;
}
.aethermap-layer-count {
  color: #aaa;
  font-size: 10px;
}
.aethermap-profile-overlay {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid rgba(127, 255, 221, 0.2);
  pointer-events: auto;
}
.aethermap-profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #00f3ff;
  margin-bottom: 4px;
}
.aethermap-profile-meta {
  color: #fff;
  font-weight: 600;
}
.aethermap-profile-svg {
  width: 100%;
  height: 36px;
  background: rgba(0, 243, 255, 0.05);
  border: 1px solid rgba(0, 243, 255, 0.2);
  border-radius: 4px;
  cursor: crosshair;
  display: block;
}
</style>