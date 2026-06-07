<template>
  <div id="toast-container" role="status" aria-live="polite" aria-atomic="true" class="toast-root">
    <div
      v-for="t in items"
      :key="t.id"
      class="toast"
      :class="t.type"
    >{{ t.message }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const items = ref([])
let nextId = 1

function add(message, type = 'info', ms = 3000) {
  const id = nextId++
  items.value.push({ id, message, type })
  setTimeout(() => remove(id), ms)
}

function remove(id) {
  items.value = items.value.filter(t => t.id !== id)
}

defineExpose({ add })
</script>
