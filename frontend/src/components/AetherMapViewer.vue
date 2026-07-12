<template>
  <div class="aethermap-viewer">
    <canvas ref="canvasRef" class="aethermap-canvas" />
    <div class="aethermap-hud">
      <b>AetherMap</b> — WebGL2 cube-sphere (Fase 4)<br />
      trascina per ruotare la camera · resize automatico<br />
      wireframe = cube-sphere · giallo = strada · verde = albero · rosso = montagna
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";

const canvasRef = ref<HTMLCanvasElement | null>(null);

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const canvasEl = canvas as HTMLCanvasElement;

  const glCtx = canvasEl.getContext("webgl2", { antialias: true });
  if (!glCtx) {
    console.error("WebGL2 non disponibile in questo browser.");
    return;
  }
  const gl = glCtx;

  const DEG = Math.PI / 180;
  function geodeticToDirection(lat: number, lon: number): [number, number, number] {
    const la = lat * DEG;
    const lo = lon * DEG;
    const cl = Math.cos(la);
    return [cl * Math.cos(lo), cl * Math.sin(lo), Math.sin(la)];
  }
  const EARTH_R = 6371000.0;

  function cameraRelative(p: [number, number, number]): [number, number, number] {
    return [p[0], p[1], p[2]];
  }

  const VS = `#version 300 es
in vec3 p;
uniform mat3 rot;
uniform vec2 scale;
uniform float pointSize;
out float facing;
void main() {
  vec3 r = rot * p;
  facing = r.z;
  if (r.z <= 0.0) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    return;
  }
  gl_Position = vec4(r.x * scale.x, r.y * scale.y, 0.0, 1.0);
  gl_PointSize = pointSize;
}`;

  const FS = `#version 300 es
precision mediump float;
in float facing;
uniform vec3 color;
out vec4 outColor;
void main() {
  float sh = clamp(0.55 + facing * 0.45, 0.0, 1.0);
  outColor = vec4(color * sh, 1.0);
}`;

  function compile(type: number, src: string): WebGLShader {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(s) ?? "shader compile failed");
    }
    return s;
  }

  const prog = gl.createProgram()!;
  gl.attachShader(prog, compile(gl.VERTEX_SHADER, VS));
  gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FS));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(prog) ?? "program link failed");
  }
  gl.useProgram(prog);

  const U = {
    rot: gl.getUniformLocation(prog, "rot")!,
    scale: gl.getUniformLocation(prog, "scale")!,
    pointSize: gl.getUniformLocation(prog, "pointSize")!,
    color: gl.getUniformLocation(prog, "color")!,
  };
  const A_p = gl.getAttribLocation(prog, "p");

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
        const p = cameraRelative([d[0] / n, d[1] / n, d[2] / n]);
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
          wire.push(...a, ...b);
        }
        if (j < N) {
          const a = grid[f][i][j];
          const b = grid[f][i][j + 1];
          wire.push(...a, ...b);
        }
      }
    }
  }

  const road: number[] = [];
  for (const [lat, lon] of [
    [45.0, 9.0],
    [45.01, 9.02],
    [45.02, 9.04],
  ]) {
    const p = cameraRelative(geodeticToDirection(lat, lon));
    road.push(...p);
  }
  const tree = cameraRelative(geodeticToDirection(45.005, 9.01));
  const mountainDir = geodeticToDirection(45.015, 9.03);
  const mountainR = 1.0 + 8000.0 / EARTH_R;
  const mountain = [
    mountainDir[0] * mountainR,
    mountainDir[1] * mountainR,
    mountainDir[2] * mountainR,
  ];

  function makeBuffer(arr: number[], mode: number) {
    const b = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW);
    return { buf: b, count: arr.length / 3, mode };
  }

  const BUF = {
    wire: makeBuffer(wire, gl.LINES),
    road: makeBuffer(road, gl.LINE_STRIP),
    tree: makeBuffer(tree, gl.POINTS),
    mountain: makeBuffer(mountain, gl.POINTS),
  };

  let yaw = 0.6;
  let pitch = 0.35;
  let dragging = false;
  let lx = 0;
  let ly = 0;

  canvasEl.addEventListener("pointerdown", (e: PointerEvent) => {
    dragging = true;
    lx = e.clientX;
    ly = e.clientY;
    canvasEl.setPointerCapture(e.pointerId);
  });
  canvasEl.addEventListener("pointerup", () => {
    dragging = false;
  });
  canvasEl.addEventListener("pointermove", (e: PointerEvent) => {
    if (!dragging) return;
    yaw += (e.clientX - lx) * 0.005;
    pitch += (e.clientY - ly) * 0.005;
    pitch = Math.max(-1.5, Math.min(1.5, pitch));
    lx = e.clientX;
    ly = e.clientY;
  });

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasEl.width = Math.floor(innerWidth * dpr);
    canvasEl.height = Math.floor(innerHeight * dpr);
  }
  addEventListener("resize", resize);
  resize();

  function rotationMatrix() {
    const cy = Math.cos(yaw);
    const sy = Math.sin(yaw);
    const cp = Math.cos(pitch);
    const sp = Math.sin(pitch);
    const c0 = [cy, 0, -sy];
    const c1 = [sy * sp, cp, cy * sp];
    const c2 = [sy * cp, -sp, cy * cp];
    return new Float32Array([...c0, ...c1, ...c2]);
  }

  function draw(
    buf: { buf: WebGLBuffer; count: number; mode: number },
    color: [number, number, number],
    size: number,
  ) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buf.buf);
    gl.enableVertexAttribArray(A_p);
    gl.vertexAttribPointer(A_p, 3, gl.FLOAT, false, 0, 0);
    gl.uniform3fv(U.color, color);
    gl.uniform1f(U.pointSize, size);
    gl.drawArrays(buf.mode, 0, buf.count);
  }

  function frame() {
    gl.viewport(0, 0, canvasEl.width, canvasEl.height);
    gl.clearColor(0.04, 0.05, 0.08, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    const s = 0.85;
    gl.uniformMatrix3fv(U.rot, false, rotationMatrix());
    gl.uniform2f(U.scale, s, s);

    draw(BUF.wire, [0.30, 0.55, 0.85], 1.0);
    draw(BUF.road, [0.95, 0.85, 0.25], 3.0);
    draw(BUF.tree, [0.35, 0.95, 0.45], 9.0);
    draw(BUF.mountain, [0.95, 0.35, 0.30], 11.0);

    requestAnimationFrame(frame);
  }

  frame();

  onBeforeUnmount(() => {
    removeEventListener("resize", resize);
  });
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
</style>
