<template>
  <section>
    <div class="panel">
      <h2>📊 Statistiche Performance</h2>
      <canvas ref="chartCanvas" width="400" height="200"></canvas>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, watch } from "vue"

const props = defineProps({ rides: Array })
const chartCanvas = ref(null)

function renderChart() {
  if (!chartCanvas.value || !props.rides?.length) return
  const labels = props.rides.map(r => r.date?.slice(5) || "Ride")
  const speeds = props.rides.map(r => r.avg_speed_kmh || 0)
  // Fallback per Chart.js non installato
  const ctx = chartCanvas.value.getContext("2d")
  ctx.fillStyle = "#333"
  ctx.fillRect(0, 0, 400, 200)
  ctx.fillStyle = "#FF6B00"
  ctx.font = "14px sans-serif"
  ctx.fillText("Chart.js integration needed", 50, 100)
}

onMounted(() => {
  renderChart()
})

watch(() => props.rides, renderChart)
</script>
