<!--
  ActivityRings — Cerchi concentrici stile Apple Watch / Google Fit.
  Mostra tre anelli: Move (minuti attivi), Exercise (esercizio intenso),
  Stand (sessioni ferme). Ogni anello ha un obiettivo configurabile.
-->
<template>
  <div class="activity-rings">
    <svg viewBox="0 0 200 200" class="rings-svg">
      <g transform="translate(100, 100)">
        <circle
          v-for="(ring, index) in rings"
          :key="ring.label"
          :r="ringRadius(index)"
          fill="none"
          :stroke="ring.color"
          stroke-width="12"
          stroke-linecap="round"
          stroke-dasharray="circumference(index)"
          :stroke-dashoffset="dashOffset(index)"
          transform="rotate(-90)"
          class="ring-circle"
          :style="{ transition: 'stroke-dashoffset 0.8s ease-out' }"
        />
      </g>
    </svg>
    <div class="rings-legend">
      <div v-for="ring in rings" :key="ring.label" class="legend-item">
        <span class="legend-dot" :style="{ backgroundColor: ring.color }"></span>
        <span class="legend-label">{{ ringLabel(ring.label) }}</span>
        <span class="legend-value">
          {{ ring.current }}/{{ ring.goal }}{{ ring.unit }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ActivityRing } from "../stores/trackingStore";

const props = defineProps<{
  rings: ActivityRing[];
}>();

const ringRadius = (index: number): number => 85 - index * 16;

function circumference(index: number): number {
  const r = ringRadius(index);
  return 2 * Math.PI * r;
}

function dashOffset(index: number): number {
  const ring = props.rings[index];
  if (!ring) return circumference(index);
  const progress = Math.min(ring.current / ring.goal, 1);
  return circumference(index) * (1 - progress);
}

function ringLabel(label: string): string {
  const labels: Record<string, string> = {
    move: "Muovi",
    exercise: "Esercizio",
    stand: "In piedi",
  };
  return labels[label] || label;
}
</script>

<style scoped>
.activity-rings {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.rings-svg {
  width: 180px;
  height: 180px;
}

.ring-circle {
  opacity: 0.9;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}

.rings-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-label {
  color: var(--text-secondary);
}

.legend-value {
  font-weight: 600;
  color: var(--text-primary);
}
</style>
