<template>
  <nav class="tabs" aria-label="Navigazione principale">
    <button class="tab" :class="{ active: active === 'rides' }" @click="$emit('update:active', 'rides')">🏍️ <span>Rides</span></button>
    <button class="tab" :class="{ active: active === 'import' }" @click="$emit('update:active', 'import')">📥 <span>Import</span></button>
    <button class="tab" :class="{ active: active === 'athlete' }" @click="$emit('update:active', 'athlete')">🏃 <span>Atleta</span></button>
    <button class="tab" :class="{ active: active === 'coach' }" @click="$emit('update:active', 'coach')">🧠 <span>AI Coach</span></button>
    <button class="tab" :class="{ active: active === 'knowledge' }" @click="$emit('update:active', 'knowledge')">📚 <span>Knowledge</span></button>
    <button class="tab" :class="{ active: active === 'calendar' }" @click="$emit('update:active', 'calendar')">📅 <span>Calendario</span></button>
    <button class="tab" :class="{ active: active === 'granfondo' }" @click="$emit('update:active', 'granfondo')">🚴‍♂️ <span>Granfondo</span></button>
    <button class="tab" :class="{ active: active === 'map' }" @click="$emit('update:active', 'map')"><span>Mappe</span></button>
    <button class="tab" :class="{ active: active === 'heatmap' }" @click="$emit('update:active', 'heatmap')">🔥 <span>Heatmap</span></button>
    <button class="tab" :class="{ active: active === 'badges' }" @click="$emit('update:active', 'badges')">🏅 <span>Badge</span></button>
    <button class="tab" :class="{ active: active === 'weather' }" @click="$emit('update:active', 'weather')">🌤️ <span>Meteo</span></button>
    <button v-if="isAdmin" class="tab" :class="{ active: active === 'admin' }" @click="$emit('update:active', 'admin')">⚙️ <span>Admin</span></button>
    <span class="user-info">{{ isAdmin ? '👑 Admin' : '👤 User' }}</span>
    <button class="tab logout-btn" @click="$emit('logout')">🚪 <span>Esci</span></button>
  </nav>
</template>

<script setup>
defineProps({
  active: { type: String, default: 'rides' },
  isAdmin: { type: Boolean, default: false },
})
</script>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  margin: 20px 0 25px;
  flex-wrap: wrap;
  align-items: center;
}

.tab {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  padding: 10px 18px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 42px;
}

.tab span {
  white-space: nowrap;
}

.tab.active {
  background: var(--accent);
  color: var(--bg-primary);
  font-weight: bold;
  transform: translateY(-1px);
}

.tab:hover:not(.active) {
  border-color: var(--accent);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.user-info {
  padding: 0 12px;
  font-size: 13px;
  color: #aaa;
  display: flex;
  align-items: center;
  margin-left: auto;
}

.logout-btn {
  background: #c0392b;
  border-color: #c0392b;
}

.logout-btn:hover {
  background: #a93226;
}

@media (max-width: 768px) {
  .tabs {
    gap: 6px;
    margin: 12px 0 18px;
  }

  .tab {
    padding: 8px 12px;
    font-size: 0.85rem;
  }

  .user-info {
    width: 100%;
    justify-content: center;
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .tab {
    padding: 6px 10px;
    font-size: 0.78rem;
  }

  .tab span {
    display: none;
  }
}
</style>
