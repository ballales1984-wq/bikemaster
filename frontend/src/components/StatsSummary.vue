<!-- General statistics summary: animated cards (count) for rides, total distance, calories, average speed and total hours.
     Props: stats (oggetto con rides/distance_km/calories/avg_speed_kmh/duration_minutes), loading. Eventi: refresh.
     UI: griglia di stat-card con direttiva v-stagger (animazione, rispetta prefers-reduced-motion) e pulsante Refresh. -->
<template>
  <div class="stats" aria-label="General Statistics">
    <template v-if="loading && !stats">
      <div
        v-stagger
        class="stat-card skeleton-card"
        :style="{ '--stagger-index': 0 }"
      >
        <BmSkeleton type="circle" size="lg" />
        <BmSkeleton
          type="text"
          size="lg"
          width="60%"
          style="margin-top: 12px"
        />
        <BmSkeleton type="text" size="sm" width="40%" style="margin-top: 8px" />
      </div>
      <div
        v-stagger
        class="stat-card skeleton-card"
        :style="{ '--stagger-index': 1 }"
      >
        <BmSkeleton type="circle" size="lg" />
        <BmSkeleton
          type="text"
          size="lg"
          width="60%"
          style="margin-top: 12px"
        />
        <BmSkeleton type="text" size="sm" width="40%" style="margin-top: 8px" />
      </div>
      <div
        v-stagger
        class="stat-card skeleton-card"
        :style="{ '--stagger-index': 2 }"
      >
        <BmSkeleton type="circle" size="lg" />
        <BmSkeleton
          type="text"
          size="lg"
          width="60%"
          style="margin-top: 12px"
        />
        <BmSkeleton type="text" size="sm" width="40%" style="margin-top: 8px" />
      </div>
      <div
        v-stagger
        class="stat-card skeleton-card"
        :style="{ '--stagger-index': 3 }"
      >
        <BmSkeleton type="circle" size="lg" />
        <BmSkeleton
          type="text"
          size="lg"
          width="60%"
          style="margin-top: 12px"
        />
        <BmSkeleton type="text" size="sm" width="40%" style="margin-top: 8px" />
      </div>
      <div
        v-stagger
        class="stat-card skeleton-card"
        :style="{ '--stagger-index': 4 }"
      >
        <BmSkeleton type="circle" size="lg" />
        <BmSkeleton
          type="text"
          size="lg"
          width="60%"
          style="margin-top: 12px"
        />
        <BmSkeleton type="text" size="sm" width="40%" style="margin-top: 8px" />
      </div>
    </template>
    <template v-else>
      <div
        v-stagger
        class="stat-card"
        role="status"
        :style="{ '--stagger-index': 0 }"
      >
        <span class="stat-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="5.5" cy="17.5" r="3.5" />
            <circle cx="18.5" cy="17.5" r="3.5" />
            <path
              d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h3"
            />
          </svg>
        </span>
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
        <span class="stat-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M18 20V10" />
            <path d="M12 20V4" />
            <path d="M6 20v-6" />
          </svg>
        </span>
        <div class="stat-value">{{ animatedDistance }} km</div>
        <div class="stat-label">Distanza Totale</div>
      </div>
      <div
        v-stagger
        class="stat-card"
        role="status"
        :style="{ '--stagger-index': 2 }"
      >
        <span class="stat-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5" />
            <path d="M8.5 8.5v.01" />
            <path d="M16 15.5v.01" />
            <path d="M12 12v.01" />
            <path d="M11 17v.01" />
            <path d="M7 14v.01" />
          </svg>
        </span>
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
        <span class="stat-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </span>
        <div class="stat-value">{{ animatedSpeed }} km/h</div>
        <div class="stat-label">Velocità Media</div>
      </div>
      <div
        v-stagger
        class="stat-card"
        role="status"
        :style="{ '--stagger-index': 4 }"
      >
        <span class="stat-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </span>
        <div class="stat-value">{{ animatedHours }} h</div>
        <div class="stat-label">Ore Totali</div>
      </div>
    </template>
    <button
      v-stagger
      class="stat-card stat-refresh"
      :style="{ '--stagger-index': 5 }"
      :disabled="loading"
      :aria-label="loading ? 'Aggiornamento in corso' : 'Aggiorna statistiche'"
      @click="$emit('refresh')"
    >
      <span class="stat-icon" :class="{ spin: loading }">
        <svg
          v-if="loading"
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"
          />
        </svg>
      </span>
      <div class="stat-label">
        {{ loading ? "Aggiornamento..." : "Aggiorna" }}
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, Directive } from "vue";
import BmSkeleton from "./BmSkeleton.vue";

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

let statsRaf: number | null = null;

function safeRequestAnimationFrame(cb: FrameRequestCallback): number {
  if (typeof requestAnimationFrame !== "undefined") {
    return requestAnimationFrame(cb);
  }
  return setTimeout(() => cb(performance.now()), 16) as unknown as number;
}

function safeCancelAnimationFrame(id: number | null) {
  if (!id) return;
  if (typeof cancelAnimationFrame !== "undefined") {
    cancelAnimationFrame(id);
  } else {
    clearTimeout(id as unknown as number);
  }
}

function animateStats(targets: {
  rides: number;
  dist: number;
  cals: number;
  speed: number;
  hours: number;
}) {
  if (statsRaf) safeCancelAnimationFrame(statsRaf);
  const startTime = performance.now();
  const from = {
    rides: animatedRides.value,
    dist: animatedDistance.value,
    cals: animatedCalories.value,
    speed: animatedSpeed.value,
    hours: animatedHours.value,
  };

  function step(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / 800, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    animatedRides.value = Math.round(
      from.rides + (targets.rides - from.rides) * eased,
    );
    animatedDistance.value = parseFloat(
      (from.dist + (targets.dist - from.dist) * eased).toFixed(1),
    );
    animatedCalories.value = Math.round(
      from.cals + (targets.cals - from.cals) * eased,
    );
    animatedSpeed.value = parseFloat(
      (from.speed + (targets.speed - from.speed) * eased).toFixed(1),
    );
    animatedHours.value = parseFloat(
      (from.hours + (targets.hours - from.hours) * eased).toFixed(1),
    );
    if (progress < 1) {
      statsRaf = safeRequestAnimationFrame(step);
    } else {
      statsRaf = null;
    }
  }
  statsRaf = safeRequestAnimationFrame(step);
}

onUnmounted(() => {
  if (statsRaf) {
    safeCancelAnimationFrame(statsRaf);
    statsRaf = null;
  }
});

watch(
  () => props.stats,
  (newStats) => {
    if (!newStats) return;
    animateStats({
      rides: Number(newStats.rides) || 0,
      dist: Number(newStats.distance_km) || 0,
      cals: Number(newStats.calories) || 0,
      speed: Number(newStats.avg_speed_kmh) || 0,
      hours: (Number(newStats.duration_minutes) || 0) / 60,
    });
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

.skeleton-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px 20px;
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
