<!-- Pannello tracciamento frequenza cardiaca 24h indipendente da Google Health/Fit.
     Mostra un grafico dei campioni HR, il riepilogo giornaliero, i controlli di
     start/stop tramite BLE e la configurazione del campionamento. -->

<script setup lang="ts">
import { onMounted, ref, watch, computed } from "vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import BaseChart from "./BaseChart.vue";
import { useI18n } from "../composables/useI18n";
import { useHr24h } from "../composables/useHr24h";
import { useHr24hStore } from "../stores/hr24h";
import type { Hr24hSettings, HrDailySummary } from "../types";

const { t } = useI18n();
const hr24h = useHr24h();
const store = useHr24hStore();

const showSettings = ref(false);
const localSettings = ref<Partial<Hr24hSettings>>({});

onMounted(async () => {
  await store.loadSettings();
  await store.load24h();
  await store.loadTodaySummary();
  await store.loadDailyHistory();
  localSettings.value = { ...store.settings };
});

const chartConfig = ref<ChartConfiguration>({
  type: "line",
  data: {
    labels: [] as string[],
    datasets: [
      {
        label: t("hr24h.heartRate"),
        data: [] as number[],
        borderColor: "#ef4444",
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        borderWidth: 1,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: "time" as const,
        time: { unit: "hour" as const, tooltipFormat: "HH:mm" },
        grid: { display: false },
        ticks: { maxTicksLimit: 12 },
      },
      y: {
        min: 40,
        max: 200,
        title: { display: true, text: "bpm" },
        grid: { color: "rgba(0,0,0,0.05)" },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: "index",
        intersect: false,
        callbacks: {
          label: (ctx: { parsed: { y: number } }) => `${ctx.parsed.y} bpm`,
        },
      },
    },
  },
});

function updateChart() {
  const samples = store.samples;
  chartConfig.value.data = {
    labels: samples.map((s) => s.recorded_at),
    datasets: [
      {
        label: t("hr24h.heartRate"),
        data: samples.map((s) => s.heart_rate),
        borderColor: "#ef4444",
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        borderWidth: 1,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      },
    ],
  };
}

watch(
  () => store.samples,
  () => {
    updateChart();
  },
  { deep: true },
);

const startButtonLabel = ref("");
const statusText = ref("");

watch(
  () => hr24h.isRunning.value,
  (running) => {
    startButtonLabel.value = running ? t("hr24h.stop") : t("hr24h.start");
    statusText.value = running
      ? hr24h.isConnected.value
        ? `${t("hr24h.connected")} ${hr24h.deviceLabel.value || ""}`
        : t("hr24h.starting")
      : t("hr24h.stopped");
  },
);

async function toggleMonitoring() {
  if (hr24h.isRunning.value) {
    await hr24h.stop();
  } else {
    await hr24h.start();
  }
}

async function applySettings() {
  showSettings.value = false;
  await store.saveSettings(localSettings.value);
}

const todaySummary = ref<HrDailySummary | null>(null);
const dailyHistory = ref<HrDailySummary[]>([]);

watch(
  () => store.todaySummary,
  (s) => {
    todaySummary.value = s;
  },
);

watch(
  () => store.dailyHistory,
  (h) => {
    dailyHistory.value = h;
  },
);

const avgHrDisplay = computed(() =>
  todaySummary.value?.avg_hr != null
    ? `${todaySummary.value.avg_hr.toFixed(0)} bpm`
    : t("hr24h.noData"),
);

const restingHrDisplay = computed(() =>
  todaySummary.value?.resting_hr != null
    ? `${todaySummary.value.resting_hr.toFixed(0)} bpm`
    : t("hr24h.noData"),
);

const sampleCountDisplay = computed(() =>
  todaySummary.value
    ? `${todaySummary.value.sample_count} ${t("hr24h.samples")}`
    : "",
);
</script>

<template>
  <div class="p-4">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-semibold">{{ t("hr24h.title") }}</h2>
      <div class="flex items-center gap-3">
        <span
          v-if="statusText"
          class="text-sm text-gray-600 dark:text-gray-400"
          >{{ statusText }}</span
        >
        <button
          v-if="hr24h.isRunning.value"
          class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          @click="toggleMonitoring"
        >
          {{ startButtonLabel || t("hr24h.stop") }}
        </button>
        <button
          v-else
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          @click="toggleMonitoring"
        >
          {{ startButtonLabel || t("hr24h.start") }}
        </button>
        <button
          class="px-3 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
          aria-label="Impostazioni HR"
          @click="showSettings = true"
        >
          ⚙️
        </button>
      </div>
    </div>

    <div
      v-if="hr24h.error.value"
      class="mb-3 p-3 bg-red-100 text-red-800 rounded-lg"
    >
      {{ hr24h.error.value }}
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ t("hr24h.resting") }}
        </span>
        <p class="text-2xl font-bold mt-1">{{ restingHrDisplay }}</p>
      </div>
      <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ t("hr24h.average") }}
        </span>
        <p class="text-2xl font-bold mt-1">{{ avgHrDisplay }}</p>
      </div>
      <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ t("hr24h.samples") }}
        </span>
        <p class="text-2xl font-bold mt-1">{{ sampleCountDisplay }}</p>
      </div>
    </div>

    <div class="h-64 mb-6">
      <BaseChart :config="chartConfig" />
    </div>

    <div v-if="dailyHistory.length > 0" class="mt-6">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {{ t("hr24h.history") }}
      </h3>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 dark:text-gray-400">
              <th class="pb-2">{{ t("hr24h.day") }}</th>
              <th class="pb-2 text-right">{{ t("hr24h.resting") }}</th>
              <th class="pb-2 text-right">{{ t("hr24h.avg") }}</th>
              <th class="pb-2 text-right">{{ t("hr24h.max") }}</th>
              <th class="pb-2 text-right">{{ t("hr24h.samples") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="h in dailyHistory"
              :key="h.day"
              class="border-t border-gray-200 dark:border-gray-700"
            >
              <td class="py-2">{{ h.day }}</td>
              <td class="py-2 text-right">
                {{
                  h.resting_hr != null ? `${h.resting_hr.toFixed(0)} bpm` : "—"
                }}
              </td>
              <td class="py-2 text-right">
                {{ h.avg_hr != null ? `${h.avg_hr.toFixed(0)} bpm` : "—" }}
              </td>
              <td class="py-2 text-right">
                {{ h.max_hr != null ? `${h.max_hr.toFixed(0)} bpm` : "—" }}
              </td>
              <td class="py-2 text-right">{{ h.sample_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="showSettings"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4"
      >
        <h3 class="text-lg font-semibold mb-4">{{ t("hr24h.settings") }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-300 mb-1">
              {{ t("hr24h.interval") }}
            </label>
            <input
              v-model.number="localSettings.interval_seconds"
              type="number"
              min="10"
              max="300"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-300 mb-1">
              {{ t("hr24h.maxHr") }}
            </label>
            <input
              v-model.number="localSettings.max_hr"
              type="number"
              min="40"
              max="300"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-300 mb-1">
              {{ t("hr24h.restingHr") }}
            </label>
            <input
              v-model.number="localSettings.resting_hr"
              type="number"
              min="30"
              max="120"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-300 mb-1">
              {{ t("hr24h.deviceId") }}
            </label>
            <input
              v-model="localSettings.device_id"
              type="text"
              placeholder="es. AA:BB:CC:DD:EE:FF"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700"
            />
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button
            class="px-4 py-2 text-gray-600 hover:text-gray-800"
            @click="showSettings = false"
          >
            {{ t("hr24h.cancel") }}
          </button>
          <button
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            @click="applySettings"
          >
            {{ t("hr24h.save") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
