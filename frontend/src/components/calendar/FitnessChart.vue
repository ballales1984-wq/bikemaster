<template>
  <div class="panel fitness-chart-panel">
    <h2>📈 Fitness ATL / CTL / TSB</h2>
    <canvas ref="canvas"
height="200" />
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from "vue";
import Chart from "chart.js/auto";

const props = defineProps({
  data: Array,
});

const canvas = ref(null);
let chart = null;

function render() {
  if (!canvas.value || !props.data?.length) return;
  const labels = props.data.map((d) => {
    const dt = new Date(d.date);
    return `${dt.getDate()}/${dt.getMonth() + 1}`;
  });
  const atl = props.data.map((d) => d.atl);
  const ctl = props.data.map((d) => d.ctl);
  const tsb = props.data.map((d) => d.tsb);
  if (chart) chart.destroy();
  const ctx = canvas.value.getContext("2d");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "ATL (Fatica)",
          data: atl,
          borderColor: "var(--color-efficiency)",
          backgroundColor: "rgba(255,107,53,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: "CTL (Fitness)",
          data: ctl,
          borderColor: "var(--color-endurance)",
          backgroundColor: "rgba(0,136,255,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: "TSB (Forma)",
          data: tsb,
          borderColor: "var(--color-performance)",
          backgroundColor: "rgba(0,255,204,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: {
            color: "var(--text-secondary)",
            usePointStyle: true,
            padding: 16,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: "var(--text-muted)",
            maxRotation: 0,
            maxTicksLimit: 10,
          },
          grid: { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          ticks: { color: "var(--text-muted)" },
          grid: { color: "rgba(255,255,255,0.06)" },
        },
      },
    },
  });
}

watch(() => props.data, render, { deep: true });

onUnmounted(() => {
  if (chart) chart.destroy();
});
</script>

<style scoped>
.fitness-chart-panel {
  position: relative;
  height: 260px;
}
</style>
