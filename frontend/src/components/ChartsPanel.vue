<!-- Pannello grafici performance: trend di una metrica selezionata, progressione mensile e confronto periodi.
     Props: nessuna. Eventi: nessuno (usa /api/v1/analytics). Selettori metrica (distanza, velocità, durata, calorie, dislivello) e finestra.
     UI: tre card BaseChart (trend con media mobile, barre mensili, confronto periodi) con riepilogo trend/R²/variazioni %. -->
<template>
  <section class="charts-panel">
    <div class="panel">
      <h2> Performance Trends</h2>
      <div class="chart-controls">
        <label>
          {{ t("charts.metric") }}
          <select id="metric-select"
name="metric" v-model="selectedMetric">
            <option value="distance_km">Distance (km)</option>
            <option value="avg_speed_kmh">Avg Speed (km/h)</option>
            <option value="duration_minutes">Duration (min)</option>
            <option value="calories">Calories</option>
            <option value="elevation_gain_m">Elevation (m)</option>
          </select>
        </label>
        <label>
          {{ t("charts.window") }}
          <select id="window-select"
name="window" v-model.number="windowSize">
            <option value="3">3 rides</option>
            <option value="7">7 rides</option>
            <option value="14">14 rides</option>
            <option value="30">30 rides</option>
          </select>
        </label>
      </div>
      <div class="chart-grid">
        <div class="chart-card">
          <h3>Trend {{ metricLabel }}</h3>
          <BaseChart :config="trendConfig" empty-label="Dati insufficienti" />
          <div v-if="trendData.ready"
class="chart-summary">
            <span :class="trendClass">{{ trendData.trend }}</span>
            <span>R²: {{ trendData.r2 }}</span>
            <span>Mean: {{ trendData.mean?.toFixed(1) }}</span>
          </div>
        </div>
        <div class="chart-card">
          <h3> Monthly Progression</h3>
          <BaseChart
            :config="monthlyConfig"
            empty-label="Nessun dato mensile"
          />
        </div>
        <div class="chart-card">
          <h3>{{ t("charts.periodComparison") }}</h3>
          <BaseChart
            :config="comparisonConfig"
            empty-label="Nessun confronto"
          />
          <div v-if="comparisonData.ready"
class="chart-summary">
            <span :class="trendClass"
              >{{ comparisonData.distance_change_pct >= 0 ? "+" : ""
              }}{{ comparisonData.distance_change_pct }}% km</span
            >
            <span :class="trendClass"
              >{{ comparisonData.speed_change_pct >= 0 ? "+" : ""
              }}{{ comparisonData.speed_change_pct }}% speed</span
            >
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import BaseChart from "./BaseChart.vue";
import { useI18n } from "../composables/useI18n";
import { apiGet } from "../utils/api";
import { chartTheme } from "../utils/chartTheme";

const { t } = useI18n();

type MetricKey =
  | "distance_km"
  | "avg_speed_kmh"
  | "duration_minutes"
  | "calories"
  | "elevation_gain_m";

const selectedMetric = ref<MetricKey>("distance_km");
const windowSize = ref(7);

interface TrendResponse {
  ready: boolean;
  trend: string;
  r2: number;
  mean: number;
  values: number[];
  dates: string[];
  rolling_avg: number[];
}

interface MonthlyResponse {
  ready: boolean;
  months: string[];
  total_distance_km: number[];
  avg_speed_kmh: number[];
  total_duration_hours: number[];
  ride_count: number[];
}

interface ComparisonResponse {
  ready: boolean;
  distance_change_pct: number;
  speed_change_pct: number;
  recent_distance_km?: number;
  previous_distance_km?: number;
  recent_avg_speed?: number;
  previous_avg_speed?: number;
  recent_rides: number;
  previous_rides: number;
}

const trendData = ref<TrendResponse>({
  ready: false,
  trend: "—",
  r2: 0,
  mean: 0,
  values: [],
  dates: [],
  rolling_avg: [],
});

const monthlyData = ref<MonthlyResponse>({
  ready: false,
  months: [],
  total_distance_km: [],
  avg_speed_kmh: [],
  total_duration_hours: [],
  ride_count: [],
});

const comparisonData = ref<ComparisonResponse>({
  ready: false,
  distance_change_pct: 0,
  speed_change_pct: 0,
  recent_rides: 0,
  previous_rides: 0,
});

const metricLabel = computed(() => {
  const map: Record<MetricKey, string> = {
    distance_km: "Distance",
    avg_speed_kmh: "Speed",
    duration_minutes: "Duration",
    calories: "Calories",
    elevation_gain_m: "Elevation",
  };
  return map[selectedMetric.value];
});

const trendClass = computed(() => {
  if (trendData.value.trend === "improving") return "trend-up";
  if (trendData.value.trend === "declining") return "trend-down";
  return "trend-neutral";
});

const trendConfig = computed<ChartConfiguration>(() => {
  const data = trendData.value;
  const p = chartTheme.palette.value;
  return {
    type: "line",
    data: {
      labels: (data.dates || []).map((d) => d?.slice(5) || "?"),
      datasets: [
        {
          label: metricLabel.value,
          data: data.values,
          borderColor: p.accent,
          backgroundColor: "rgba(0,255,204,0.1)",
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        ...(data.rolling_avg?.length
          ? [
              {
                label: `Moving avg (${windowSize.value})`,
                data: data.rolling_avg,
                borderColor: "#4ecca3",
                backgroundColor: "transparent",
                borderDash: [5, 5],
                tension: 0.4,
                pointRadius: 0,
                fill: false,
              },
            ]
          : []),
      ],
    },
    options: {
      scales: {
        x: { ticks: { maxTicksLimit: 12 } },
      },
    },
  } as ChartConfiguration;
});

const monthlyConfig = computed<ChartConfiguration>(() => {
  const data = monthlyData.value;
  return {
    type: "bar",
    data: {
      labels: data.months || [],
      datasets: [
        {
          label: "Distance (km)",
          data: data.total_distance_km || [],
          backgroundColor: "#4ecca3",
          yAxisID: "y",
        },
        {
          label: "Duration (h)",
          data: data.total_duration_hours || [],
          backgroundColor: "#FF6B00",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      scales: {
        y: { position: "left", ticks: { color: "#4ecca3" } },
        y1: { position: "right", grid: { display: false } },
      },
    },
  } as ChartConfiguration;
});

const comparisonConfig = computed<ChartConfiguration>(() => {
  const data = comparisonData.value;
  return {
    type: "bar",
    data: {
      labels: ["Recent Period", "Previous Period"],
      datasets: [
        {
          label: "Distance (km)",
          data: [data.recent_distance_km ?? 0, data.previous_distance_km ?? 0],
          backgroundColor: ["#4ecca3", "#888"],
        },
        {
          label: "Avg Speed (km/h)",
          data: [data.recent_avg_speed ?? 0, data.previous_avg_speed ?? 0],
          backgroundColor: ["#FF6B00", "#666"],
        },
      ],
    },
    options: {},
  } as ChartConfiguration;
});

async function loadTrends() {
  try {
    trendData.value = await apiGet<TrendResponse>(
      `/api/v1/analytics/trends?metric=${selectedMetric.value}&window=${windowSize.value}`,
    );
  } catch (e) {
    console.error("trends load failed", e);
  }
}

async function loadMonthly() {
  try {
    monthlyData.value = await apiGet<MonthlyResponse>(
      "/api/v1/analytics/monthly",
    );
  } catch (e) {
    console.error("monthly load failed", e);
  }
}

async function loadComparison() {
  try {
    comparisonData.value = await apiGet<ComparisonResponse>(
      "/api/v1/analytics/comparison?period_days=7",
    );
  } catch (e) {
    console.error("comparison load failed", e);
  }
}

watch([selectedMetric, windowSize], () => {
  loadTrends();
  loadComparison();
});

onMounted(() => {
  loadTrends();
  loadMonthly();
  loadComparison();
});
</script>

<style scoped>
.charts-panel {
  margin: 1rem 0;
}
.chart-controls {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.chart-controls label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #ccc;
  font-size: 0.9rem;
}
.chart-controls select {
  background: #16213e;
  color: #eee;
  border: 1px solid #333;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
}
</style>
