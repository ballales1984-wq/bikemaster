import { onErrorCaptured } from 'vue'

export const ErrorBoundary = {
  name: 'ErrorBoundary',
  data() {
    return {
      error: null,
    }
  },
  mounted() {
    onErrorCaptured((err) => {
      this.error = err instanceof Error ? err.message : String(err)
      return false
    })
  },
  methods: {
    resetError() {
      this.error = null
    },
  },
  render() {
    if (this.error) {
      return [
        h('div', { class: 'error-boundary' }, [
          h('div', { class: 'error-boundary-icon' }, '⚠️'),
          h('h2', { class: 'error-boundary-title' }, 'Something went wrong'),
          h('p', { class: 'error-boundary-message' }, this.error),
          h('button', { class: 'btn btn-primary', onClick: this.resetError }, '🔄 Try Again'),
        ]),
      ]
    }
    return this.$slots.default ? this.$slots.default() : []
  },
}
