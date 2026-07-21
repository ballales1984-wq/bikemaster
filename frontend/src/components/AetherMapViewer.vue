<!-- Visualizzatore AetherMap: rendering WebGL2 di un globo cube-sphere con terrain, illuminazione e percorsi GPS.
      Props: points (list of lat/lon/speed), rideIds (ride IDs to load via API), colorBySpeed (color by speed).
      Events: none. UI: full-size canvas + HUD with statistics and mouse controls (drag/scroll). -->
<template>
  <div class="aethermap-viewer">
    <canvas ref="canvasRef" class="aethermap-canvas" />
    <div class="aethermap-hud">
      <b>AetherMap</b> · WebGL2 cube-sphere + terrain<br />
      trascina per ruotare · rotella per zoom · spazio = auto-rotazione<br />
      <template v-if="rideIds && rideIds.length">
        <span v-if="loading">carico scena…</span>
        <span v-else-if="error" class="aethermap-warn">scena non disponibile</span>
        <template v-else-if="scene && scene.statistics">
          dist: {{ Math.round(scene.statistics.total_distance_m) }} m ·
          avg: {{ scene.statistics.avg_speed_km_h }} km/h ·
          &Delta;h: {{ Math.round(scene.statistics.total_elevation_gain_m) }} m
        </template>
      </template>
      <br />linea = percorso · verde = start · rosso = end · giallo = stats
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { useAetherMap, hexToRgb, type AetherScene } from "../composables/useAetherMap";

interface MapPoint {
  lat: number;
  lon: number;
  speed?: number;
  altitude?: number;
}

const props = defineProps<{
  points?: MapPoint[];
  rideIds?: number[];
  colorBySpeed?: boolean;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
let gl: WebGL2RenderingContext | null = null;
let rafId: number | null = null;

let globeBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let routeBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let pointBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let markerBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;

const rideIdsRef = computed(() => props.rideIds ?? []);
const { scene, loading, error } = useAetherMap(rideIdsRef);

const DEG = Math.PI / 180;
const EARTH_R = 6371000.0;
const GLOBE_RADIUS = 1.0;
const TERRAIN_SCALE = 1.0 / EARTH_R;
const SKIRT_HEIGHT = 0.003;
const MESH_N = 22;

function geodeticToDirection(lat: number, lon: number): [number, number, number] {
  const la = lat * DEG;
  const lo = lon * DEG;
  const cl = Math.cos(la);
  return [cl * Math.cos(lo), cl * Math.sin(lo), Math.sin(la)];
}

type Vec3 = [number, number, number];
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
  const v: Vec3 = [a[0] * w1 + b[0] * w2, a[1] * w1 + b[1] * w2, a[2] * w1 + b[2] * w2];
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
  if (speed == null) return [0.40, 40 / 255, 1.0];
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

// --- Procedural terrain (frontend-side, matches backend terrain.py) ---
function hash(x: number, y: number): number {
  const buf = new ArrayBuffer(8);
  const view = new DataView(buf);
  view.setUint32(0, (x | 0) ^ 0xAE7E5, true);
  view.setUint32(4, (y | 0) ^ 0x5E7AE, true);
  const bytes = new Uint8Array(buf);
  let h = 0;
  for (let i = 0; i < bytes.length; i++) h = ((h << 5) - h + bytes[i]) | 0;
  return ((h & 0xFFFF) / 0xFFFF);
}

function smooth(t: number): number {
  return t * t * (3 - 2 * t);
}

function noise2d(x: number, y: number): number {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const ux = smooth(xf);
  const uy = smooth(yf);
  const a = hash(xi, yi);
  const b = hash(xi + 1, yi);
  const c = hash(xi, yi + 1);
  const d = hash(xi + 1, yi + 1);
  return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
}

function fbm(x: number, y: number, octaves = 6): number {
  let value = 0;
  let amplitude = 0.5;
  let frequency = 1;
  for (let i = 0; i < octaves; i++) {
    value += amplitude * noise2d(x * frequency, y * frequency);
    frequency *= 2;
    amplitude *= 0.5;
  }
  return value;
}

function getTerrainHeight(lat: number, lon: number): number {
  const latR = lat * DEG;
  const lonR = lon * DEG;
  const n = fbm(lonR * 3, latR * 3, 6);
  const n2 = fbm(lonR * 7 + 100, latR * 7 + 100, 4);
  const mask = n * 0.7 + n2 * 0.3;
  const threshold = 0.48 + 0.08 * Math.sin(latR * 2);
  if (mask > threshold) {
    const detail = fbm(lonR * 15, latR * 15, 4);
    let elevation = ((mask - threshold) / (1 - threshold)) * 0.7 + detail * 0.3;
    if (latR > 1.2) elevation *= Math.max(0, 1 - (latR - 1.2) / 0.4);
    return Math.max(0, elevation) * 4000;
  }
  return 0;
}

function latLonFromDir(dir: Vec3): { lat: number; lon: number } {
  const n = Math.hypot(dir[0], dir[1], dir[2]) || 1;
  const x = dir[0] / n, y = dir[1] / n, z = dir[2] / n;
  const lat = Math.asin(Math.max(-1, Math.min(1, z))) / DEG;
  const lon = Math.atan2(y, x) / DEG;
  return { lat, lon };
}

// --- Camera ---
const CAM_DIST = 2.7;
const CAM_DIST_MIN = 1.3;
const CAM_DIST_MAX = 8.0;
let camDist = CAM_DIST;
const CAM_FOV = (50 * Math.PI) / 180;
const CAM_NEAR = 0.1;
const CAM_FAR = 100.0;

function normalize3(v: Vec3): Vec3 {
  const n = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / n, v[1] / n, v[2] / n];
}
function sub3(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}
function cross3(a: Vec3, b: Vec3): Vec3 {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function dot3(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
function camEye(yaw: number, pitch: number): Vec3 {
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  return [camDist * cy * cp, camDist * sp, camDist * sy * cp];
}
function mat4Perspective(fov: number, aspect: number, near: number, far: number): Float32Array {
  const f = 1 / Math.tan(fov / 2);
  const nf = 1 / (near - far);
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) * nf, -1,
    0, 0, 2 * far * near * nf, 0,
  ]);
}
function mat4LookAt(eye: Vec3, center: Vec3, up: Vec3): Float32Array {
  const z = normalize3(sub3(eye, center));
  const x = normalize3(cross3(up, z));
  const y = cross3(z, x);
  return new Float32Array([
    x[0], y[0], z[0], 0,
    x[1], y[1], z[1], 0,
    x[2], y[2], z[2], 0,
    -dot3(x, eye), -dot3(y, eye), -dot3(z, eye), 1,
  ]);
}

// --- Globe mesh generation (cube-sphere with skirts) ---
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

function buildGlobeBuffers(): { positions: Float32Array; normals: Float32Array; indices: Uint32Array; vertexCount: number } {
  const N = MESH_N;
  const verts: Vec3[][][] = [];
  const skirtVerts: Vec3[][][] = [];

  for (let f = 0; f < 6; f++) {
    verts[f] = [];
    skirtVerts[f] = [];
    for (let i = 0; i <= N; i++) {
      verts[f][i] = [];
      skirtVerts[f][i] = [];
      for (let j = 0; j <= N; j++) {
        const u = (i / N) * 2 - 1;
        const v = (j / N) * 2 - 1;
        const dir = faceDir(f, u, v);
        const { lat, lon } = latLonFromDir(dir);
        const terrainH = getTerrainHeight(lat, lon) * TERRAIN_SCALE;
        const r = GLOBE_RADIUS + terrainH;
        const pos: Vec3 = [dir[0] * r, dir[1] * r, dir[2] * r];
        verts[f][i][j] = pos;

        if (i === 0 || i === N || j === 0 || j === N) {
          const skirtDir = faceDir(f, u, v);
          const sk: Vec3 = [skirtDir[0] * (r + SKIRT_HEIGHT), skirtDir[1] * (r + SKIRT_HEIGHT), skirtDir[2] * (r + SKIRT_HEIGHT)];
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
        faceSkirt[i][j] = addVertex(sk, normalize3(sk));
      }
    }

    // Main grid triangles
    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const a = faceVerts[i][j];
        const b = faceVerts[i + 1][j];
        const c = faceVerts[i][j + 1];
        const d = faceVerts[i + 1][j + 1];
        indices.push(a, b, c, b, d, c);
      }
    }

    // Skirt quads (only on boundary edges)
    for (let i = 0; i < N; i++) {
      // Bottom edge (j=0)
      const a = faceVerts[i][0];
      const b = faceVerts[i + 1][0];
      const sa = faceSkirt[i][0];
      const sb = faceSkirt[i + 1][0];
      indices.push(a, sa, b, b, sa, sb);
      // Top edge (j=N)
      const c = faceVerts[i][N];
      const d = faceVerts[i + 1][N];
      const sc = faceSkirt[i][N];
      const sd = faceSkirt[i + 1][N];
      indices.push(c, d, sc, d, sd, sc);
    }
    for (let j = 0; j < N; j++) {
      // Left edge (i=0)
      const a = faceVerts[0][j];
      const b = faceVerts[0][j + 1];
      const sa = faceSkirt[0][j];
      const sb = faceSkirt[0][j + 1];
      indices.push(a, b, sa, b, sb, sa);
      // Right edge (i=N)
      const c = faceVerts[N][j];
      const d = faceVerts[N][j + 1];
      const sc = faceSkirt[N][j];
      const sd = faceSkirt[N][j + 1];
      indices.push(c, d, sc, d, sd, sc);
    }
  }

  return {
    positions: new Float32Array(positions),
    normals: new Float32Array(normals),
    indices: new Uint32Array(indices),
    vertexCount,
  };
}

function makeBuffer(data: ArrayBufferView, mode: number, stride: number): { buf: WebGLBuffer; count: number; mode: number } | null {
  if (!gl) return null;
  const b = gl.createBuffer()!;
  gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  return { buf: b, count: data.byteLength / stride, mode };
}

function makeIndexBuffer(data: Uint32Array): WebGLBuffer | null {
  if (!gl) return null;
  const b = gl.createBuffer()!;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, data, gl.STATIC_DRAW);
  return b;
}

function draw(buf: { buf: WebGLBuffer; count: number; mode: number }) {
  if (!gl) return;
  gl.bindBuffer(gl.ARRAY_BUFFER, buf.buf);
  gl.drawArrays(buf.mode, 0, buf.count);
}

function drawIndexed(idxBuf: WebGLBuffer, count: number, mode = gl!.TRIANGLES) {
  if (!gl) return;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
  gl.drawElements(mode, count, gl.UNSIGNED_INT, 0);
}

function updateDynamicBuffers(points: MapPoint[], colorBySpeed: boolean) {
  if (routeBuffer && gl) { gl.deleteBuffer(routeBuffer.buf); routeBuffer = null; }
  if (pointBuffer && gl) { gl.deleteBuffer(pointBuffer.buf); pointBuffer = null; }
  if (markerBuffer && gl) { gl.deleteBuffer(markerBuffer.buf); markerBuffer = null; }
  if (!gl) return;

  const routeData: number[] = [];
  const pointData: number[] = [];
  const markerData: number[] = [];
  let prev: Vec3 | null = null;
  for (const p of points) {
    const dir = geodeticToDirection(p.lat, p.lon);
    const col: Vec3 = colorBySpeed ? speedColor(p.speed) : [0.95, 0.85, 0.25];
    const elev = (p.altitude || 0) * TERRAIN_SCALE;
    const r = GLOBE_RADIUS + elev;
    pointData.push(dir[0] * r, dir[1] * r, dir[2] * r, col[0], col[1], col[2]);
    if (prev) pushArc(routeData, prev, [dir[0] * r, dir[1] * r, dir[2] * r], col);
    prev = [dir[0] * r, dir[1] * r, dir[2] * r];
  }
  if (routeData.length) routeBuffer = makeBuffer(new Float32Array(routeData), gl.LINE_STRIP, 6);
  if (pointData.length) pointBuffer = makeBuffer(new Float32Array(pointData), gl.POINTS, 6);
}

function updateSceneBuffers(sc: AetherScene) {
  if (routeBuffer && gl) { gl.deleteBuffer(routeBuffer.buf); routeBuffer = null; }
  if (pointBuffer && gl) { gl.deleteBuffer(pointBuffer.buf); pointBuffer = null; }
  if (markerBuffer && gl) { gl.deleteBuffer(markerBuffer.buf); markerBuffer = null; }
  if (!gl) return;

  const routeData: number[] = [];
  const markerData: number[] = [];
  for (const ent of sc.entities) {
    if (ent.tipo === "segment") {
      const col = hexToRgb(ent.char);
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        const elev = (pts[i + 1] && (pts[i + 1][2] !== undefined) ? (pts[i + 1][2] || 0) : 0);
        const h0 = (ent.pts[i] && ent.pts[i].length >= 3 ? (ent.pts[i][2] || 0) : 0) * TERRAIN_SCALE;
        const h1 = (ent.pts[i + 1] && ent.pts[i + 1].length >= 3 ? (ent.pts[i + 1][2] || 0) : 0) * TERRAIN_SCALE;
        const a = [pts[i][0] * (GLOBE_RADIUS + h0), pts[i][1] * (GLOBE_RADIUS + h0), pts[i][2] * (GLOBE_RADIUS + h0)];
        const b = [pts[i + 1][0] * (GLOBE_RADIUS + h1), pts[i + 1][1] * (GLOBE_RADIUS + h1), pts[i + 1][2] * (GLOBE_RADIUS + h1)];
        pushArc(routeData, a as Vec3, b as Vec3, col);
      }
    } else if (ent.tipo === "start" || ent.tipo === "end" || ent.tipo === "stats") {
      const p = ent.pts[0];
      if (!p) continue;
      const rel = toDir(p);
      const h = (p.length >= 3 ? (p[2] || 0) : 0) * TERRAIN_SCALE;
      const r = GLOBE_RADIUS + h;
      markerData.push(rel[0] * r, rel[1] * r, rel[2] * r, ...markerColor(ent.tipo));
    } else {
      const col = hexToRgb(ent.char);
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        const h0 = (ent.pts[i] && ent.pts[i].length >= 3 ? (ent.pts[i][2] || 0) : 0) * TERRAIN_SCALE;
        const h1 = (ent.pts[i + 1] && ent.pts[i + 1].length >= 3 ? (ent.pts[i + 1][2] || 0) : 0) * TERRAIN_SCALE;
        const a = [pts[i][0] * (GLOBE_RADIUS + h0), pts[i][1] * (GLOBE_RADIUS + h0), pts[i][2] * (GLOBE_RADIUS + h0)];
        const b = [pts[i + 1][0] * (GLOBE_RADIUS + h1), pts[i + 1][1] * (GLOBE_RADIUS + h1), pts[i + 1][2] * (GLOBE_RADIUS + h1)];
        pushArc(routeData, a as Vec3, b as Vec3, col);
      }
    }
  }
  if (routeData.length) routeBuffer = makeBuffer(new Float32Array(routeData), gl.LINE_STRIP, 6);
  if (markerData.length) markerBuffer = makeBuffer(new Float32Array(markerData), gl.POINTS, 6);
}

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const canvasEl = canvas as HTMLCanvasElement;

  const glCtx = canvasEl.getContext("webgl2", { antialias: true });
  if (!glCtx) {
    console.error("WebGL2 non disponibile in questo browser.");
    return;
  }
  gl = glCtx;

  const VS = `#version 300 es
  in vec3 aPosition;
  in vec3 aNormal;
  uniform mat4 uProj;
  uniform mat4 uView;
  uniform vec3 uSunDir;
  uniform float uPointSize;
  out vec3 vNormal;
  out vec3 vViewPos;
  out float vElevation;
  void main() {
    vec4 viewPos = uView * vec4(aPosition, 1.0);
    gl_Position = uProj * viewPos;
    gl_PointSize = uPointSize;
    vNormal = mat3(uView) * aNormal;
    vViewPos = viewPos.xyz;
    vElevation = length(aPosition) - ${GLOBE_RADIUS.toFixed(1)};
  }`;

  const FS = `#version 300 es
  precision mediump float;
  in vec3 vNormal;
  in vec3 vViewPos;
  in float vElevation;
  uniform vec3 uSunDir;
  out vec4 outColor;
  void main() {
    vec3 n = normalize(vNormal);
    vec3 sun = normalize(uSunDir);
    float diff = max(dot(n, sun), 0.0);
    float ambient = 0.18;

    vec3 ocean = vec3(0.08, 0.22, 0.45);
    vec3 land = vec3(0.18, 0.42, 0.18);
    vec3 highland = vec3(0.55, 0.45, 0.30);
    vec3 snow = vec3(0.92, 0.94, 0.98);

    vec3 color;
    float h = vElevation;
    if (h < 0.005) {
      color = ocean;
    } else if (h < 0.06) {
      color = mix(ocean * 1.15, land, smoothstep(0.005, 0.04, h));
    } else if (h < 0.18) {
      color = mix(land, highland, smoothstep(0.06, 0.15, h));
    } else {
      color = mix(highland, snow, smoothstep(0.18, 0.35, h));
    }

    vec3 lit = color * (ambient + diff * 0.82);

    vec3 viewDir = normalize(-vViewPos);
    float rim = 1.0 - max(dot(viewDir, n), 0.0);
    rim = pow(rim, 3.5);
    lit += vec3(0.25, 0.45, 0.85) * rim * 0.35;

    outColor = vec4(lit, 1.0);
  }`;

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
    pointSize: gl!.getUniformLocation(prog, "uPointSize")!,
  };
  const A_p = gl!.getAttribLocation(prog, "aPosition");
  const A_n = gl!.getAttribLocation(prog, "aNormal");

  const globeData = buildGlobeBuffers();
  const globePosBuf = makeBuffer(globeData.positions, gl!.TRIANGLES, 3);
  const globeNormBuf = makeBuffer(globeData.normals, gl!.TRIANGLES, 3);
  const globeIdxBuf = makeIndexBuffer(globeData.indices);
  const globeIdxCount = globeData.indices.length;

  if (scene.value) {
    updateSceneBuffers(scene.value);
  } else {
    updateDynamicBuffers(props.points || [], props.colorBySpeed || false);
  }

  let yaw = 0.6;
  let pitch = 0.35;
  let vyaw = 0;
  let vpitch = 0;
  let dragging = false;
  let lx = 0;
  let ly = 0;
  let autoRotate = false;

  canvasEl.addEventListener("pointerdown", (e: PointerEvent) => {
    dragging = true;
    autoRotate = false;
    vyaw = 0;
    vpitch = 0;
    lx = e.clientX;
    ly = e.clientY;
    canvasEl.setPointerCapture(e.pointerId);
  });
  canvasEl.addEventListener("pointerup", () => { dragging = false; });
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

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasEl.width = Math.floor(innerWidth * dpr);
    canvasEl.height = Math.floor(innerHeight * dpr);
  }
  addEventListener("resize", resize);
  resize();

  const sunDir = normalize3([0.6, 0.8, 0.4]);

  let lastTime = performance.now();
  let frameCount = 0;
  let fps = 0;

  function frame() {
    if (!gl) return;
    const now = performance.now();
    frameCount++;
    if (now - lastTime >= 1000) {
      fps = frameCount;
      frameCount = 0;
      lastTime = now;
    }

    gl.viewport(0, 0, canvasEl.width, canvasEl.height);
    gl.clearColor(0.02, 0.03, 0.06, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);

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

    const aspect = canvasEl.width / Math.max(canvasEl.height, 1);
    const eye = camEye(yaw, pitch);
    const proj = mat4Perspective(CAM_FOV, aspect, CAM_NEAR, CAM_FAR);
    const view = mat4LookAt(eye, [0, 0, 0], [0, 1, 0]);

    gl.uniformMatrix4fv(U.proj, false, proj);
    gl.uniformMatrix4fv(U.view, false, view);
    gl.uniform3fv(U.sunDir, sunDir);
    gl.uniform1f(U.pointSize, 6.0);

    if (globePosBuf && globeNormBuf && globeIdxBuf) {
      gl.bindBuffer(gl.ARRAY_BUFFER, globePosBuf.buf);
      gl.enableVertexAttribArray(A_p);
      gl.vertexAttribPointer(A_p, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, globeNormBuf.buf);
      gl.enableVertexAttribArray(A_n);
      gl.vertexAttribPointer(A_n, 3, gl.FLOAT, false, 0, 0);
      drawIndexed(globeIdxBuf, globeIdxCount);
    }

    if (routeBuffer) draw(routeBuffer);
    if (pointBuffer) draw(pointBuffer);
    if (markerBuffer) draw(markerBuffer);

    rafId = requestAnimationFrame(frame);
  }

  rafId = requestAnimationFrame(frame);
});

watch(() => [props.points, props.colorBySpeed], () => {
  if (!gl) return;
  if (!scene.value) updateDynamicBuffers(props.points || [], props.colorBySpeed || false);
});

watch(
  scene,
  (sc) => {
    if (!gl) return;
    if (sc) updateSceneBuffers(sc);
    else updateDynamicBuffers(props.points || [], props.colorBySpeed || false);
  },
  { deep: false },
);

onBeforeUnmount(() => {
  if (rafId != null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (gl) {
    [
      globeBuffer, routeBuffer, pointBuffer, markerBuffer
    ].forEach((b) => { if (b) gl!.deleteBuffer(b.buf); });
  }
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
  position: fixed;
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
</style>
