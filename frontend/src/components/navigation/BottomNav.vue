<template>
  <nav class="bottom-nav" aria-label="Mobile navigation">
    <router-link
      v-for="item in navItems"
      :key="item.to"
      :to="item.to"
      class="bottom-nav-item"
      active-class="active"
    >
      <component :is="item.icon" />
      <span class="bottom-nav-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { h, type VNode } from "vue";

function IconRides(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "20",
      height: "20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("circle", { cx: "5.5", cy: "17.5", r: "3.5" }),
      h("circle", { cx: "18.5", cy: "17.5", r: "3.5" }),
      h("path", {
        d: "M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h3",
      }),
    ],
  );
}

function IconDashboard(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "20",
      height: "20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("rect", { x: "3", y: "3", width: "7", height: "7" }),
      h("rect", { x: "14", y: "3", width: "7", height: "7" }),
      h("rect", { x: "14", y: "14", width: "7", height: "7" }),
      h("rect", { x: "3", y: "14", width: "7", height: "7" }),
    ],
  );
}

function IconCalendar(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "20",
      height: "20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("rect", {
        x: "3",
        y: "4",
        width: "18",
        height: "18",
        rx: "2",
        ry: "2",
      }),
      h("line", { x1: "16", y1: "2", x2: "16", y2: "6" }),
      h("line", { x1: "8", y1: "2", x2: "8", y2: "6" }),
      h("line", { x1: "3", y1: "10", x2: "21", y2: "10" }),
    ],
  );
}

function IconImport(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "20",
      height: "20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }),
      h("polyline", { points: "17 8 12 3 7 8" }),
      h("line", { x1: "12", y1: "3", x2: "12", y2: "15" }),
    ],
  );
}

function IconAthlete(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "20",
      height: "20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" }),
      h("circle", { cx: "12", cy: "7", r: "4" }),
    ],
  );
}

const navItems = [
  { to: "/rides", label: "Uscite", icon: IconRides },
  { to: "/dashboard", label: "Dashboard", icon: IconDashboard },
  { to: "/calendar", label: "Calendario", icon: IconCalendar },
  { to: "/import", label: "Importa", icon: IconImport },
  { to: "/athlete", label: "Profilo", icon: IconAthlete },
];
</script>

<style scoped>
.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: var(--z-header);
  justify-content: space-around;
  align-items: center;
  padding: 0 var(--space-1);
}

.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--text-muted);
  font-size: 0.65rem;
  font-weight: 500;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-xs);
  transition: color var(--transition-fast);
  flex: 1;
  max-width: 80px;
}

.bottom-nav-item:hover {
  color: var(--text-primary);
}

.bottom-nav-item.active {
  color: var(--accent);
}

.bottom-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.bottom-nav-label {
  white-space: nowrap;
  line-height: 1;
}

@media (max-width: 768px) {
  .bottom-nav {
    display: flex;
  }
}
</style>
