<!-- Skeleton loading placeholders for panels and cards.
     Usage: <BmSkeleton type="text" :lines="3" /> or <BmSkeleton type="card" /> -->
<template>
  <div class="skeleton" :class="[type, `size-${size}`]" :style="style" aria-hidden="true">
    <span class="skeleton-shimmer" />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: "text" | "card" | "circle" | "button";
  size?: "sm" | "md" | "lg";
  width?: string | number;
  height?: string | number;
  style?: Record<string, string>;
}>(), {
  type: "text",
  size: "md",
  width: undefined,
  height: undefined,
  style: () => ({}),
});
</script>

<style scoped>
.skeleton {
  position: relative;
  overflow: hidden;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.skeleton-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 50%,
    transparent 100%
  );
  animation: shimmer 1.8s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.size-sm { --skeleton-h: 12px; }
.size-md { --skeleton-h: 16px; }
.size-lg { --skeleton-h: 24px; }

.type-text {
  height: var(--skeleton-h);
  width: 100%;
}

.type-card {
  height: 120px;
  width: 100%;
  border-radius: var(--radius);
}

.type-circle {
  height: var(--skeleton-h);
  width: var(--skeleton-h);
  border-radius: 50%;
}

.type-button {
  height: 40px;
  width: 100%;
  border-radius: var(--radius-sm);
}
</style>
