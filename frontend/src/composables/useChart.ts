import { onMounted, watch, ref, type Ref } from 'vue'
import { Chart, type ChartConfiguration, type ChartTypeRegistry } from 'chart.js/auto'

export function useChart(
  id: string,
  getData: () => ChartConfiguration['data'] | ChartConfiguration['data'],
  options: { type?: keyof ChartTypeRegistry; extra?: any } = {}
) {
  const canvas = ref<HTMLCanvasElement | null>(null)
  let chart: Chart | null = null

  function render() {
    if (!canvas.value) return
    const ctx = canvas.value.getContext('2d')
    if (!ctx) return
    const data = typeof getData === 'function' ? getData() : getData
    if (chart) chart.destroy()
    chart = new Chart(ctx, {
      type: options.type || 'bar',
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#aaa' } },
        },
        scales: {
          x: { ticks: { color: '#aaa' }, grid: { color: '#333' } },
          y: { ticks: { color: '#aaa' }, grid: { color: '#333' } },
        },
        ...options.extra,
      },
    })
  }

  onMounted(() => render())
  watch(() => (typeof getData === 'function' ? getData() : getData), () => render(), { deep: true })

  return { canvas, render }
}
