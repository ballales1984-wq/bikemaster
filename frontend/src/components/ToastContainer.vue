<template>
  <div id="toast-container" role="status" aria-live="polite" aria-atomic="true" class="toast-root">
    <div
      v-for="t in items"
      :key="t.id"
      class="toast"
      :class="[t.type, { exiting: t.exiting }]"
    >
      <span class="toast-icon">{{ toastIcon(t.type) }}</span>
      <span class="toast-content">{{ t.message }}</span>
      <button class="toast-close" @click="remove(t.id)" aria-label="Close">✕</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const items = ref([])
let nextId = 1

function add(message, type = 'info', ms = 3000) {
  const id = nextId++
  items.value.push({ id, message, type, exiting: false })
  setTimeout(() => removeWithAnimation(id), ms)
}

function toastIcon(type) {
  const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' }
  return icons[type] || icons.info
}

function remove(id) {
  items.value = items.value.filter(t => t.id !== id)
}

function removeWithAnimation(id) {
  const toast = items.value.find(t => t.id === id)
  if (toast) {
    toast.exiting = true
    setTimeout(() => remove(id), 300)
  }
}

onMounted(() => {
  window.__toast = { add, remove }
})

defineExpose({ add, remove })
</script>

<style scoped>
.toast-root {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 14px 20px;
  border-radius: var(--radius-sm);
  border-left: 4px solid var(--accent);
  box-shadow: var(--shadow-sm);
  animation: slideIn 0.3s ease;
  max-width: 380px;
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  backdrop-filter: blur(var(--glass-blur));
}

.toast.exiting {
  animation: slideOut 0.3s ease forwards;
}

.toast-icon {
  font-size: 1rem;
  font-weight: bold;
}

.toast-content {
  flex: 1;
  font-size: 0.9rem;
}

.toast-close {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1rem;
  padding: 0 4px;
  line-height: 1;
}

.toast-close:hover {
  color: var(--text-primary);
}

.toast.success { border-left-color: var(--success); }
.toast.success .toast-icon { color: var(--success); }
.toast.error { border-left-color: var(--error); }
.toast.error .toast-icon { color: var(--error); }
.toast.warning { border-left-color: var(--warning); }
.toast.warning .toast-icon { color: var(--warning); }
.toast.info { border-left-color: var(--accent); }
.toast.info .toast-icon { color: var(--accent); }

@keyframes slideIn {
  from { transform: translateX(380px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOut {
  from { transform: translateX(0); opacity: 1; }
  to { transform: translateX(380px); opacity: 0; }
}
</style>
