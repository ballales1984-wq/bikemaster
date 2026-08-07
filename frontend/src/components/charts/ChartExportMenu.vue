<!-- ChartExportMenu: menu export per grafici Chart.js.
     Props: chart (istanza Chart.js), filename (default "chart").
     Eventi: nessuno. Azioni: PNG, CSV (dati labels/dataset).
     UI: icona download con dropdown. -->
<template>
  <div class="chart-export">
    <button
      class="chart-export__btn"
      :aria-label="t('charts.export')"
      @click="open = !open"
    >
      <span aria-hidden="true">⬇</span>
    </button>
    <div v-if="open" class="chart-export__menu">
      <button @click="exportPng">
        {{ t("charts.exportPng") }}
      </button>
      <button @click="exportCsv">
        {{ t("charts.exportCsv") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "../../composables/useI18n";

const { t } = useI18n();

const props = defineProps<{
  chart: any;
  filename?: string;
}>();

const open = ref(false);

function exportPng() {
  if (!props.chart) return;
  const url = (props.chart as any).toBase64Image?.();
  if (!url) return;
  const link = document.createElement("a");
  link.download = `${props.filename || "chart"}.png`;
  link.href = url;
  link.click();
  open.value = false;
}

function exportCsv() {
  if (!props.chart) return;
  const cfg = props.chart.config;
  const labels = cfg.data?.labels || [];
  const datasets = cfg.data?.datasets || [];
  const rows: string[][] = [["label", ...datasets.map((ds: any) => ds.label)]];

  labels.forEach((label: any, i: number) => {
    const row = [String(label)];
    datasets.forEach((ds: any) => {
      const val = Array.isArray(ds.data) ? ds.data[i] : "";
      row.push(String(val ?? ""));
    });
    rows.push(row);
  });

  const csv = rows
    .map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.download = `${props.filename || "chart"}.csv`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
  open.value = false;
}

function handleClickOutside(e: MouseEvent) {
  if ((e.target as HTMLElement).closest(".chart-export")) return;
  open.value = false;
}

onMounted(() => document.addEventListener("click", handleClickOutside));
onBeforeUnmount(() =>
  document.removeEventListener("click", handleClickOutside),
);
</script>

<style scoped>
.chart-export {
  position: relative;
  display: inline-flex;
}
.chart-export__btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: all 0.15s;
}
.chart-export__btn:hover {
  color: var(--text-primary);
  background: var(--border);
}
.chart-export__menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px;
  min-width: 160px;
  box-shadow: var(--shadow-lg);
}
.chart-export__menu button {
  background: none;
  border: none;
  color: var(--text-primary);
  padding: 8px 12px;
  text-align: left;
  cursor: pointer;
  border-radius: 6px;
  font-size: 0.85rem;
}
.chart-export__menu button:hover {
  background: var(--border);
}
</style>
