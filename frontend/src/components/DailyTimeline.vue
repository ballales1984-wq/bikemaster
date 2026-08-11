<!--
  DailyTimeline — Timeline verticale H24 stile Google Fit.
  Mostra i segmenti di attivita del giorno corrente come blocchi colorati
  lungo una barra temporale. Ogni segmento mostra durata e distanza.
  Emette 'select' quando l'utente clicca un segmento.
-->
<template>
  <div class="daily-timeline">
    <div class="timeline-track">
      <div
        v-for="segment in segments"
        :key="segment.id"
        class="timeline-segment"
        :class="[segment.state, { active: segment.state === 'active' }]"
        :style="segmentStyle(segment)"
        :title="segmentTitle(segment)"
        @click="$emit('select', segment.id)"
      >
        <div class="segment-inner">
          <span class="segment-duration">{{ formatDuration(segment) }}</span>
          <span class="segment-distance">{{ formatDistance(segment) }}</span>
        </div>
      </div>
    </div>
    <div class="timeline-labels">
      <span v-for="hour in hours" :key="hour" class="hour-label">
        {{ hour.toString().padStart(2, "0") }}:00
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ActivitySegment } from "../stores/trackingStore";

const props = defineProps<{
  segments: ActivitySegment[];
}>();

defineEmits<{
  (e: "select", id: string): void;
}>();

const hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22];

function startOfDay(): number {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

function segmentStyle(segment: ActivitySegment) {
  const dayStart = startOfDay();
  const dayMs = 86400000;
  const startHour = Math.max(0, (segment.startTime - dayStart) / dayMs);
  const endMs = segment.endTime ?? Date.now();
  const endHour = Math.min(1, (endMs - dayStart) / dayMs);
  const width = Math.max(endHour - startHour, 0.01);
  const left = startHour * 100;

  const colors: Record<string, string> = {
    active: "#10b981",
    candidate: "#3b82f6",
    paused: "#f59e0b",
    idle: "#64748b",
  };

  return {
    left: `${left}%`,
    width: `${width * 100}%`,
    backgroundColor: colors[segment.state] || "#64748b",
  };
}

function segmentTitle(segment: ActivitySegment): string {
  const duration = formatDuration(segment);
  const distance = formatDistance(segment);
  const type =
    segment.state === "active"
      ? "In corso"
      : segment.state === "paused"
        ? "In pausa"
        : segment.state === "candidate"
          ? "In rilevamento"
          : "Ferm";
  return `${type}: ${duration} - ${distance}`;
}

function formatDuration(segment: ActivitySegment): string {
  const end = segment.endTime ?? Date.now();
  const seconds = Math.floor((end - segment.startTime) / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

function formatDistance(segment: ActivitySegment): string {
  const km = segment.distanceM / 1000;
  return `${km.toFixed(1)} km`;
}
</script>

<style scoped>
.daily-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-track {
  position: relative;
  height: 48px;
  background: rgba(100, 116, 139, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.timeline-segment {
  position: absolute;
  top: 4px;
  bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    opacity 0.15s ease;
  min-width: 4px;
  overflow: hidden;
}

.timeline-segment:hover {
  transform: scaleY(1.15);
  opacity: 0.9;
  z-index: 2;
}

.timeline-segment.active {
  animation: segmentPulse 2s ease-in-out infinite;
}

@keyframes segmentPulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0);
  }
}

.segment-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2px 6px;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  white-space: nowrap;
  overflow: hidden;
}

.segment-duration {
  line-height: 1;
}

.segment-distance {
  font-size: 0.65rem;
  opacity: 0.9;
}

.timeline-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
}

.hour-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}
</style>
