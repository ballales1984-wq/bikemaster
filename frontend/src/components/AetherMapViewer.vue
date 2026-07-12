<template>
  <div class="aethermap-viewer">
    <canvas ref="canvasRef" class="aethermap-canvas" />
    <div class="aethermap-hud">
      <b>AetherMap</b> · WebGL2 cube-sphere (Fase 4)<br />
      trascina per ruotare (prospettica) · rotella per zoom<br />
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
}

const props = defineProps<{
  points?: MapPoint[];
  rideIds?: number[];
  colorBySpeed?: boolean;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
let gl: WebGL2RenderingContext | null = null;
let rafId: number | null = null;

let wireBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let routeBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let pointBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;
let markerBuffer: { buf: WebGLBuffer; count: number; mode: number } | null = null;

const rideIdsRef = computed(() => props.rideIds ?? []);
const { scene, loading, error } = useAetherMap(rideIdsRef);

const DEG = Math.PI / 180;
function geodeticToDirection(lat: number, lon: number): [number, number, number] {
  const la = lat * DEG;
  const lo = lon * DEG;
  const cl = Math.cos(la);
  return [cl * Math.cos(lo), cl * Math.sin(lo), Math.sin(la)];
}

// Normalizza un punto entità in direzione unitaria sulla sfera.
// Supporta sia [lat, lon] gradi (adapter live) sia vettori ECEF
// [x, y, z] (ordine di grandezza ~6.37e6 m), come nel vecchio
// ride_1_map.json.
type Vec3 = [number, number, number];
function toDir(p: number[]): Vec3 {
  if (p.length >= 3 && Math.abs(p[0]) > 1e5) {
    const n = Math.hypot(p[0], p[1], p[2]) || 1;
    return [p[0] / n, p[1] / n, p[2] / n];
  }
  return geodeticToDirection(p[0], p[1]);
}

// Interpolazione su grande cerchio (slerp) tra due direzioni unitarie.
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

// Aggiunge un segmento di rotta suddiviso in arche di grande cerchio, così
// il percorso aderisce alla superficie invece di essere una corda che taglia
// la sfera (causa dell'effetto "ventaglio/cono" in proiezione).
function pushArc(arr: number[], a: Vec3, b: Vec3, col: Vec3): void {
  const d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const theta = Math.acos(Math.max(-1, Math.min(1, d)));
  const steps = Math.max(1, Math.min(64, Math.ceil(theta / (2 * DEG))));
  for (let k = 0; k <= steps; k++) {
    const pt = slerpDir(a, b, k / steps);
    arr.push(pt[0], pt[1], pt[2], col[0], col[1], col[2]);
  }
}

// --- Camera prospettica orbitale (coerente con il motore backend) ---
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
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  return [camDist * cy * cp, camDist * sp, camDist * sy * cp];
}
// Matrice di prospettiva destrorsa (forma standard glPerspective), column-major.
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
// Matrice lookAt (colonna-major) che guarda l'origine (centro globo).
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

function speedColor(speed: number | undefined): [number, number, number] {
  if (speed == null) return [0.40, 40 / 255, 1.0];
  if (speed >= 35) return [0.0, 0.8, 0.27];
  if (speed >= 25) return [0.53, 0.8, 0.0];
  if (speed >= 15) return [0.87, 0.73, 0.0];
  if (speed >= 5) return [0.93, 0.53, 0.0];
  return [0.93, 0.2, 0.2];
}

function makeBuffer(arr: number[], mode: number, stride: number) {
  if (!gl) throw new Error("WebGL context not initialized");
  const b = gl.createBuffer()!;
  gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW);
  return { buf: b, count: arr.length / stride, mode };
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
  if (!gl) return;

  const routeData: number[] = [];
  const pointData: number[] = [];
  let prev: Vec3 | null = null;
  for (const p of points) {
    const dir = geodeticToDirection(p.lat, p.lon);
    const col: Vec3 = colorBySpeed ? speedColor(p.speed) : [0.95, 0.85, 0.25];
    pointData.push(...dir, ...col);
    if (prev) pushArc(routeData, prev, dir, col);
    prev = dir;
  }
  if (routeData.length) {
    routeBuffer = makeBuffer(routeData, gl.LINE_STRIP, 6);
    pointBuffer = makeBuffer(pointData, gl.POINTS, 6);
  }
}

function markerColor(tipo: string): [number, number, number] {
  if (tipo === "start") return [0.2, 0.9, 0.3];
  if (tipo === "end") return [0.95, 0.3, 0.3];
  return [1.0, 0.85, 0.2];
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
      const col = hexToRgb(ent.char);
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        pushArc(routeData, pts[i], pts[i + 1], col);
      }
    } else if (ent.tipo === "start" || ent.tipo === "end" || ent.tipo === "stats") {
      const p = ent.pts[0];
      if (!p) continue;
      const rel = toDir(p);
      markerData.push(...rel, ...markerColor(ent.tipo));
    } else {
      const col = hexToRgb(ent.char);
      const pts = ent.pts.map(toDir);
      for (let i = 0; i + 1 < pts.length; i++) {
        pushArc(routeData, pts[i], pts[i + 1], col);
      }
    }
  }
  if (routeData.length) {
    routeBuffer = makeBuffer(routeData, gl.LINE_STRIP, 6);
  }
  if (markerData.length) {
    markerBuffer = makeBuffer(markerData, gl.POINTS, 6);
  }
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
in vec3 p;
in vec3 vColor;
uniform mat4 uProj;
uniform mat4 uView;
uniform vec3 uEye;
uniform float pointSize;
out vec3 vColorOut;
out float facing;
 void main() {
   vec3 n = normalize(p);
   facing = dot(n, normalize(uEye));
   gl_Position = uProj * uView * vec4(p, 1.0);
   gl_PointSize = pointSize;
   vColorOut = vColor;
 }`;

  const FS = `#version 300 es
precision mediump float;
in float facing;
in vec3 vColorOut;
out vec4 outColor;
 void main() {
   if (facing <= 0.0) discard;
   float sh = clamp(0.40 + facing * 0.60, 0.0, 1.0);
   outColor = vec4(vColorOut * sh, 1.0);
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
    eye: gl!.getUniformLocation(prog, "uEye")!,
    pointSize: gl!.getUniformLocation(prog, "pointSize")!,
  };
  const A_p = gl!.getAttribLocation(prog, "p");
  const A_color = gl!.getAttribLocation(prog, "vColor");

  const N = 16;
  const wire: number[] = [];
  const grid: Array<Array<Array<number[]>>> = [];
  for (let f = 0; f < 6; f++) {
    grid[f] = [];
    for (let i = 0; i <= N; i++) {
      grid[f][i] = [];
      for (let j = 0; j <= N; j++) {
        const u = (i / N) * 2 - 1;
        const v = (j / N) * 2 - 1;
        let d: [number, number, number];
        if (f === 0) d = [1, u, v];
        else if (f === 1) d = [-1, u, v];
        else if (f === 2) d = [u, 1, v];
        else if (f === 3) d = [u, -1, v];
        else if (f === 4) d = [u, v, 1];
        else d = [u, v, -1];
        const n = Math.hypot(d[0], d[1], d[2]);
        const p = [d[0] / n, d[1] / n, d[2] / n] as Vec3;
        grid[f][i][j] = p;
      }
    }
  }
  for (let f = 0; f < 6; f++) {
    for (let i = 0; i <= N; i++) {
      for (let j = 0; j <= N; j++) {
        if (i < N) {
          const a = grid[f][i][j];
          const b = grid[f][i + 1][j];
          wire.push(...a, ...b, 0.30, 0.55, 0.85, 0.30, 0.55, 0.85);
        }
        if (j < N) {
          const a = grid[f][i][j];
          const b = grid[f][i][j + 1];
          wire.push(...a, ...b, 0.30, 0.55, 0.85, 0.30, 0.55, 0.85);
        }
      }
    }
  }
  wireBuffer = makeBuffer(wire, gl!.LINES, 6);
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

  canvasEl.addEventListener("pointerdown", (e: PointerEvent) => {
    dragging = true;
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

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasEl.width = Math.floor(innerWidth * dpr);
    canvasEl.height = Math.floor(innerHeight * dpr);
  }
  addEventListener("resize", resize);
  resize();

  function draw(
    buf: { buf: WebGLBuffer; count: number; mode: number },
  ) {
    gl!.bindBuffer(gl!.ARRAY_BUFFER, buf.buf);
    gl!.enableVertexAttribArray(A_p);
    gl!.vertexAttribPointer(A_p, 3, gl!.FLOAT, false, 24, 0);
    gl!.enableVertexAttribArray(A_color);
    gl!.vertexAttribPointer(A_color, 3, gl!.FLOAT, false, 24, 12);
    gl!.drawArrays(buf.mode, 0, buf.count);
  }

  function frame() {
    if (!gl) return;
    gl.viewport(0, 0, canvasEl.width, canvasEl.height);
    gl.clearColor(0.04, 0.05, 0.08, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    if (!dragging) {
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
    gl.uniformMatrix4fv(U.proj, false, mat4Perspective(CAM_FOV, aspect, CAM_NEAR, CAM_FAR));
    gl.uniformMatrix4fv(U.view, false, mat4LookAt(eye, [0, 0, 0], [0, 1, 0]));
    gl.uniform3f(U.eye, eye[0], eye[1], eye[2]);
    gl.uniform1f(U.pointSize, 6.0);

    if (wireBuffer) draw(wireBuffer);
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
    if (wireBuffer) gl.deleteBuffer(wireBuffer.buf);
    if (routeBuffer) gl.deleteBuffer(routeBuffer.buf);
    if (pointBuffer) gl.deleteBuffer(pointBuffer.buf);
    if (markerBuffer) gl.deleteBuffer(markerBuffer.buf);
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
