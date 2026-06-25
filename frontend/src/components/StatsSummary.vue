<template>
  <div class="stats" aria-label="General Statistics">
    <div class="stat-card" role="status">
      <div class="stat-value"><AnimatedNumber :value="stats?.rides ?? 0" :decimals="0" /></div>
      <div class="stat-label">Rides</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value"><AnimatedNumber :value="stats?.distance_km ?? 0" :decimals="1" /> km</div>
      <div class="stat-label">Total Distance</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value"><AnimatedNumber :value="stats?.calories ?? 0" :decimals="0" /></div>
      <div class="stat-label">Calories</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value"><AnimatedNumber :value="stats?.avg_speed_kmh ?? 0" :decimals="1" /> km/h</div>
      <div class="stat-label">Avg Speed</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value"><AnimatedNumber :value="hoursFromMin" :decimals="1" /></div>
      <div class="stat-label">Total Hours</div>
    </div>
    <button class="stat-card stat-refresh" @click="$emit('refresh')" :disabled="loading" :aria-label="loading ? 'Updating in progress' : 'Refresh statistics'">
      <span :class="{ spinner: loading }">{{ loading ? '' : '🔄' }}</span>
      <div class="stat-label">{{ loading ? 'Updating...' : 'Refresh' }}</div>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

defineEmits(['refresh'])

const hoursFromMin = computed(() => {
  const m = props.stats?.duration_minutes
  if (m == null || isNaN(m)) return 0
  return Number(m) / 60
})

// Animated number component inline
const AnimatedNumber = {
  props: {
    value: { type: Number, required: true },
    decimals: { type: Number, default: 0 },
    duration: { type: Number, default: 1000 }
  },
  data() {
    return { displayed: 0 }
  },
  computed: {
    formatted() {
      return this.displayed.toFixed(this.decimals)
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(newVal) {
        this.animateTo(newVal)
      }
    }
  },
  methods: {
    animateTo(to) {
      const from = this.displayed
      const start = performance.now()
      const step = (now) => {
        const elapsed = now - start
        const progress = Math.min(elapsed / this.duration, 1)
        this.displayed = from + (to - from) * progress
        if (progress < 1) requestAnimationFrame(step)
      }
      requestAnimationFrame(step)
    }
  },
  template: '{{ formatted }}'
}
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
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 2px;
  background: var(--accent-gradient);
  opacity: 0;
  transition: var(--transition);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--border-light);
}

.stat-card:hover::after { opacity: 1; }

.stat-value {
  font-size: 2rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
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
