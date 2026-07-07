<template>
  <section class="charts-panel">
    <div class="panel">
      <h2>📊 Performance Trends</h2>
      <div class="chart-controls">
        <label>
          Metric:
          <select v-model="selectedMetric">
            <option value="distance_km">Distance (km)</option>
            <option value="avg_speed_kmh">Avg Speed (km/h)</option>
            <option value="duration_minutes">Duration (min)</option>
            <option value="calories">Calories</option>
            <option value="elevation_gain_m">Elevation (m)</option>
          </select>
        </label>
        <label>
          Window:
          <select v-model="windowSize">
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
          <canvas ref="trendCanvas" />
          <div v-if="trendData.ready" class="chart-summary">
            <span :class="trendClass">{{ trendData.trend }}</span>
            <span>R²: {{ trendData.r2 }}</span>
            <span>Mean: {{ trendData.mean?.toFixed(1) }}</span>
          </div>
        </div>
        <div class="chart-card">
          <h3>📆 Monthly Progression</h3>
          <canvas ref="monthlyCanvas" />
        </div>
        <div class="chart-card">
          <h3>Period Comparison</h3>
          <canvas ref="comparisonCanvas" />
          <div v-if="comparisonData.ready" class="chart-summary">
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

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from "vue";
import { apiGet } from "../utils/api";

const props = defineProps({ rides: Array });
const selectedMetric = ref("distance_km");
const windowSize = ref(7);
const trendCanvas = ref(null);
const monthlyCanvas = ref(null);
const comparisonCanvas = ref(null);
const trendData = ref({
  ready: false,
  trend: "—",
  r2: 0,
  mean: 0,
  values: [],
  dates: [],
  rolling_avg: [],
});
const monthlyData = ref({
  ready: false,
  months: [],
  total_distance_km: [],
  avg_speed_kmh: [],
  total_duration_hours: [],
  ride_count: [],
});
const comparisonData = ref({
  ready: false,
  distance_change_pct: 0,
  speed_change_pct: 0,
  recent_rides: 0,
  previous_rides: 0,
});
let trendChart = null;
let monthlyChart = null;
let comparisonChart = null;

const metricLabel = computed(() => {
  const map = {
    distance_km: "Distance",
    avg_speed_kmh: "Speed",
    duration_minutes: "Duration",
    calories: "Calories",
    elevation_gain_m: "Elevation",
  };
  return map[selectedMetric.value] || selectedMetric.value;
});

const trendClass = computed(() => {
  if (trendData.value.trend === "improving") return "trend-up";
  if (trendData.value.trend === "declining") return "trend-down";
  return "trend-neutral";
});

async function loadTrends() {
  try {
    const data = await apiGet(
      `/api/v1/analytics/trends?metric=${selectedMetric.value}&window=${windowSize.value}`,
    );
    trendData.value = data;
    renderTrendChart();
  } catch (e) {
    console.error("trends load failed", e);
  }
}

async function loadMonthly() {
  try {
    const data = await apiGet("/api/v1/analytics/monthly");
    monthlyData.value = data;
    renderMonthlyChart();
  } catch (e) {
    console.error("monthly load failed", e);
  }
}

async function loadComparison() {
  try {
    const data = await apiGet("/api/v1/analytics/comparison?period_days=7");
    comparisonData.value = data;
    renderComparisonChart();
  } catch (e) {
    console.error("comparison load failed", e);
  }
}

function renderTrendChart() {
  if (!trendCanvas.value) return;
  const ctx = trendCanvas.value.getContext("2d");
  if (trendChart) trendChart.destroy();

  const data = trendData.value;
  if (!data.ready || !data.values?.length) {
    trendChart = null;
    return;
  }

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.dates.map((d) => d?.slice(5) || "?"),
      datasets: [
        {
          label: metricLabel.value,
          data: data.values,
          borderColor: "#FF6B00",
          backgroundColor: "rgba(255,107,0,0.1)",
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
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#ccc" } },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x: {
          ticks: { color: "#999", maxTicksLimit: 12 },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          ticks: { color: "#999" },
          grid: { color: "rgba(255,255,255,0.1)" },
        },
      },
    },
  });
}

function renderMonthlyChart() {
  if (!monthlyCanvas.value) return;
  const ctx = monthlyCanvas.value.getContext("2d");
  if (monthlyChart) monthlyChart.destroy();

  const data = monthlyData.value;
  if (!data.ready || !data.months?.length) {
    monthlyChart = null;
    return;
  }

  monthlyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.months,
      datasets: [
        {
          label: "Distance (km)",
          data: data.total_distance_km,
          backgroundColor: "#4ecca3",
          yAxisID: "y",
        },
        {
          label: "Duration (h)",
          data: data.total_duration_hours,
          backgroundColor: "#FF6B00",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#ccc" } } },
      scales: {
        x: {
          ticks: { color: "#999" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          position: "left",
          ticks: { color: "#4ecca3" },
          grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
        },
        y1: {
          position: "right",
          ticks: { color: "#FF6B00" },
          grid: { display: false },
        },
      },
    },
  });
}

function renderComparisonChart() {
  if (!comparisonCanvas.value) return;
  const ctx = comparisonCanvas.value.getContext("2d");
  if (comparisonChart) comparisonChart.destroy();

  const data = comparisonData.value;
  if (!data.ready) {
    comparisonChart = null;
    return;
  }

  comparisonChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Recent Period", "Previous Period"],
      datasets: [
        {
          label: "Distance (km)",
          data: [data.recent_distance_km, data.previous_distance_km],
          backgroundColor: ["#4ecca3", "#888"],
        },
        {
          label: "Avg Speed (km/h)",
          data: [data.recent_avg_speed, data.previous_avg_speed],
          backgroundColor: ["#FF6B00", "#666"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#ccc" } } },
      scales: {
        x: {
          ticks: { color: "#999" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          ticks: { color: "#999" },
          grid: { color: "rgba(255,255,255,0.1)" },
        },
      },
    },
  });
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

onUnmounted(() => {
  if (trendChart) trendChart.destroy();
  if (monthlyChart) monthlyChart.destroy();
  if (comparisonChart) comparisonChart.destroy();
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
