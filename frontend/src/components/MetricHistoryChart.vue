<!--
  Grafico storico per una metrica atleta (peso, % grassa, FTP, umore, sonno, altezza).
  Props: metricType (es. "weight_kg"), days (finestra temporale), label (titolo grafico).
  Store: useAthleteStore().fetchMetricLog() per caricare i dati.
  UI: LineChart con line chart, mostra valori e timestamp.
-->
<template>
  <div class="metric-history-chart">
    <div class="metric-history-chart__header">
      <h4>{{ label }}</h4>
      <span v-if="loading" class="metric-history-chart__loading"
        >Caricamento...</span
      >
    </div>
    <LineChart
      v-if="hasData"
      :labels="formattedDates"
      :data="values"
      :label="chartLabel"
      :unit="unit"
      height="260px"
      :empty-label="emptyLabel"
    />
    <p v-else class="metric-history-chart__empty">
      {{ emptyLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import LineChart from "../components/charts/LineChart.vue";
import { useAthleteStore } from "../stores/athlete";
import { formatDateFull } from "../utils/chartFormatters";

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
  },
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

const formattedDates = computed(() =>
  series.value.map((s) => formatDateFull(s.recorded_at)),
);

const values = computed(() => series.value.map((s) => s.value));

const chartLabel = computed(() => {
  const base = props.label || props.metricType;
  return unit.value ? `${base} ${unit.value}` : base;
});

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
  },
);

watch(
  () => props.days,
  () => {
    load();
  },
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
