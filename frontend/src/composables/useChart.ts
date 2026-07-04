import { onMounted, watch, ref } from 'vue'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Chart: any = (await import('chart.js')).default

interface ChartData {
  labels?: (string | number)[]
  datasets?: { label?: string; data: (number | null)[] }[]
}

export function useChart(
  id: string,
  getData: () => ChartData,
  options: { type?: 'bar' | 'line'; extra?: Record<string, unknown> } = {},
) {
  const canvas = ref<HTMLElement | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let chart: any = null

  function render() {
    if (!canvas.value) return
    const ctx = (canvas.value as HTMLCanvasElement).getContext('2d')
    if (!ctx) return
    const data = typeof getData === 'function' ? getData() : getData
    if (chart) chart.destroy()
    chart = new Chart(ctx, {
      type: options.type || 'bar',
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#aaa' } } },
        scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' } } },
        ...(options.extra || {}),
      },
    })
  }

  onMounted(() => render())
  watch(
    () => (typeof getData === 'function' ? getData() : getData),
    () => render(),
    { deep: true },
  )

  return { canvas, render }
}