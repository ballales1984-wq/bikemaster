<template>
  <nav class="tabs" aria-label="Navigazione principale">
    <button class="tab" :class="{ active: active === 'rides' }" @click="$emit('update:active', 'rides')">🏍️ Rides</button>
    <button class="tab" :class="{ active: active === 'import' }" @click="$emit('update:active', 'import')">📥 Import</button>
    <button class="tab" :class="{ active: active === 'athlete' }" @click="$emit('update:active', 'athlete')">🏃 Atleta</button>
    <button class="tab" :class="{ active: active === 'coach' }" @click="$emit('update:active', 'coach')">🧠 AI Coach</button>
    <button class="tab" :class="{ active: active === 'knowledge' }" @click="$emit('update:active', 'knowledge')">📚 Knowledge</button>
    <button class="tab" :class="{ active: active === 'calendar' }" @click="$emit('update:active', 'calendar')">📅 Calendario</button>
    <button class="tab" :class="{ active: active === 'granfondo' }" @click="$emit('update:active', 'granfondo')">🚴‍♂️ Granfondo</button>
    <button class="tab" :class="{ active: active === 'heatmap' }" @click="$emit('update:active', 'heatmap')">🔥 Heatmap</button>
    <button class="tab" :class="{ active: active === 'badges' }" @click="$emit('update:active', 'badges')">🏅 Badge</button>
    <button class="tab" :class="{ active: active === 'admin' }" @click="$emit('update:active', 'admin')">⚙️ Admin</button>
  </nav>
</template>

<script setup>
defineProps({ active: { type: String, default: 'rides' } })
</script>