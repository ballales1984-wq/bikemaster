import { onMounted, watch, ref } from 'vue'

export function useChart(id, getData, options = {}) {
  const canvas = ref(null)
  let chart = null

  function render() {
    if (!canvas.value) return
    const ctx = canvas.value.getContext('2d')
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
