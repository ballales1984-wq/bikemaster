<template>
<nav class="tabs" aria-label="Main navigation">
     <router-link to="/rides" class="tab" active-class="active">🏍️ <span>Rides</span></router-link>
     <router-link to="/track" class="tab" active-class="active">📍 <span>Tracking</span></router-link>
     <router-link to="/import" class="tab" active-class="active">📥 <span>Import</span></router-link>
     <router-link to="/athlete" class="tab" active-class="active">🏃 <span>Athlete</span></router-link>
     <router-link to="/coach" class="tab" active-class="active">🧠 <span>AI Coach</span></router-link>
     <router-link to="/knowledge" class="tab" active-class="active">📚 <span>Knowledge</span></router-link>
     <router-link to="/calendar" class="tab" active-class="active">📅 <span>Calendar</span></router-link>
     <router-link to="/granfondo" class="tab" active-class="active">🚴‍♂️ <span>Granfondo</span></router-link>
     <router-link to="/map" class="tab" active-class="active"><span>Maps</span></router-link>
     <router-link to="/heatmap" class="tab" active-class="active">🔥 <span>Heatmap</span></router-link>
     <router-link to="/badges" class="tab" active-class="active">🏅 <span>Badges</span></router-link>
     <router-link to="/weather" class="tab" active-class="active">🌤️ <span>Weather</span></router-link>
     <router-link v-if="isAdmin" to="/admin" class="tab" active-class="active">⚙️ <span>Admin</span></router-link>
     <span class="user-info">{{ isAdmin ? '👑 Admin' : '👤 User' }}</span>
     <button class="tab logout-btn" @click="$emit('logout')">🚪 <span>Logout</span></button>
   </nav>
</template>

<script setup>
defineProps({
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
  text-decoration: none;
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
