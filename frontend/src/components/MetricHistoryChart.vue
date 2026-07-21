<!--
  Grafico storico per una metrica atleta (peso, % grassa, FTP, umore, sonno, altezza).
  Props: metricType (es. "weight_kg"), days (finestra temporale), label (titolo grafico).
  Store: useAthleteStore().fetchMetricLog() per caricare i dati.
  UI: BaseChart con line chart, mostra valori e timestamp.
-->
<template>
  <div class="metric-history-chart">
    <div class="metric-history-chart__header">
      <h4>{{ label }}</h4>
      <span v-if="loading" class="metric-history-chart__loading">Caricamento...</span>
    </div>
    <BaseChart
      v-if="hasData"
      :config="chartConfig"
      height="260px"
      empty-label="Nessun dato storico"
    />
    <p v-else class="metric-history-chart__empty">
      {{ emptyLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import BaseChart from "./BaseChart.vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import { useAthleteStore } from "../stores/athlete";

const props = withDefaults(
  defineProps<{
    metricType: string;
    days?: number;
    label?: string;
    emptyLabel?: string;
  }>(),
  {
    days: 365,
    label: "",
    emptyLabel: "Nessun dato storico disponibile",
  }
);

const athleteStore = useAthleteStore();

const loading = computed(() => athleteStore.metricLogLoading);
const series = computed(() => athleteStore.metricLog[props.metricType] ?? []);
const hasData = computed(() => series.value.length > 0);

const unit = computed(() => {
  const units: Record<string, string> = {
    weight_kg: "kg",
    height_cm: "cm",
    fat_percentage: "%",
    ftp_watts: "W",
    mood: "/10",
    sleep_hours: "h",
  };
  return units[props.metricType] || "";
});

const chartConfig = computed<ChartConfiguration>(() => ({
  type: "line",
  data: {
    labels: series.value.map((s) =>
      new Date(s.recorded_at).toLocaleDateString("it-IT", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    ),
    datasets: [
      {
        label: `${props.label || props.metricType} (${unit.value})`,
        data: series.value.map((s) => s.value),
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      y: {
        beginAtZero: false,
        grid: { color: "rgba(128,128,128,0.1)" },
      },
      x: {
        grid: { display: false },
        ticks: {
          maxRotation: 45,
          minRotation: 0,
        },
      },
    },
    plugins: {
      legend: { labels: { usePointStyle: true } },
      tooltip: {
        callbacks: {
          label: (ctx: any) =>
            `${ctx.dataset.label}: ${ctx.parsed.y} ${unit.value}`.trim(),
        },
      },
    },
  },
}));

async function load() {
  await athleteStore.fetchMetricLog(props.metricType, props.days);
}

onMounted(() => {
  load();
});

watch(
  () => props.metricType,
  () => {
    load();
  }
);

watch(
  () => props.days,
  () => {
    load();
  }
);
</script>

<style scoped>
.metric-history-chart {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.2rem;
  margin-bottom: 1rem;
}
.metric-history-chart__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}
.metric-history-chart__header h4 {
  margin: 0;
  font-size: 1rem;
  color: #eee;
}
.metric-history-chart__loading {
  font-size: 0.8rem;
  color: #888;
}
.metric-history-chart__empty {
  color: var(--text-muted);
  font-size: 0.9rem;
  text-align: center;
  padding: 1.5rem;
}
</style>
