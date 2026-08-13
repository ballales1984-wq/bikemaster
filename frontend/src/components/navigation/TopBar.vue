<!--
BikeMaster Frontend — TopBar.

Responsibility:
- Collapse/expand sidebar trigger
- Breadcrumb / page title
- Theme toggle
- User menu (avatar, name, quick links)
- Mobile hamburger menu
-->

<template>
  <header class="topbar" :class="{ collapsed }">
    <div class="topbar-left">
      <button
        class="topbar-toggle"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="$emit('toggle-sidebar')"
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div class="topbar-breadcrumb">
        <router-link to="/rides" class="breadcrumb-home" aria-label="Home">
          <span class="breadcrumb-icon" aria-hidden="true">🚴</span>
        </router-link>
        <span v-if="currentRouteName" class="breadcrumb-sep" aria-hidden="true">/</span>
        <span v-if="currentRouteName" class="breadcrumb-current">{{ currentRouteName }}</span>
      </div>
    </div>

    <div class="topbar-right">
      <button
        class="theme-toggle"
        :aria-label="ui.isDark ? 'Light mode' : 'Dark mode'"
        @click="ui.toggleTheme"
        title="Toggle theme"
      >
        <svg
          v-if="ui.isDark"
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
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
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
          aria-hidden="true"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </button>

      <div class="user-menu" v-if="auth.user">
        <button class="user-menu-trigger" @click="showUserMenu = !showUserMenu" aria-haspopup="true" :aria-expanded="showUserMenu">
          <span class="user-avatar">{{ userInitials }}</span>
          <span class="user-name">{{ auth.user.name || auth.user.username }}</span>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div v-if="showUserMenu" class="user-menu-dropdown" ref="dropdownRef">
          <div class="user-menu-header">
            <span class="user-avatar-lg">{{ userInitials }}</span>
            <div class="user-info">
              <span class="user-display-name">{{ auth.user.name || auth.user.username }}</span>
              <span class="user-email">{{ auth.user.email || auth.user.username }}</span>
            </div>
          </div>
          <div class="user-menu-divider"></div>
          <router-link to="/athlete" class="user-menu-item" @click="showUserMenu = false">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            Profilo atleta
          </router-link>
          <router-link to="/settings" class="user-menu-item" @click="showUserMenu = false">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            Impostazioni
          </router-link>
          <div class="user-menu-divider"></div>
          <button class="user-menu-item logout" @click="showUserMenu = false; $emit('logout')">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Logout
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useUIStore } from "../../stores/ui";

defineProps({
  collapsed: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["toggle-sidebar", "logout"]);

const auth = useAuthStore();
const ui = useUIStore();
const route = useRoute();
const showUserMenu = ref(false);
const dropdownRef = ref<HTMLElement | null>(null);

const currentRouteName = computed(() => route.meta.title as string | undefined);

const userInitials = computed(() => {
  const name = auth.user?.name || auth.user?.username || "U";
  return name.slice(0, 2).toUpperCase();
});

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    showUserMenu.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-5);
  background: linear-gradient(180deg, rgba(10, 11, 16, 0.6), transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  min-height: 56px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  overflow: hidden;
}

.topbar-toggle {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
  flex-shrink: 0;
}

.topbar-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.topbar-breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  overflow: hidden;
}

.breadcrumb-home {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--transition);
}

.breadcrumb-home:hover {
  color: var(--accent);
}

.breadcrumb-icon {
  font-size: 1.2rem;
}

.breadcrumb-sep {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.breadcrumb-current {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.theme-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}

.theme-toggle:hover {
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(0, 255, 204, 0.2);
}

.user-menu {
  position: relative;
}

.user-menu-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  cursor: pointer;
  font-family: inherit;
  font-size: 0.85rem;
  transition: all var(--transition);
}

.user-menu-trigger:hover {
  border-color: var(--accent);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent-gradient);
  color: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
}

.user-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.user-menu-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 240px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown);
  overflow: hidden;
}

.user-menu-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
}

.user-avatar-lg {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent-gradient);
  color: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 700;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.user-display-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-menu-divider {
  height: 1px;
  background: var(--border);
  margin: var(--space-1) 0;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  transition: all var(--transition);
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.user-menu-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.user-menu-item.logout {
  color: var(--accent-secondary);
}

.user-menu-item.logout:hover {
  background: rgba(255, 51, 102, 0.1);
}

@media (max-width: 768px) {
  .topbar {
    padding: var(--space-2) var(--space-3);
  }

  .user-name {
    display: none;
  }
}
</style>
