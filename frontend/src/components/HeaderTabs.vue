<template>
<nav class="tabs" aria-label="Main navigation" ref="tabsRef">
   <router-link to="/rides" class="tab" active-class="active" @touchstart="$router.push('/rides')">🏍️ <span>Rides</span></router-link>
  <router-link to="/track" class="tab" active-class="active" @touchstart="$router.push('/track')">📍 <span>Tracking</span></router-link>
  <router-link to="/import" class="tab" active-class="active" @touchstart="$router.push('/import')">📥 <span>Import</span></router-link>
  <router-link to="/athlete" class="tab" active-class="active" @touchstart="$router.push('/athlete')">🏃 <span>Athlete</span></router-link>
  <router-link to="/coach" class="tab" active-class="active" @touchstart="$router.push('/coach')">🧠 <span>AI Coach</span></router-link>
  <router-link to="/knowledge" class="tab" active-class="active" @touchstart="$router.push('/knowledge')">📚 <span>Knowledge</span></router-link>
  <router-link to="/calendar" class="tab" active-class="active" @touchstart="$router.push('/calendar')">📅 <span>Calendar</span></router-link>
  <router-link to="/granfondo" class="tab" active-class="active" @touchstart="$router.push('/granfondo')">🚴‍♂️ <span>Granfondo</span></router-link>
  <router-link to="/map" class="tab" active-class="active" @touchstart="$router.push('/map')">🗺️ <span>Maps</span></router-link>
  <router-link to="/heatmap" class="tab" active-class="active" @touchstart="$router.push('/heatmap')">🔥 <span>Heatmap</span></router-link>
  <router-link to="/badges" class="tab" active-class="active" @touchstart="$router.push('/badges')">🏅 <span>Badges</span></router-link>
  <router-link to="/comparison" class="tab" active-class="active" @touchstart="$router.push('/comparison')">⚖️ <span>Compare</span></router-link>
  <router-link to="/weather" class="tab" active-class="active" @touchstart="$router.push('/weather')">🌤️ <span>Weather</span></router-link>
  <router-link v-if="isAdmin" to="/admin" class="tab" active-class="active" @touchstart="$router.push('/admin')">⚙️ <span>Admin</span></router-link>
  <span class="user-info">{{ isAdmin ? '👑 Admin' : '👤 User' }}</span>
  <button class="tab logout-btn" @click="$emit('logout')" @touchstart="$emit('logout')">🚪 <span>Logout</span></button>
</nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  isAdmin: { type: Boolean, default: false },
})

const tabsRef = ref(null)

function checkScrollable() {
  if (tabsRef.value) {
    const el = tabsRef.value
    el.classList.toggle('scrollable', el.scrollWidth > el.clientWidth)
  }
}

onMounted(() => {
  checkScrollable()
  window.addEventListener('resize', checkScrollable)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScrollable)
})
</script>

<style scoped>
.tabs {
   position: relative;
   display: flex;
   gap: 8px;
   margin: 20px 0 25px;
   flex-wrap: nowrap;
   align-items: center;
   overflow-x: auto;
   overflow-y: hidden;
   padding-bottom: 6px;
   scrollbar-width: none;
   -ms-overflow-style: none;
  }

  .tabs::after {
   content: '';
   position: absolute;
   right: 0;
   top: 0;
   bottom: 6px;
   width: 20px;
   background: linear-gradient(to right, transparent, var(--bg-primary));
   pointer-events: none;
   opacity: 0;
   transition: opacity 0.2s;
  }

  .tabs.scrollable::after {
   opacity: 1;
  }

.tabs::-webkit-scrollbar {
  display: none;
}

.tab {
   background: var(--bg-secondary);
   backdrop-filter: blur(var(--glass-blur));
   -webkit-backdrop-filter: blur(var(--glass-blur));
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
   flex-shrink: 0;
 }

.tab span {
  white-space: nowrap;
}

.tab.active {
  background: var(--accent-gradient);
  color: #000;
  font-weight: bold;
  position: relative;
}

.tab.active::after {
   content: '';
   position: absolute;
   bottom: -6px;
   left: 50%;
   transform: translateX(-50%);
   width: 30px;
   height: 4px;
   background: var(--accent);
   border-radius: 2px;
 }

 .user-info {
   padding: 0 12px;
   font-size: 13px;
   color: var(--text-muted);
   display: flex;
   align-items: center;
   margin-left: auto;
   flex-shrink: 0;
 }

 .logout-btn {
    background: rgba(255, 51, 102, 0.15);
    backdrop-filter: blur(var(--glass-blur));
    -webkit-backdrop-filter: blur(var(--glass-blur));
    border-color: rgba(255, 51, 102, 0.4);
    flex-shrink: 0;
  }

  .logout-btn:hover {
    background: rgba(255, 51, 102, 0.25);
    border-color: var(--error);
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
  }

  @media (max-width: 480px) {
    .tab {
      padding: 6px 10px;
      font-size: 0.78rem;
    }

    .tab span {
      display: none;
    }

    .logout-btn span {
      display: none;
    }

    .logout-btn::before {
      content: '🚪';
    }

    .logout-btn {
      min-width: 42px;
    }
  }
 </style>
