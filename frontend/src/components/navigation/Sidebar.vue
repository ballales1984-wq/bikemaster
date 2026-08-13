<!--
BikeMaster Frontend — Sidebar navigation.

Responsibility:
- Collapsible sidebar with icons + labels
- Navigation items for all main routes
- Role-based visibility (admin, client)
- Logout button
- Mobile: hidden on small screens, replaced by bottom nav in AppLayout
-->

<template>
  <aside class="sidebar" :class="{ collapsed }" aria-label="Sidebar navigation">
    <div class="sidebar-header">
      <router-link
        to="/rides"
        class="sidebar-brand"
        aria-label="BikeMaster Home"
      >
        <span class="brand-icon" aria-hidden="true">🚴</span>
        <span v-if="!collapsed" class="brand-text">BikeMaster</span>
      </router-link>
      <button
        class="sidebar-toggle"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="$emit('toggle')"
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
    </div>

    <nav class="sidebar-nav" aria-label="Main">
      <router-link
        v-for="item in mainNav"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        active-class="active"
        :title="collapsed ? item.label : undefined"
      >
        <span class="nav-icon" aria-hidden="true">
          <component :is="item.icon" />
        </span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </router-link>

      <div v-if="isAdmin && !collapsed" class="nav-section">
        <span class="nav-section-title">Amministrazione</span>
        <router-link to="/admin" class="nav-item" active-class="active">
          <span class="nav-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </span>
          <span class="nav-label">Admin</span>
        </router-link>
        <router-link to="/monitoring" class="nav-item" active-class="active">
          <span class="nav-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </span>
          <span class="nav-label">Monitoring</span>
        </router-link>
      </div>

      <div v-if="isClient && !collapsed" class="nav-section">
        <span class="nav-section-title">Area Client</span>
        <router-link to="/client" class="nav-item" active-class="active">
          <span class="nav-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </span>
          <span class="nav-label">Client</span>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <router-link
        to="/settings"
        class="nav-item"
        active-class="active"
        :title="collapsed ? 'Impostazioni' : undefined"
      >
        <span class="nav-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
            />
          </svg>
        </span>
        <span v-if="!collapsed" class="nav-label">Impostazioni</span>
      </router-link>
      <button
        class="nav-item logout-btn"
        :title="collapsed ? 'Logout' : undefined"
        @click="$emit('logout')"
      >
        <span class="nav-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </span>
        <span v-if="!collapsed" class="nav-label">Logout</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import * as SidebarIcons from "./SidebarIcons";

defineProps({
  collapsed: {
    type: Boolean,
    required: true,
  },
  isAdmin: {
    type: Boolean,
    default: false,
  },
  isClient: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["toggle", "logout"]);

const mainNav = [
  { to: "/rides", label: "Uscite", icon: SidebarIcons.IconRides },
  { to: "/dashboard", label: "Dashboard", icon: SidebarIcons.IconDashboard },
  { to: "/calendar", label: "Calendario", icon: SidebarIcons.IconCalendar },
  { to: "/import", label: "Importa", icon: SidebarIcons.IconImport },
  { to: "/track", label: "Tracciamento", icon: SidebarIcons.IconTrack },
  { to: "/hr24h", label: "FC 24h", icon: SidebarIcons.IconHr24h },
  { to: "/athlete", label: "Profilo", icon: SidebarIcons.IconAthlete },
  { to: "/avatar", label: "Avatar", icon: SidebarIcons.IconAvatar },
  { to: "/coach", label: "AI Coach", icon: SidebarIcons.IconCoach },
  { to: "/knowledge", label: "Knowledge", icon: SidebarIcons.IconKnowledge },
  { to: "/bm2", label: "BM2", icon: SidebarIcons.IconBm2 },
  { to: "/performance", label: "Performance", icon: SidebarIcons.IconPerformance },
  { to: "/map", label: "Mappe", icon: SidebarIcons.IconMap },
  { to: "/aethermap", label: "AetherMap", icon: SidebarIcons.IconAetherMap },
  { to: "/pois", label: "POI", icon: SidebarIcons.IconPois },
  { to: "/itinerary", label: "Itinerari", icon: SidebarIcons.IconItinerary },
  { to: "/heatmap", label: "Heatmap", icon: SidebarIcons.IconHeatmap },
  { to: "/metabolism", label: "Metabolismo", icon: SidebarIcons.IconMetabolism },
  { to: "/granfondo", label: "Granfondo", icon: SidebarIcons.IconGranfondo },
  { to: "/zones", label: "Zone", icon: SidebarIcons.IconZones },
  { to: "/weather", label: "Meteo", icon: SidebarIcons.IconWeather },
  { to: "/comparison", label: "Confronti", icon: SidebarIcons.IconComparison },
  { to: "/badges", label: "Badge", icon: SidebarIcons.IconBadges },
];
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  z-index: var(--z-header);
  transition: width var(--transition);
  overflow: hidden;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-2);
  border-bottom: 1px solid var(--border);
  min-height: 64px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--text-primary);
  font-weight: var(--font-weight-bold);
  font-size: 1rem;
  overflow: hidden;
}

.brand-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.brand-text {
  white-space: nowrap;
  opacity: 1;
  transition: opacity var(--transition);
}

.collapsed .brand-text {
  opacity: 0;
  width: 0;
}

.sidebar-toggle {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.collapsed .sidebar-toggle {
  transform: rotate(180deg);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all var(--transition);
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
}

.nav-item.active .nav-icon {
  color: var(--bg-primary);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
}

.nav-label {
  opacity: 1;
  transition: opacity var(--transition);
}

.collapsed .nav-label {
  opacity: 0;
  width: 0;
}

.nav-section {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}

.nav-section-title {
  display: block;
  padding: var(--space-1) var(--space-3);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 600;
}

.sidebar-footer {
  padding: var(--space-2);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logout-btn {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
}

.logout-btn:hover {
  background: rgba(255, 51, 102, 0.1);
  color: var(--accent-secondary);
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
