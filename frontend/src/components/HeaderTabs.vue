<!-- Barra di navigazione a tab: lista di link router alle sezioni principali con frecce di scorrimento orizzontale.
     Props: isAdmin, isClient (mostrano tab Admin/Client). Eventi: logout. Tab admin/client/settings/connection aggiunti
     in base ai ruoli; la tab attiva viene mantenuta visibile (scrollIntoView) e le frecce compaiono al bisogno. -->
<template>
  <div class="tabs-wrap">
    <button
      v-show="canScrollLeft"
      class="tab-arrow tab-arrow-left"
      :aria-label="t('nav.scrollLeft')"
      @click="scrollBy(-200)"
    >
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <polyline points="15 18 9 12 15 6" />
      </svg>
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
        <span class="tab-icon" aria-hidden="true">
          <svg
            v-if="tab.icon === 'bike'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="5.5" cy="17.5" r="3.5" />
            <circle cx="18.5" cy="17.5" r="3.5" />
            <path
              d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h3"
            />
          </svg>
          <svg
            v-else-if="tab.icon === 'chart'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M3 3v18h18" />
            <path d="M7 16l4-4 4 4 6-6" />
          </svg>
          <svg
            v-else-if="tab.icon === 'pin'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <svg
            v-else-if="tab.icon === 'heart'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7Z"
            />
          </svg>
          <svg
            v-else-if="tab.icon === 'download'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <svg
            v-else-if="tab.icon === 'user'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <svg
            v-else-if="tab.icon === 'id-card'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <circle cx="8" cy="10" r="1.5" fill="currentColor" />
            <path d="M14 9h4" />
            <path d="M14 13h2" />
            <path d="M14 17h4" />
          </svg>
          <svg
            v-else-if="tab.icon === 'brain'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M9.5 18A2.5 2.5 0 0 1 7 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z"
            />
            <path
              d="M14.5 18A2.5 2.5 0 0 1 12 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z"
            />
            <path
              d="M17.5 9.5A2.5 2.5 0 0 1 20 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z"
            />
            <path
              d="M6.5 9.5A2.5 2.5 0 0 1 9 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z"
            />
          </svg>
          <svg
            v-else-if="tab.icon === 'books'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a2.5 2.5 0 0 1 0-5H20"
            />
            <path d="M6.5 2H20" />
          </svg>
          <svg
            v-else-if="tab.icon === 'zap'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <svg
            v-else-if="tab.icon === 'calendar'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <svg
            v-else-if="tab.icon === 'flag'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"
            />
            <line x1="4" y1="22" x2="4" y2="15" />
          </svg>
          <svg
            v-else-if="tab.icon === 'map-world'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
            <path d="M2 12h20" />
          </svg>
          <svg
            v-else-if="tab.icon === 'compass'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polygon
              points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"
            />
          </svg>
          <svg
            v-else-if="tab.icon === 'globe'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
            <path d="M2 12h20" />
          </svg>
          <svg
            v-else-if="tab.icon === 'map-pin'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <svg
            v-else-if="tab.icon === 'fire'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"
            />
          </svg>
          <svg
            v-else-if="tab.icon === 'trophy'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 9H4a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h2" />
            <path d="M18 9h2a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-2" />
            <path d="M4 15h16" />
            <path d="M6 15v4" />
            <path d="M18 15v4" />
            <path d="M8 21h8" />
            <path d="M12 15v6" />
          </svg>
          <svg
            v-else-if="tab.icon === 'flask'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M10 2v7.527a2 2 0 0 1-.211.896L4.5 20.5h15l-5.316-10.326A2 2 0 0 1 14 9.527V2"
            />
            <path d="M8.5 2h7" />
          </svg>
          <svg
            v-else-if="tab.icon === 'trending-up'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
            <polyline points="16 7 22 7 22 13" />
          </svg>
          <svg
            v-else-if="tab.icon === 'scale'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
            <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
            <path d="M7 21h10" />
            <path d="M12 3v18" />
            <path d="M3 7h2v2H3z" />
            <path d="M19 7h2v2h-2z" />
          </svg>
          <svg
            v-else-if="tab.icon === 'cloud-sun'"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 2v2" />
            <path d="m4.93 4.93 1.41 1.41" />
            <path d="M20 12h2" />
            <path d="m19.07 4.93-1.41 1.41" />
            <path d="M15.947 12.65a4 4 0 0 0-5.925-4.128" />
            <path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z" />
          </svg>
          <svg
            v-else
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="1" />
          </svg>
        </span>
        <span>{{ t(tab.label) }}</span>
      </router-link>
      <router-link
        v-if="isAdmin"
        ref="tabEls"
        to="/admin"
        class="tab"
        active-class="active"
      >
        <span>{{ t("nav.admin") }}</span>
      </router-link>
      <router-link
        v-if="isAdmin"
        ref="tabEls"
        to="/admin/bm2"
        class="tab"
        active-class="active"
      >
        <span>BM2 Admin</span>
      </router-link>
      <router-link
        v-if="isAdmin"
        ref="tabEls"
        to="/monitoring"
        class="tab"
        active-class="active"
      >
        <span>{{ t("nav.monitoring") }}</span>
      </router-link>
      <router-link
        v-if="isClient"
        ref="tabEls"
        to="/client"
        class="tab"
        active-class="active"
      >
        <span>{{ t("nav.client") }}</span>
      </router-link>
      <router-link
        ref="tabEls"
        to="/settings"
        class="tab"
        active-class="active"
      >
        <span>{{ t("nav.settings") }}</span>
      </router-link>
      <router-link
        ref="tabEls"
        to="/settings/connections"
        class="tab"
        active-class="active"
      >
        <span>{{ t("nav.connections") }}</span>
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
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "../composables/useI18n";

const { t } = useI18n();
const route = useRoute();

defineProps({
  isAdmin: { type: Boolean, default: false },
  isClient: { type: Boolean, default: false },
});

defineEmits(["logout"]);

const tabEls = ref([]);

const tabs = [
  { to: "/rides", label: "nav.rides", icon: "bike" },
  { to: "/dashboard", label: "nav.dashboard", icon: "chart" },
  { to: "/track", label: "nav.tracking", icon: "pin" },
  { to: "/hr24h", label: "nav.heartRate24h", icon: "heart" },
  { to: "/import", label: "nav.import", icon: "download" },
  { to: "/athlete", label: "nav.athlete", icon: "user" },
  { to: "/avatar", label: "nav.avatar", icon: "id-card" },
  { to: "/coach", label: "nav.coach", icon: "brain" },
  { to: "/knowledge", label: "nav.knowledge", icon: "books" },
  { to: "/bm2", label: "nav.bm2", icon: "zap" },
  { to: "/calendar", label: "nav.calendar", icon: "calendar" },
  { to: "/granfondo", label: "nav.granfondo", icon: "flag" },
  { to: "/map", label: "nav.maps", icon: "map-world" },
  { to: "/itinerary", label: "nav.itinerary", icon: "compass" },
  { to: "/aethermap", label: "nav.aethermap", icon: "globe" },
  { to: "/pois", label: "nav.pois", icon: "map-pin" },
  { to: "/heatmap", label: "nav.heatmap", icon: "fire" },
  { to: "/badges", label: "nav.badges", icon: "trophy" },
  { to: "/metabolism", label: "nav.metabolism.title", icon: "flask" },
  { to: "/performance", label: "nav.performance", icon: "trending-up" },
  { to: "/comparison", label: "nav.comparison", icon: "scale" },
  { to: "/weather", label: "nav.weather", icon: "cloud-sun" },
];

const tabsRef = ref<HTMLElement | null>(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);
let layoutRaf: number | null = null;

function updateArrows() {
  const el = tabsRef.value;
  if (!el) return;
  canScrollLeft.value = el.scrollLeft > 4;
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4;
}

function scheduleLayoutUpdate() {
  if (layoutRaf) return;
  layoutRaf = requestAnimationFrame(() => {
    layoutRaf = null;
    updateArrows();
  });
}

function onScroll() {
  scheduleLayoutUpdate();
}

function scrollBy(px: number) {
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
  const active = el.querySelector<HTMLElement>(".tab.active");
  if (active) {
    const activeEl = active as HTMLElement;
    const left =
      activeEl.offsetLeft - el.clientWidth / 2 + activeEl.clientWidth / 2;
    el.scrollTo({ left, behavior: "smooth" });
  }
  scheduleLayoutUpdate();
}

let resizeTimer: ReturnType<typeof setTimeout> | null = null;
function onResize() {
  if (resizeTimer) clearTimeout(resizeTimer!);
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
  if (resizeTimer) clearTimeout(resizeTimer!);
  if (layoutRaf) {
    cancelAnimationFrame(layoutRaf);
    layoutRaf = null;
  }
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

.tab-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tab-icon svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
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
  width: 40px;
  height: 44px;
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
  content: "";
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
    width: 40px;
    height: 44px;
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
