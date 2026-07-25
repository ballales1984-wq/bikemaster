<!-- General statistics summary: animated cards (count) for rides, total distance, calories, average speed and total hours.
     Props: stats (oggetto con rides/distance_km/calories/avg_speed_kmh/duration_minutes), loading. Eventi: refresh.
     UI: griglia di stat-card con direttiva v-stagger (animazione, rispetta prefers-reduced-motion) e pulsante Refresh. -->
<template>
  <div class="stats" aria-label="General Statistics">
    <div
      v-stagger
      class="stat-card"
      role="status"
      :style="{ '--stagger-index': 0 }"
    >
      <span class="stat-icon" aria-hidden="true"></span>
      <div class="stat-value">
        {{ animatedRides }}
      </div>
      <div class="stat-label">Uscite</div>
    </div>
    <div
      v-stagger
      class="stat-card"
      role="status"
      :style="{ '--stagger-index': 1 }"
    >
      <span class="stat-icon" aria-hidden="true"></span>
      <div class="stat-value">{{ animatedDistance }} km</div>
      <div class="stat-label">Distanza Totale</div>
    </div>
    <div
      v-stagger
      class="stat-card"
      role="status"
      :style="{ '--stagger-index': 2 }"
    >
      <span class="stat-icon" aria-hidden="true"></span>
      <div class="stat-value">
        {{ animatedCalories }}
      </div>
      <div class="stat-label">Calorie</div>
    </div>
    <div
      v-stagger
      class="stat-card"
      role="status"
      :style="{ '--stagger-index': 3 }"
    >
      <span class="stat-icon" aria-hidden="true"></span>
      <div class="stat-value">{{ animatedSpeed }} km/h</div>
      <div class="stat-label">Velocità Media</div>
    </div>
    <div
      v-stagger
      class="stat-card"
      role="status"
      :style="{ '--stagger-index': 4 }"
    >
      <span class="stat-icon" aria-hidden="true">⏱</span>
      <div class="stat-value">{{ animatedHours }} h</div>
      <div class="stat-label">Ore Totali</div>
    </div>
    <button
      v-stagger
      class="stat-card stat-refresh"
      :style="{ '--stagger-index': 5 }"
      :disabled="loading"
      :aria-label="loading ? 'Aggiornamento in corso' : 'Aggiorna statistiche'"
      @click="$emit('refresh')"
    >
      <span class="stat-icon" :class="{ spin: loading }">{{
        loading ? "⏳" : "🔄"
      }}</span>
      <div class="stat-label">
        {{ loading ? "Aggiornamento..." : "Aggiorna" }}
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, Directive } from "vue";

const props = defineProps({
  stats: { type: Object, default: null },
  loading: { type: Boolean, default: false },
});

defineEmits(["refresh"]);

const vStagger: Directive<HTMLElement, boolean> = {
  mounted(el) {
    let reduceMotion = false;
    try {
      reduceMotion =
        typeof window.matchMedia === "function" &&
        !!window.matchMedia("(prefers-reduced-motion: reduce)")?.matches;
    } catch {
      reduceMotion = false;
    }
    if (reduceMotion) return;
    el.classList.add("stagger-item");
    el.addEventListener(
      "animationend",
      () => el.classList.remove("stagger-item"),
      { once: true },
    );
  },
};

const animatedRides = ref(0);
const animatedDistance = ref(0);
const animatedCalories = ref(0);
const animatedSpeed = ref(0);
const animatedHours = ref(0);

function animate(to: number, from = 0, duration = 800) {
  return new Promise<number>((resolve) => {
    const start = performance.now();
    const raf =
      typeof requestAnimationFrame !== "undefined"
        ? requestAnimationFrame
        : (cb: FrameRequestCallback) =>
            setTimeout(() => cb(performance.now()), 0);
    const step = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = from + (to - from) * eased;
      if (progress < 1) {
        raf(step);
      } else {
        resolve(value);
      }
    };
    raf(step);
  });
}

watch(
  () => props.stats,
  (newStats) => {
    if (!newStats) return;
    const rides = Number(newStats.rides) || 0;
    const dist = Number(newStats.distance_km) || 0;
    const cals = Number(newStats.calories) || 0;
    const speed = Number(newStats.avg_speed_kmh) || 0;
    const hours = (Number(newStats.duration_minutes) || 0) / 60;

    animate(rides).then((v) => (animatedRides.value = Math.round(v)));
    animate(dist).then(
      (v) => (animatedDistance.value = parseFloat(v.toFixed(1))),
    );
    animate(cals).then((v) => (animatedCalories.value = Math.round(v)));
    animate(speed).then(
      (v) => (animatedSpeed.value = parseFloat(v.toFixed(1))),
    );
    animate(hours).then(
      (v) => (animatedHours.value = parseFloat(v.toFixed(1))),
    );
  },
  { immediate: true },
);
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 20px;
  margin: 25px 0;
}

.stat-card {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  padding: 24px 20px;
  border-radius: var(--radius);
  text-align: center;
  border: 1px solid var(--border);
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}

/* Gradient border via mask */
.stat-card::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: var(--radius);
  padding: 1px;
  background: var(--gradient-border);
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask-composite: exclude;
  opacity: 0;
  transition: opacity var(--transition);
  pointer-events: none;
}

.stat-icon {
  font-size: 1.4rem;
  display: block;
  margin-bottom: 8px;
  filter: drop-shadow(0 0 6px rgba(0, 255, 204, 0.35));
  transition: transform var(--transition);
}

.stat-card:hover .stat-icon {
  transform: scale(1.15) translateY(-2px);
}

.stat-card::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--accent-gradient);
  opacity: 0;
  transition: var(--transition);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg), var(--glow-card);
  border-color: var(--border-light);
}

.stat-card:hover::before {
  opacity: 0.7;
  animation: rotateGradient 6s linear infinite;
}

.stat-card:hover::after {
  opacity: 1;
}

.stat-value {
  font-size: 2rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
  font-family: "Outfit", sans-serif;
}

.stat-label {
  color: var(--text-secondary);
  margin-top: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-refresh {
  background: rgba(0, 255, 204, 0.08);
  color: var(--text-primary);
  border: 1px solid var(--border);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  font-size: 1.2rem;
}

.stat-refresh:hover {
  border-color: var(--accent);
  background: rgba(0, 255, 204, 0.14);
}

.stat-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.stat-refresh .stat-icon.spin {
  animation: statSpin 0.8s linear infinite;
}

@keyframes statSpin {
  to {
    transform: rotate(360deg);
  }
}
</style>
