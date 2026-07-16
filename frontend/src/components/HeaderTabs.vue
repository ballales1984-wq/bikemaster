<template>
  <nav class="tabs" aria-label="Main navigation">
    <router-link to="/rides" class="tab" active-class="active">
      🏍️ <span>{{ t("nav.rides") }}</span>
    </router-link>
    <router-link to="/dashboard" class="tab" active-class="active">
      📊 <span>{{ t("nav.dashboard") }}</span>
    </router-link>
    <router-link to="/track" class="tab" active-class="active">
      📍 <span>{{ t("nav.tracking") }}</span>
    </router-link>
    <router-link to="/import" class="tab" active-class="active">
      📥 <span>{{ t("nav.import") }}</span>
    </router-link>
    <router-link to="/athlete" class="tab" active-class="active">
      🏃 <span>{{ t("nav.athlete") }}</span>
    </router-link>
    <router-link to="/coach" class="tab" active-class="active">
      🧠 <span>{{ t("nav.coach") }}</span>
    </router-link>
    <router-link to="/knowledge" class="tab" active-class="active">
      📚 <span>{{ t("nav.knowledge") }}</span>
    </router-link>
    <router-link to="/bm2" class="tab" active-class="active">
      🧮 <span>{{ t("nav.bm2") }}</span>
    </router-link>
    <router-link to="/calendar" class="tab" active-class="active">
      📅 <span>{{ t("nav.calendar") }}</span>
    </router-link>
    <router-link to="/granfondo" class="tab" active-class="active">
      🚴‍♂️ <span>{{ t("nav.granfondo") }}</span>
    </router-link>
    <router-link to="/map" class="tab" active-class="active">
      🗺️ <span>{{ t("nav.maps") }}</span>
    </router-link>
    <router-link to="/aethermap" class="tab" active-class="active">
      🌐 <span>{{ t("nav.aethermap") }}</span>
    </router-link>
    <router-link to="/pois" class="tab" active-class="active">
      📍 <span>{{ t("nav.pois") }}</span>
    </router-link>
    <router-link to="/heatmap" class="tab" active-class="active">
      🔥 <span>{{ t("nav.heatmap") }}</span>
    </router-link>
    <router-link to="/badges" class="tab" active-class="active">
      🏅 <span>{{ t("nav.badges") }}</span>
    </router-link>
    <router-link to="/comparison" class="tab" active-class="active">
      ⚖️ <span>{{ t("nav.comparison") }}</span>
    </router-link>
    <router-link to="/weather" class="tab" active-class="active">
      🌤️ <span>{{ t("nav.weather") }}</span>
    </router-link>
    <router-link v-if="isAdmin" to="/admin" class="tab" active-class="active">
      ⚙️ <span>{{ t("nav.admin") }}</span>
    </router-link>
    <router-link to="/settings" class="tab" active-class="active">
      🛠️ <span>{{ t("nav.settings") }}</span>
    </router-link>

    <button
      class="tab logout-btn"
      :aria-label="t('nav.logout')"
      @click="$emit('logout')"
    >
      <span>{{ t("nav.logout") }}</span>
    </button>
  </nav>
</template>

<script setup>
import { useI18n } from "../composables/useI18n";

const { t } = useI18n();

defineProps({
  isAdmin: { type: Boolean, default: false },
});
</script>

<style scoped>
.tabs {
  position: relative;
  display: flex;
  gap: 8px;
  margin: 20px 0 25px;
  flex-wrap: wrap;
  align-items: center;
  padding-bottom: 6px;
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
  color: var(--text-primary);
  font-weight: bold;
  position: relative;
}

.tab.active::after {
  content: "";
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
  background: var(--color-alert-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-color: var(--color-alert-border);
  flex-shrink: 0;
  position: relative;
}

.logout-btn::before {
  content: "🚪";
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

  .logout-btn span {
    display: none;
  }

  .logout-btn {
    min-width: 42px;
  }
}
</style>
