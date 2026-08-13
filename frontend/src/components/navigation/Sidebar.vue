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
      <router-link to="/rides" class="sidebar-brand" aria-label="BikeMaster Home">
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
        <span class="nav-icon" aria-hidden="true" v-html="item.icon"></span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </router-link>

      <div v-if="isAdmin && !collapsed" class="nav-section">
        <span class="nav-section-title">Amministrazione</span>
        <router-link to="/admin" class="nav-item" active-class="active">
          <span class="nav-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </span>
          <span class="nav-label">Admin</span>
        </router-link>
        <router-link to="/monitoring" class="nav-item" active-class="active">
          <span class="nav-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
      <router-link to="/settings" class="nav-item" active-class="active" :title="collapsed ? 'Impostazioni' : undefined">
        <span class="nav-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </span>
        <span v-if="!collapsed" class="nav-label">Impostazioni</span>
      </router-link>
      <button class="nav-item logout-btn" :title="collapsed ? 'Logout' : undefined" @click="$emit('logout')">
        <span class="nav-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
import type { PropType } from "vue";

const props = defineProps({
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
  {
    to: "/rides",
    label: "Uscite",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h3"/></svg>`,
  },
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
  },
  {
    to: "/calendar",
    label: "Calendario",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  },
  {
    to: "/import",
    label: "Importa",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
  },
  {
    to: "/track",
    label: "Tracciamento",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`,
  },
  {
    to: "/hr24h",
    label: "FC 24h",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7Z"/></svg>`,
  },
  {
    to: "/athlete",
    label: "Profilo",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  },
  {
    to: "/avatar",
    label: "Avatar",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><circle cx="8" cy="10" r="1.5" fill="currentColor"/><path d="M14 9h4"/><path d="M14 13h2"/><path d="M14 17h4"/></svg>`,
  },
  {
    to: "/coach",
    label: "AI Coach",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 18A2.5 2.5 0 0 1 7 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z"/><path d="M14.5 18A2.5 2.5 0 0 1 12 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z"/><path d="M17.5 9.5A2.5 2.5 0 0 1 20 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z"/><path d="M6.5 9.5A2.5 2.5 0 0 1 9 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z"/></svg>`,
  },
  {
    to: "/knowledge",
    label: "Knowledge",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>`,
  },
  {
    to: "/bm2",
    label: "BM2",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  },
  {
    to: "/performance",
    label: "Performance",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 6-6"/></svg>`,
  },
  {
    to: "/map",
    label: "Mappe",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 21 18 21 2 16 6 8 2 1 6"/><line x1="16" y1="6" x2="16" y2="22"/><line x1="8" y1="2" x2="8" y2="18"/></svg>`,
  },
  {
    to: "/aethermap",
    label: "AetherMap",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`,
  },
  {
    to: "/pois",
    label: "POI",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`,
  },
  {
    to: "/itinerary",
    label: "Itinerari",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
  },
  {
    to: "/heatmap",
    label: "Heatmap",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>`,
  },
  {
    to: "/metabolism",
    label: "Metabolismo",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7z"/></svg>`,
  },
  {
    to: "/granfondo",
    label: "Granfondo",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>`,
  },
  {
    to: "/zones",
    label: "Zone",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`,
  },
  {
    to: "/weather",
    label: "Meteo",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/></svg>`,
  },
  {
    to: "/comparison",
    label: "Confronti",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2v2H3z"/><path d="M19 7h2v2h-2z"/></svg>`,
  },
  {
    to: "/badges",
    label: "Badge",
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="10.5 21 12 17 13.5 21"/><polyline points="7 12 9 8 11 12"/><polyline points="13 12 15 8 17 12"/></svg>`,
  },
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
