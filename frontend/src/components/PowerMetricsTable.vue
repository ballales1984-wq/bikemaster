<template>
  <div class="power-table">
    <div class="header">
      <h3>Metriche di potenza</h3>
      <button class="recompute"
:disabled="loading" @click="$emit('recompute')">
        {{ loading ? "Ricalcolo..." : "Ricalcola tutte" }}
      </button>
    </div>

    <p v-if="!metrics.length" class="empty">
      Nessuna metrica di potenza calcolata.
    </p>

    <table v-else>
      <thead>
        <tr>
          <th>Data</th>
          <th>Ride</th>
          <th>Avg P (W)</th>
          <th>NP (W)</th>
          <th>IF</th>
          <th>TSS</th>
          <th>FTP (W)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in metrics"
:key="m.id ?? m.ride_id ?? m.date">
          <td>{{ m.date }}</td>
          <td>#{{ m.ride_id ?? "—" }}</td>
          <td>{{ fmt(m.average_power) }}</td>
          <td>{{ fmt(m.normalized_power) }}</td>
          <td>{{ fmt(m.intensity_factor, 3) }}</td>
          <td>{{ fmt(m.tss) }}</td>
          <td>{{ fmt(m.ftp_watts) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { PerformanceMetrics } from "../types/index";

defineProps<{ metrics: PerformanceMetrics[]; loading: boolean }>();
defineEmits<{ (e: "recompute"): void }>();

function fmt(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
h3 {
  margin: 0;
}
.recompute {
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  border: none;
  background: var(--accent, #4ecca3);
  color: #04221a;
  font-weight: 600;
  cursor: pointer;
}
.recompute:disabled {
  opacity: 0.6;
  cursor: default;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th,
td {
  text-align: right;
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--border);
}
th:first-child,
td:first-child {
  text-align: left;
}
.empty {
  color: var(--text-muted);
  padding: 0.5rem 0;
}
</style>
