<template>
  <div class="panel">
    <h2>🏅 Badge System</h2>

    <div class="form-grid">
      <div class="form-group">
        <label for="badges-athlete-id">Athlete ID</label>
        <input
          id="badges-athlete-id"
          v-model.number="athleteId"
          type="number"
          min="1"
        />
      </div>
      <div class="form-group">
        <button class="btn btn-primary"
@click="loadBadges">
          🔄 Load Badges
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-text">
      <span class="spinner" /> Loading badges...
    </div>

    <div
v-if="!loading && !badgesData" class="empty-state">
      <div class="empty-icon">🏅</div>
      <div class="empty-title">No badges loaded</div>
      <div class="empty-desc">Enter an Athlete ID to view your badges</div>
    </div>

    <div
v-if="badgesData" class="badges-container">
      <div class="badges-stats">
        <div class="stat-card">
          <div class="stat-value">
            {{ badgesData.achieved }}/{{ badgesData.total_badges }}
          </div>
          <div class="stat-label">Badges Unlocked</div>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: completionPercent + '%' }"
          />
        </div>
      </div>

      <div class="badge-categories">
        <div v-for="cat in categories"
:key="cat.key" class="badge-category">
          <h4>{{ cat.label }}</h4>
          <div class="badge-grid">
            <div
              v-for="badge in getBadgesByCategory(cat.key)"
              :key="badge.id"
              class="badge-card"
              :class="{ achieved: badge.achieved }"
            >
              <div class="badge-icon">
                {{ badge.icon }}
              </div>
              <div class="badge-info">
                <strong>{{ badge.name }}</strong>
                <small>{{ badge.description }}</small>
                <div class="badge-progress">
                  <div class="progress-bar-sm">
                    <div
                      class="progress-fill-sm"
                      :style="{ width: badge.progress + '%' }"
                    />
                  </div>
                  <span class="progress-text">{{ Math.round(badge.progress) }}%</span>
                </div>
              </div>
              <div
v-if="badge.achieved" class="badge-check">✓</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { apiGet } from "../utils/api";

const athleteId = ref(null);
const loading = ref(false);
const badgesData = ref(null);

async function loadAthleteId() {
  const data = await apiGet("/api/v1/athletes");
  athleteId.value = data.athletes?.[0]?.id ?? null;
}

const categories = [
  { key: "milestone", label: "🎯 Milestone" },
  { key: "distance", label: "📏 Distance" },
  { key: "elevation", label: "⛰️ Elevation" },
  { key: "speed", label: "⚡ Speed" },
  { key: "consistency", label: "📆 Consistency" },
];

const completionPercent = computed(() => {
  if (!badgesData.value) return 0;
  return (
    (badgesData.value.achieved / badgesData.value.total_badges) *
    100
  ).toFixed(1);
});

async function loadBadges() {
  if (!athleteId.value) return;
  loading.value = true;
  try {
    badgesData.value = await apiGet("/api/v1/badges", {
      athlete_id: athleteId.value,
    });
  } catch (e) {
    console.error("badges error", e);
    badgesData.value = null;
  } finally {
    loading.value = false;
  }
}

function getBadgesByCategory(category) {
  if (!badgesData.value?.badges) return [];
  return badgesData.value.badges.filter((b) => b.category === category);
}

onMounted(() => {
  loadAthleteId().then(loadBadges).catch(console.error);
});
</script>

<style scoped>
.badges-container {
  margin-top: 15px;
}

.badges-stats {
  margin-bottom: 20px;
}

.progress-bar {
  width: 100%;
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-top: 10px;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.badge-categories {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.badge-category h4 {
  color: var(--text-secondary);
  margin-bottom: 10px;
  font-size: 1rem;
}

.badge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.badge-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  transition: all 0.2s;
}

.badge-card.achieved {
  border-color: var(--accent);
  background: rgba(78, 204, 163, 0.1);
}

.badge-icon {
  font-size: 2rem;
}

.badge-info {
  flex: 1;
}

.badge-info strong {
  display: block;
  font-size: 0.95rem;
}

.badge-info small {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.badge-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}

.progress-bar-sm {
  flex: 1;
  height: 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill-sm {
  height: 100%;
  background: var(--accent);
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  min-width: 35px;
  text-align: right;
}

.badge-check {
  color: var(--accent);
  font-weight: bold;
  font-size: 1.2rem;
}
</style>
