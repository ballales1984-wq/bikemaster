<!-- Pannello Avatar Atleta: manichino umano SVG interattivo con aree corporee colorate per categoria,
     affiancato da una card stile giocatore di calcio/videogioco con valori, livelli e statistiche.
     Legge da /api/v1/athletes/me, /api/v1/athlete/state, /api/v1/scores/athlete/:id.
     Props: nessuna. Eventi: nessuno. -->
<template>
  <div class="avatar-panel">
    <div class="avatar-header">
      <h2>Athlete Avatar</h2>
      <div class="avatar-subtitle">
        Visualizza i tuoi dati atletici in tempo reale
      </div>
      <div v-if="loading" class="avatar-loading">
        Caricamento dati atleta...
      </div>
      <div v-if="error" class="avatar-error">
        {{ error }}
      </div>
    </div>

    <div v-if="!loading && !error" class="avatar-content">
      <!-- Manichino umano SVG -->
      <div class="mannequin-section">
        <div class="section-title">Mappa Corporea</div>
        <div class="mannequin-container">
          <svg viewBox="0 0 200 420" class="mannequin-svg">
            <!-- Ombra/base -->
            <ellipse cx="100" cy="405" rx="45" ry="8" fill="rgba(0,0,0,0.3)" />

            <!-- Testa -->
            <g class="body-part" data-category="head">
              <ellipse cx="100" cy="45" rx="28" ry="32" class="body-shape" />
              <circle cx="100" cy="45" r="28" class="body-outline" />
              <!-- Linee del viso -->
              <circle cx="90" cy="40" r="3" class="body-detail" />
              <circle cx="110" cy="40" r="3" class="body-detail" />
              <path
                d="M 92 55 Q 100 62 108 55"
                class="body-detail"
                fill="none"
                stroke-width="2"
              />
            </g>

            <!-- Collo -->
            <g class="body-part" data-category="neck">
              <rect
                x="90"
                y="72"
                width="20"
                height="18"
                rx="6"
                class="body-shape"
              />
            </g>

            <!-- Torace -->
            <g class="body-part" data-category="chest">
              <path
                d="M 60 90 Q 60 85 70 82 L 130 82 Q 140 85 140 90 L 138 145 Q 138 150 133 152 L 67 152 Q 62 150 62 145 Z"
                class="body-shape"
              />
              <path
                d="M 60 90 Q 60 85 70 82 L 130 82 Q 140 85 140 90 L 138 145 Q 138 150 133 152 L 67 152 Q 62 150 62 145 Z"
                class="body-outline"
                fill="none"
              />
              <!-- Linea centrale -->
              <line x1="100" y1="85" x2="100" y2="150" class="body-detail" />
            </g>

            <!-- Addome -->
            <g class="body-part" data-category="core">
              <path
                d="M 67 152 L 133 152 Q 138 155 138 162 L 136 210 Q 136 215 131 217 L 69 217 Q 64 215 64 210 Z"
                class="body-shape"
              />
              <path
                d="M 67 152 L 133 152 Q 138 155 138 162 L 136 210 Q 136 215 131 217 L 69 217 Q 64 215 64 210 Z"
                class="body-outline"
                fill="none"
              />
            </g>

            <!-- Braccia -->
            <g class="body-part" data-category="arms">
              <!-- Braccio sinistro -->
              <path
                d="M 60 90 L 45 95 Q 38 98 35 105 L 25 155 Q 22 162 28 165 L 38 168 Q 42 168 44 163 L 55 115 Q 58 105 62 100"
                class="body-shape"
              />
              <!-- Braccio destro -->
              <path
                d="M 140 90 L 155 95 Q 162 98 165 105 L 175 155 Q 178 162 172 165 L 162 168 Q 158 168 156 163 L 145 115 Q 142 105 138 100"
                class="body-shape"
              />
            </g>

            <!-- Gambe -->
            <g class="body-part" data-category="legs">
              <!-- Gamba sinistra -->
              <path
                d="M 69 217 L 65 280 Q 63 290 65 300 L 70 370 Q 72 380 78 382 L 90 385 Q 95 385 97 380 L 100 290 L 100 217"
                class="body-shape"
              />
              <!-- Gamba destra -->
              <path
                d="M 131 217 L 135 280 Q 137 290 135 300 L 130 370 Q 128 380 122 382 L 110 385 Q 105 385 103 380 L 100 290 L 100 217"
                class="body-shape"
              />
            </g>

            <!-- Indicatori corpo -->
            <g class="body-indicators">
              <circle cx="100" cy="45" r="32" class="indicator-ring" />
              <circle cx="100" cy="120" r="45" class="indicator-ring" />
              <circle cx="100" cy="185" r="35" class="indicator-ring" />
            </g>
          </svg>

          <!-- Tooltip categoria -->
          <div
            v-if="hoveredCategory"
            class="mannequin-tooltip"
            :style="tooltipStyle"
          >
            <div class="tooltip-title">
              {{ categoryLabels[hoveredCategory] }}
            </div>
            <div class="tooltip-value">
              {{ categoryValues[hoveredCategory] }}
            </div>
            <div
              class="tooltip-status"
              :class="categoryStatus[hoveredCategory]"
            >
              {{ categoryStatusLabels[categoryStatus[hoveredCategory]] }}
            </div>
          </div>
        </div>

        <!-- Legenda categorie -->
        <div class="category-legend">
          <div
            v-for="(cat, key) in categoryConfig"
            :key="key"
            class="legend-item"
            @mouseenter="hoveredCategory = key"
            @mouseleave="hoveredCategory = ''"
          >
            <span class="legend-color" :style="{ background: cat.color }" />
            <span class="legend-label">{{ cat.label }}</span>
          </div>
        </div>
      </div>

      <!-- Card stile giocatore -->
      <div class="player-card-section">
        <div class="player-card">
          <!-- Header card -->
          <div class="card-header">
            <div class="player-avatar">
              <span class="avatar-emoji" />
              <div class="avatar-level">
                <span class="level-badge"
                  >Lv.{{ profile?.experience_level || "—" }}</span
                >
              </div>
            </div>
            <div class="player-info">
              <h3 class="player-name">
                {{ profile?.name || "Atleta" }}
              </h3>
              <div class="player-class">
                {{ profile?.experience_level || "Beginner" }}
              </div>
              <div class="player-meta">
                <span class="meta-item">{{ profile?.age }} anni</span>
                <span class="meta-divider">|</span>
                <span class="meta-item">{{ profile?.weight_kg }} kg</span>
                <span class="meta-divider">|</span>
                <span class="meta-item">{{ profile?.height_cm }} cm</span>
                <span class="meta-divider">|</span>
                <span class="meta-item"
                  >Acqua {{ profile?.body_water_percentage }}%</span
                >
                <span class="meta-divider">|</span>
                <span class="meta-item"
                  >Muscoli {{ profile?.muscle_mass_percentage }}%</span
                >
                <span class="meta-divider">|</span>
                <span class="meta-item">BMR {{ profile?.bmr_kcal }} kcal</span>
              </div>
            </div>
          </div>

          <!-- Barra esperienza -->
          <div class="xp-bar-container">
            <div class="xp-label">
              <span>Esperienza</span>
              <span class="xp-value">{{ profile?.years_active }} anni</span>
            </div>
            <div class="xp-bar">
              <div class="xp-fill" :style="{ width: xpPercent + '%' }" />
            </div>
          </div>

          <!-- Statistiche principali -->
          <div class="stats-grid">
            <div
              v-for="stat in primaryStats"
              :key="stat.label"
              class="stat-card"
            >
              <div class="stat-icon">
                {{ stat.icon }}
              </div>
              <div class="stat-content">
                <div class="stat-value" :style="{ color: stat.color }">
                  {{ stat.value }}
                </div>
                <div class="stat-label">
                  {{ stat.label }}
                </div>
              </div>
              <div class="stat-bar">
                <div
                  class="stat-fill"
                  :style="{ width: stat.percent + '%', background: stat.color }"
                />
              </div>
            </div>
          </div>

          <!-- Composizione corporea -->
          <div class="body-section">
            <div class="body-title">Composizione Corporea</div>
            <div class="stats-grid">
              <div
                v-for="stat in bodyStats"
                :key="stat.label"
                class="stat-card"
              >
                <div class="stat-content">
                  <div class="stat-value" :style="{ color: stat.color }">
                    {{ stat.value }}
                  </div>
                  <div class="stat-label">
                    {{ stat.label }}
                  </div>
                </div>
                <div class="stat-bar">
                  <div
                    class="stat-fill"
                    :style="{
                      width: stat.percent + '%',
                      background: stat.color,
                    }"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Attributi secondari -->
          <div class="attributes-section">
            <div class="attributes-title">Attributi</div>
            <div class="attributes-grid">
              <div
                v-for="attr in attributes"
                :key="attr.name"
                class="attribute-item"
              >
                <div class="attr-header">
                  <span class="attr-name">{{ attr.name }}</span>
                  <span class="attr-value">{{ attr.value }}/100</span>
                </div>
                <div class="attr-bar">
                  <div
                    class="attr-fill"
                    :style="{ width: attr.value + '%', background: attr.color }"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Power/Performance stats -->
          <div v-if="profile?.ftp_watts" class="power-section">
            <div class="power-header">
              <span class="power-icon" />
              <span class="power-label">FTP</span>
              <span class="power-value">{{ profile.ftp_watts }} W</span>
            </div>
            <div class="power-bar">
              <div class="power-fill" :style="{ width: ftpPercent + '%' }" />
            </div>
            <div class="power-zones">
              <span
                v-for="zone in powerZones"
                :key="zone.name"
                class="zone-item"
                :class="{ active: zone.active }"
                :style="{ borderColor: zone.color }"
              >
                {{ zone.name }}
              </span>
            </div>
          </div>

          <!-- Fitness State -->
          <div v-if="athleteState" class="fitness-section">
            <div class="fitness-title">Fitness State</div>
            <div class="fitness-grid">
              <div
                v-for="f in fitnessMetrics"
                :key="f.label"
                class="fitness-item"
              >
                <div class="fitness-value">
                  {{ f.value }}
                </div>
                <div class="fitness-label">
                  {{ f.label }}
                </div>
              </div>
            </div>
            <div
              class="risk-badge"
              :class="'risk-' + (athleteState.risk_level || 'ok')"
            >
              {{ (athleteState.risk_level || "ok").toUpperCase() }}
            </div>
          </div>

          <!-- Equipaggiamento & Limitazioni -->
          <div
            v-if="profile?.equipment || profile?.medical_notes"
            class="equipment-section"
          >
            <div class="equipment-title">Equipaggiamento & Limitazioni</div>
            <div class="equipment-grid">
              <div
                v-if="profile?.equipment"
                class="equipment-item"
              >
                <span class="equipment-label">Equipaggiamento</span>
                <span class="equipment-value">{{ profile.equipment }}</span>
              </div>
              <div
                v-if="profile?.medical_notes"
                class="equipment-item"
              >
                <span class="equipment-label">Note mediche</span>
                <span class="equipment-value">{{ profile.medical_notes }}</span>
              </div>
            </div>
          </div>

          <!-- Footer card -->
          <div class="card-footer">
            <div class="footer-stats">
              <div class="footer-stat">
                <span class="footer-value">{{ weeklySessions }}</span>
                <span class="footer-label">Sessioni/sett</span>
              </div>
              <div class="footer-stat">
                <span class="footer-value">{{ monthlyHours }}h</span>
                <span class="footer-label">Ore/mese</span>
              </div>
              <div class="footer-stat">
                <span class="footer-value">{{ annualHours }}h</span>
                <span class="footer-label">Ore/anno</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAthleteStore } from "../stores/athlete";
import { useAthleteStateStore } from "../stores/athleteState";
import { useAuthStore } from "../stores/auth";
import { storeToRefs } from "pinia";
import type { AthleteState } from "../types/athlete_state";

const authStore = useAuthStore();
const auth = useAthleteStore();
const stateStore = useAthleteStateStore();

const { state: athleteStateRaw, error: stateError } = storeToRefs(stateStore);
const { error: authError } = storeToRefs(auth);
const profile = computed(() => auth.profile);

const athleteState = computed<AthleteState | null>(() => athleteStateRaw.value);
const error = computed(() => stateError.value || authError.value);

const hoveredCategory = ref<keyof typeof categoryConfig | "">("");
const loading = ref(true);

// Categorie corporee con colori e configurazione
const categoryConfig = {
  head: { color: "#a855f7", label: "Head / Recovery" },
  neck: { color: "#ec4899", label: "Neck / Tension" },
  chest: { color: "#00ffcc", label: "Chest / Cardio" },
  core: { color: "#ffb800", label: "Core / Stability" },
  arms: { color: "#0088ff", label: "Arms / Strength" },
  legs: { color: "#ff3366", label: "Legs / Power" },
};

const categoryLabels = computed(() => {
  const labels: Record<string, string> = {};
  for (const [key, config] of Object.entries(categoryConfig)) {
    labels[key] = config.label;
  }
  return labels;
});

const categoryStatus = computed(
  (): Record<keyof typeof categoryConfig, "ok" | "warning" | "danger"> => {
    const s = athleteState.value;
    if (!s) {
      return {
        head: "ok",
        neck: "ok",
        chest: "ok",
        core: "ok",
        arms: "ok",
        legs: "ok",
      };
    }
    return {
      head: s.readiness >= 70 ? "ok" : s.readiness >= 40 ? "warning" : "danger",
      neck:
        s.fatigue_score <= 4
          ? "ok"
          : s.fatigue_score <= 7
            ? "warning"
            : "danger",
      chest: s.ctl >= 60 ? "ok" : s.ctl >= 30 ? "warning" : "danger",
      core: s.acwr >= 0.8 && s.acwr <= 1.3
        ? "ok"
        : s.acwr >= 0.5 && s.acwr <= 1.5
          ? "warning"
          : "danger",
      arms: s.atl <= 60 ? "ok" : s.atl <= 85 ? "warning" : "danger",
      legs: s.tsb >= 10 ? "ok" : s.tsb >= -20 ? "warning" : "danger",
    };
  },
);

const categoryStatusLabels = {
  ok: "Ottimo",
  warning: "Attenzione",
  danger: "Rischio",
};

const categoryValues = computed(() => {
  const s = athleteState.value;
  if (!s) {
    return {
      head: "—",
      neck: "—",
      chest: "—",
      core: "—",
      arms: "—",
      legs: "—",
    };
  }
  return {
    head: `${s.readiness}% readiness`,
    neck: `Fatigue ${s.fatigue_score.toFixed(1)}`,
    chest: `CTL ${s.ctl.toFixed(1)}`,
    core: `ACWR ${s.acwr.toFixed(2)}`,
    arms: `ATL ${s.atl.toFixed(1)}`,
    legs: `TSB ${s.tsb.toFixed(1)}`,
  };
});

const tooltipStyle = computed(() => {
  if (!hoveredCategory.value) return {};
  const config =
    categoryConfig[hoveredCategory.value as keyof typeof categoryConfig];
  return {
    borderColor: config?.color || "var(--accent)",
    boxShadow: `0 0 20px ${config?.color || "var(--accent)"}33`,
  };
});

// XP e livelli
const xpPercent = computed(() => {
  const years = profile.value?.years_active || 0;
  return Math.min((years / 20) * 100, 100);
});

const weeklySessions = computed(() => profile.value?.weekly_sessions || 0);
const monthlyHours = computed(() => profile.value?.monthly_hours || 0);
const annualHours = computed(() => profile.value?.annual_hours || 0);

// Statistiche primarie
const primaryStats = computed(() => {
  const s = athleteState.value;
  const ftp = profile.value?.ftp_watts || 0;
  const weight = profile.value?.weight_kg || 70;
  const ftpPerKg = ftp > 0 ? (ftp / weight).toFixed(2) : "0.00";
  const ftpPerKgNum = ftp > 0 ? ftp / weight : 0;

  return [
    {
      label: "Performance",
      value: s?.readiness ? `${s.readiness}%` : "—",
      icon: "",
      color: "#00ffcc",
      percent: s?.readiness || 0,
    },
    {
      label: "FTP",
      value: ftp > 0 ? `${ftp}W` : "—",
      icon: "",
      color: "#ff3366",
      percent: ftp > 0 ? Math.min((ftp / 400) * 100, 100) : 0,
    },
    {
      label: "FTP/kg",
      value: ftpPerKg,
      icon: "",
      color: "#ffb800",
      percent: ftpPerKgNum > 0 ? Math.min((ftpPerKgNum / 6) * 100, 100) : 0,
    },
    {
      label: "Fitness (CTL)",
      value: s?.ctl ? s.ctl.toFixed(1) : "—",
      icon: "",
      color: "#0088ff",
      percent: s?.ctl ? Math.min((s.ctl / 100) * 100, 100) : 0,
    },
  ];
});

const bodyStats = computed(() => {
  const p = profile.value;
  const weight = p?.weight_kg || 70;
  const muscle = p?.muscle_mass_kg || 0;
  const bone = p?.bone_mass_kg || 0;
  const fat = p?.fat_mass_kg || 0;
  const _musclePct = p?.muscle_mass_percentage || 0;
  const waterPct = p?.body_water_percentage || 0;
  const visceral = p?.visceral_fat_level || 0;
  const proteinPct = p?.protein_percentage || 0;

  return [
    {
      label: "Acqua",
      value: `${waterPct.toFixed(1)}%`,
      color: "#00b4d8",
      percent: Math.min(waterPct, 100),
    },
    {
      label: "Muscoli",
      value: `${muscle.toFixed(1)} kg`,
      color: "#e63946",
      percent: Math.min((muscle / 60) * 100, 100),
    },
    {
      label: "Osso",
      value: `${bone.toFixed(1)} kg`,
      color: "#8ecae6",
      percent: Math.min((bone / 6) * 100, 100),
    },
    {
      label: "Grasso",
      value: `${fat.toFixed(1)} kg`,
      color: "#ffb703",
      percent: Math.min((fat / weight) * 100, 100),
    },
    {
      label: "Viscerale",
      value: `${visceral.toFixed(1)}`,
      color: "#fb8500",
      percent: Math.min((visceral / 20) * 100, 100),
    },
    {
      label: "Proteine",
      value: `${proteinPct.toFixed(1)}%`,
      color: "#2a9d8f",
      percent: Math.min(proteinPct, 100),
    },
  ];
});

// FTP percentuale per barra
const ftpPercent = computed(() => {
  const ftp = profile.value?.ftp_watts || 0;
  return Math.min((ftp / 400) * 100, 100);
});

// Zone di potenza
const powerZones = computed(() => {
  const ftp = profile.value?.ftp_watts || 0;
  if (ftp === 0) return [];
  return [
    { name: "Z1", active: false, color: "#6b7280" },
    { name: "Z2", active: false, color: "#22c55e" },
    { name: "Z3", active: false, color: "#ffb800" },
    { name: "Z4", active: true, color: "#ff6b35" },
    { name: "Z5", active: false, color: "#ef4444" },
  ];
});

// Attributi derivati
const attributes = computed(() => {
  const s = athleteState.value;
  const ftp = profile.value?.ftp_watts || 0;
  const _weight = profile.value?.weight_kg || 70;

  return [
    {
      name: "Potenza",
      value: ftp > 0 ? Math.min(Math.round((ftp / 400) * 100), 100) : 0,
      color: "#ff3366",
    },
    {
      name: "Resistenza",
      value: s?.ctl ? Math.min(Math.round(s.ctl), 100) : 0,
      color: "#0088ff",
    },
    {
      name: "Recupero",
      value: s?.readiness ? Math.round(s.readiness) : 0,
      color: "#00ffcc",
    },
    {
      name: "Forza",
      value: s?.atl ? Math.min(Math.round(s.atl), 100) : 0,
      color: "#ffb800",
    },
    {
      name: "Form",
      value: s?.form ? Math.min(Math.round(s.form + 50), 100) : 30,
      color: "#22c55e",
    },
    {
      name: "Stability",
      value:
        s?.acwr && s.acwr > 0
          ? Math.min(Math.round((1 / s.acwr) * 50), 100)
          : 50,
      color: "#a855f7",
    },
  ];
});

// Metriche fitness
const fitnessMetrics = computed(() => {
  const s = athleteState.value;
  if (!s) return [];
  return [
    { label: "Readiness", value: `${s.readiness}%` },
    { label: "Fatigue", value: s.fatigue_score.toFixed(1) },
    { label: "TSB", value: s.tsb.toFixed(1) },
    { label: "ACWR", value: s.acwr.toFixed(2) },
  ];
});

onMounted(async () => {
  if (!authStore.isLoggedIn) {
    loading.value = false;
    return;
  }
  try {
    await auth.fetchProfile();
    await stateStore.fetchState();
  } catch (e) {
    console.error("Failed to load avatar data:", e);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.avatar-panel {
  padding: 4px 0;
}

.avatar-header {
  margin-bottom: 24px;
}

.avatar-header h2 {
  color: var(--accent);
  font-size: 1.4rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-subtitle {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-top: 4px;
}

.avatar-loading {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-top: 8px;
  font-style: italic;
}

.avatar-error {
  color: #ff3366;
  font-size: 0.85rem;
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255, 51, 102, 0.1);
  border: 1px solid rgba(255, 51, 102, 0.3);
  border-radius: var(--radius-xs);
}

.avatar-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

/* Sezione manichino */
.mannequin-section {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  position: relative;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mannequin-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 420px;
}

.mannequin-svg {
  width: 200px;
  height: 420px;
  filter: drop-shadow(0 0 20px rgba(0, 255, 204, 0.15));
  transition: filter 0.3s ease;
}

.mannequin-svg:hover {
  filter: drop-shadow(0 0 30px rgba(0, 255, 204, 0.3));
}

.body-shape {
  fill: var(--bg-tertiary);
  stroke: var(--border);
  stroke-width: 1.5;
  transition: all 0.3s ease;
}

.body-outline {
  fill: none;
  stroke: var(--border-light);
  stroke-width: 2;
  transition: all 0.3s ease;
}

.body-detail {
  stroke: var(--text-muted);
  stroke-width: 1.5;
  opacity: 0.6;
}

.body-part {
  cursor: pointer;
  transition: all 0.3s ease;
}

.body-part:hover .body-shape {
  stroke-width: 3;
  filter: brightness(1.3);
}

.body-part:hover .body-outline {
  stroke-width: 3;
}

/* Indicatori corpo */
.body-indicators {
  pointer-events: none;
}

.indicator-ring {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
  opacity: 0.3;
  stroke-dasharray: 8 4;
  animation: rotateIndicator 20s linear infinite;
}

@keyframes rotateIndicator {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Tooltip */
.mannequin-tooltip {
  position: absolute;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  min-width: 160px;
  pointer-events: none;
  z-index: 10;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tooltip-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.tooltip-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
  margin-bottom: 6px;
}

.tooltip-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.tooltip-status.ok {
  background: rgba(0, 255, 204, 0.15);
  color: #00ffcc;
}

.tooltip-status.warning {
  background: rgba(255, 184, 0, 0.15);
  color: #ffb800;
}

.tooltip-status.danger {
  background: rgba(255, 51, 102, 0.15);
  color: #ff3366;
}

/* Legenda */
.category-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.legend-item:hover {
  border-color: var(--border-light);
  transform: translateY(-1px);
}

.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  white-space: nowrap;
}

/* Card giocatore */
.player-card-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.player-card {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.player-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--accent-gradient);
}

/* Header card */
.card-header {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
}

.player-avatar {
  position: relative;
  width: 70px;
  height: 70px;
  flex-shrink: 0;
}

.avatar-emoji {
  font-size: 3rem;
  line-height: 1;
  display: block;
  text-align: center;
  filter: drop-shadow(0 0 10px rgba(0, 255, 204, 0.4));
}

.avatar-level {
  position: absolute;
  bottom: -4px;
  right: -4px;
  background: var(--accent-gradient);
  color: #000;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  box-shadow: var(--glow-soft);
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
  font-family: "Outfit", sans-serif;
}

.player-class {
  font-size: 0.85rem;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.player-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.meta-item {
  white-space: nowrap;
}

.meta-divider {
  color: var(--border-light);
}

/* XP Bar */
.xp-bar-container {
  margin-bottom: 20px;
}

.xp-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.xp-value {
  font-weight: 600;
  color: var(--accent);
}

.xp-bar {
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.xp-fill {
  height: 100%;
  background: var(--accent-gradient);
  border-radius: 4px;
  transition: width 0.8s ease;
  box-shadow: var(--glow-soft);
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  border-color: var(--border-light);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stat-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: 700;
  font-family: "Outfit", sans-serif;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.stat-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--border);
}

.stat-fill {
  height: 100%;
  border-radius: 0 0 0 var(--radius-sm);
  transition: width 0.8s ease;
}

/* Attributi */
.attributes-section {
  margin-bottom: 20px;
}

.attributes-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.attributes-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attribute-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.attr-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.attr-name {
  color: var(--text-secondary);
  font-weight: 500;
}

.attr-value {
  color: var(--text-primary);
  font-weight: 700;
  font-family: "Outfit", sans-serif;
}

.attr-bar {
  height: 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  overflow: hidden;
}

.attr-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

/* Power section */
.power-section {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 20px;
}

.power-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.power-icon {
  font-size: 1.2rem;
}

.power-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.power-value {
  margin-left: auto;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
}

.power-bar {
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 10px;
}

.power-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ffcc, #0088ff, #ff3366);
  border-radius: 6px;
  transition: width 0.8s ease;
  box-shadow: var(--glow-soft);
}

.power-zones {
  display: flex;
  gap: 6px;
  justify-content: space-between;
}

.zone-item {
  flex: 1;
  text-align: center;
  padding: 4px;
  border-radius: var(--radius-xs);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.zone-item.active {
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border-color: var(--accent);
  box-shadow: var(--glow-soft);
}

/* Fitness section */
.fitness-section {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 20px;
}

.fitness-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.fitness-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.fitness-item {
  text-align: center;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-xs);
}

.fitness-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
}

.fitness-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

/* Equipment section */
.equipment-section {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 20px;
}

.equipment-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.equipment-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.equipment-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.equipment-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.equipment-value {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.4;
  word-break: break-word;
}

/* Risk badge */
.risk-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-align: center;
  width: 100%;
}

.risk-badge.risk-ok {
  background: rgba(0, 255, 204, 0.15);
  color: #00ffcc;
}

.risk-badge.risk-warning {
  background: rgba(255, 184, 0, 0.15);
  color: #ffb800;
}

.risk-badge.risk-high {
  background: rgba(251, 146, 60, 0.15);
  color: #fb923c;
}

.risk-badge.risk-block {
  background: rgba(255, 51, 102, 0.15);
  color: #ff3366;
  animation: pulse 2s infinite;
}

/* Footer */
.card-footer {
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

.footer-stats {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.footer-stat {
  text-align: center;
}

.footer-value {
  display: block;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
}

.footer-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Loading */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  color: var(--text-muted);
}

/* Responsive */
@media (max-width: 1024px) {
  .avatar-content {
    grid-template-columns: 1fr;
  }

  .mannequin-container {
    min-height: 350px;
  }

  .mannequin-svg {
    width: 180px;
    height: 380px;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .footer-stats {
    grid-template-columns: 1fr;
  }

  .player-card {
    padding: 16px;
  }

  .card-header {
    flex-direction: column;
    text-align: center;
  }

  .player-meta {
    justify-content: center;
  }
}
</style>
