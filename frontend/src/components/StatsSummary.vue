<template>
  <div class="stats"
aria-label="General Statistics">
    <div class="stat-card"
role="status">
      <div class="stat-value">
        {{ animatedRides }}
      </div>
      <div class="stat-label">Rides</div>
    </div>
    <div class="stat-card"
role="status">
      <div class="stat-value">{{ animatedDistance }} km</div>
      <div class="stat-label">Total Distance</div>
    </div>
    <div class="stat-card"
role="status">
      <div class="stat-value">
        {{ animatedCalories }}
      </div>
      <div class="stat-label">Calories</div>
    </div>
    <div class="stat-card"
role="status">
      <div class="stat-value">{{ animatedSpeed }} km/h</div>
      <div class="stat-label">Avg Speed</div>
    </div>
    <div class="stat-card"
role="status">
      <div class="stat-value">{{ animatedHours }} h</div>
      <div class="stat-label">Total Hours</div>
    </div>
    <button
      class="stat-card stat-refresh"
      :disabled="loading"
      :aria-label="loading ? 'Updating in progress' : 'Refresh statistics'"
      @click="$emit('refresh')"
    >
      <span :class="{ spinner: loading }">{{ loading ? "" : "🔄" }}</span>
      <div class="stat-label">
        {{ loading ? "Updating..." : "Refresh" }}
      </div>
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  stats: { type: Object, default: null },
  loading: { type: Boolean, default: false },
});

defineEmits(["refresh"]);

const animatedRides = ref(0);
const animatedDistance = ref(0);
const animatedCalories = ref(0);
const animatedSpeed = ref(0);
const animatedHours = ref(0);

function animate(to, from = 0, duration = 800) {
  return new Promise((resolve) => {
    const start = performance.now();
    const step = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = from + (to - from) * eased;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        resolve(value);
      }
    };
    requestAnimationFrame(step);
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
    animate(dist).then((v) => (animatedDistance.value = v.toFixed(1)));
    animate(cals).then((v) => (animatedCalories.value = Math.round(v)));
    animate(speed).then((v) => (animatedSpeed.value = v.toFixed(1)));
    animate(hours).then((v) => (animatedHours.value = v.toFixed(1)));
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
  box-shadow: var(--shadow-lg);
  border-color: var(--border-light);
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
</style>
