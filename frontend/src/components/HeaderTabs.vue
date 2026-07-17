<template>
  <div class="tabs-wrap">
    <button
      v-show="canScrollLeft"
      class="tab-arrow tab-arrow-left"
      :aria-label="t('nav.scrollLeft')"
      @click="scrollBy(-200)"
    >
      ‹
    </button>

    <nav
      ref="tabsRef"
      class="tabs"
      aria-label="Main navigation"
      @scroll="onScroll"
    >
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        ref="tabEls"
        :to="tab.to"
        class="tab"
        active-class="active"
      >
        {{ tab.icon }} <span>{{ t(tab.label) }}</span>
      </router-link>
      <router-link
        v-if="isAdmin"
        ref="tabEls"
        to="/admin"
        class="tab"
        active-class="active"
      >
        ⚙️ <span>{{ t("nav.admin") }}</span>
      </router-link>
      <router-link
        v-if="isClient"
        ref="tabEls"
        to="/client"
        class="tab"
        active-class="active"
      >
        👥 <span>{{ t("nav.client") }}</span>
      </router-link>
      <router-link
        ref="tabEls"
        to="/settings"
        class="tab"
        active-class="active"
      >
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

    <button
      v-show="canScrollRight"
      class="tab-arrow tab-arrow-right"
      :aria-label="t('nav.scrollRight')"
      @click="scrollBy(200)"
    >
      ›
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "../composables/useI18n";

const { t } = useI18n();
const route = useRoute();

defineProps({
  isAdmin: { type: Boolean, default: false },
  isClient: { type: Boolean, default: false },
});

const tabEls = ref([]);

const tabs = [
  { to: "/rides", label: "nav.rides", icon: "🏍️" },
  { to: "/dashboard", label: "nav.dashboard", icon: "📊" },
  { to: "/track", label: "nav.tracking", icon: "📍" },
  { to: "/import", label: "nav.import", icon: "📥" },
  { to: "/athlete", label: "nav.athlete", icon: "🏃" },
  { to: "/coach", label: "nav.coach", icon: "🧠" },
  { to: "/knowledge", label: "nav.knowledge", icon: "📚" },
  { to: "/bm2", label: "nav.bm2", icon: "🧮" },
  { to: "/calendar", label: "nav.calendar", icon: "📅" },
  { to: "/granfondo", label: "nav.granfondo", icon: "🚴‍♂️" },
  { to: "/map", label: "nav.maps", icon: "🗺️" },
  { to: "/aethermap", label: "nav.aethermap", icon: "🌐" },
  { to: "/pois", label: "nav.pois", icon: "📍" },
  { to: "/heatmap", label: "nav.heatmap", icon: "🔥" },
  { to: "/badges", label: "nav.badges", icon: "🏅" },
  { to: "/comparison", label: "nav.comparison", icon: "⚖️" },
  { to: "/weather", label: "nav.weather", icon: "🌤️" },
];

const tabsRef = ref(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);

function updateArrows() {
  const el = tabsRef.value;
  if (!el) return;
  canScrollLeft.value = el.scrollLeft > 4;
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4;
}

function onScroll() {
  updateArrows();
}

function scrollBy(px) {
  const el = tabsRef.value;
  if (!el) return;
  if (typeof el.scrollBy === "function") {
    el.scrollBy({ left: px, behavior: "smooth" });
  } else {
    el.scrollLeft += px;
  }
}

function scrollActiveIntoView() {
  const el = tabsRef.value;
  if (!el || typeof el.scrollTo !== "function") return;
  const active = el.querySelector(".tab.active");
  if (active) {
    const left =
      active.offsetLeft - el.clientWidth / 2 + active.clientWidth / 2;
    el.scrollTo({ left, behavior: "smooth" });
  }
  updateArrows();
}

let resizeTimer;
function onResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    updateArrows();
    scrollActiveIntoView();
  }, 150);
}

onMounted(() => {
  nextTick(() => {
    updateArrows();
    scrollActiveIntoView();
  });
  window.addEventListener("resize", onResize);
});

watch(
  () => route.path,
  () => {
    nextTick(scrollActiveIntoView);
  },
);

onUnmounted(() => {
  window.removeEventListener("resize", onResize);
  clearTimeout(resizeTimer);
});
</script>

<style scoped>
.tabs-wrap {
  position: relative;
  display: flex;
  align-items: center;
  margin: 20px 0 25px;
}

.tabs {
  position: relative;
  display: flex;
  gap: 8px;
  flex: 1;
  flex-wrap: nowrap;
  align-items: center;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 6px 6px;
  scrollbar-width: none;
  -ms-overflow-style: none;
  scroll-behavior: smooth;
  -webkit-mask-image: linear-gradient(
    to right,
    transparent,
    #000 24px,
    #000 calc(100% - 24px),
    transparent
  );
  mask-image: linear-gradient(
    to right,
    transparent,
    #000 24px,
    #000 calc(100% - 24px),
    transparent
  );
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
  transition: all 0.25s var(--ease-out-quint);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 42px;
  text-decoration: none;
  flex-shrink: 0;
  position: relative;
}

.tab span {
  white-space: nowrap;
}

.tab:hover {
  background: rgba(0, 255, 204, 0.06);
  border-color: rgba(0, 255, 204, 0.2);
  color: var(--text-primary);
  transform: translateY(-2px);
  box-shadow: var(--glow-soft);
}

.tab.active {
  background: var(--accent-gradient);
  color: #000;
  font-weight: bold;
  position: relative;
  box-shadow: var(--glow-accent), var(--glow-inset);
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
  box-shadow: var(--glow-soft);
  animation: pulseGlow 2s ease-in-out infinite;
}

@keyframes pulseGlow {
  0%,
  100% {
    box-shadow: 0 0 4px rgba(0, 255, 204, 0.3);
  }
  50% {
    box-shadow: 0 0 16px rgba(0, 255, 204, 0.5);
  }
}

.tab-arrow {
  flex-shrink: 0;
  width: 36px;
  height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  color: var(--text-secondary);
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 3;
}

.tab-arrow:hover {
  color: var(--text-primary);
  border-color: var(--accent);
  box-shadow: var(--glow-soft);
}

.tab-arrow-left {
  margin-right: 6px;
}
.tab-arrow-right {
  margin-left: 6px;
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
  box-shadow: var(--glow-error);
}

@media (max-width: 768px) {
  .tabs-wrap {
    margin: 12px 0 18px;
  }

  .tabs {
    gap: 6px;
  }

  .tab {
    padding: 8px 12px;
    font-size: 0.85rem;
  }

  .tab-arrow {
    width: 32px;
    height: 38px;
    font-size: 1.2rem;
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
