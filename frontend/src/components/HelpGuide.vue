<!--
  Guida interattiva dell'applicazione: piccoli tag esplicativi per ogni
  sezione, pulsante e azione principale. Apre un pannello slide-in con
  categorie navigabili e tag cliccabili per filtrare la vista.
-->
<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="help-overlay" @click.self="close" />
    </Transition>

    <aside :class="['help-panel', { open }]">
      <div class="help-header">
        <h2>{{ t("help.title") }}</h2>
        <button class="help-close" aria-label="Close" @click="close">✕</button>
      </div>

      <div class="help-categories">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['cat-btn', { active: activeCategory === cat.key }]"
          @click="activeCategory = cat.key"
        >
          {{ cat.icon }} {{ t(cat.label) }}
        </button>
      </div>

      <div class="help-body">
        <div v-if="activeCategory === 'welcome'" class="help-section">
          <h3>{{ t("help.secWelcome") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.welcomeStartTitle") }}</strong>
              <p>{{ t("help.welcomeStartText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.welcomeLoginTitle") }}</strong>
              <p>{{ t("help.welcomeLoginText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.welcomeGoogleTitle") }}</strong>
              <p>{{ t("help.welcomeGoogleText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'navigation'" class="help-section">
          <h3>{{ t("help.secNavigation") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.navRidesTitle") }}</strong>
              <p>{{ t("help.navRidesText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navDashboardTitle") }}</strong>
              <p>{{ t("help.navDashboardText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navTrackingTitle") }}</strong>
              <p>{{ t("help.navTrackingText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navImportTitle") }}</strong>
              <p>{{ t("help.navImportText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navAthleteTitle") }}</strong>
              <p>{{ t("help.navAthleteText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navCoachTitle") }}</strong>
              <p>{{ t("help.navCoachText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navKnowledgeTitle") }}</strong>
              <p>{{ t("help.navKnowledgeText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navBm2Title") }}</strong>
              <p>{{ t("help.navBm2Text") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navCalendarTitle") }}</strong>
              <p>{{ t("help.navCalendarText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navGranfondoTitle") }}</strong>
              <p>{{ t("help.navGranfondoText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navMapsTitle") }}</strong>
              <p>{{ t("help.navMapsText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navAetherMapTitle") }}</strong>
              <p>{{ t("help.navAetherMapText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navPoiTitle") }}</strong>
              <p>{{ t("help.navPoiText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navHeatmapTitle") }}</strong>
              <p>{{ t("help.navHeatmapText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navBadgeTitle") }}</strong>
              <p>{{ t("help.navBadgeText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navCompareTitle") }}</strong>
              <p>{{ t("help.navCompareText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navWeatherTitle") }}</strong>
              <p>{{ t("help.navWeatherText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navSettingsTitle") }}</strong>
              <p>{{ t("help.navSettingsText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navConnectionsTitle") }}</strong>
              <p>{{ t("help.navConnectionsText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.navLogoutTitle") }}</strong>
              <p>{{ t("help.navLogoutText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'tracking'" class="help-section">
          <h3>{{ t("help.secTracking") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.trackTypeTitle") }}</strong>
              <p>{{ t("help.trackTypeText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.trackStartTitle") }}</strong>
              <p>{{ t("help.trackStartText") }}</p>
            </div>
            <div class="help-tag">
              <strong>⏸ {{ t("help.trackPauseTitle") }}</strong>
              <p>{{ t("help.trackPauseText") }}</p>
            </div>
            <div class="help-tag">
              <strong>▶ {{ t("help.trackResumeTitle") }}</strong>
              <p>{{ t("help.trackResumeText") }}</p>
            </div>
            <div class="help-tag">
              <strong>⏹ {{ t("help.trackStopTitle") }}</strong>
              <p>{{ t("help.trackStopText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.trackUploadTitle") }}</strong>
              <p>{{ t("help.trackUploadText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'rides'" class="help-section">
          <h3>{{ t("help.secRides") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.ridesTrackTitle") }}</strong>
              <p>{{ t("help.ridesTrackText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.ridesPlanTitle") }}</strong>
              <p>{{ t("help.ridesPlanText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.ridesCoachTitle") }}</strong>
              <p>{{ t("help.ridesCoachText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.ridesListTitle") }}</strong>
              <p>{{ t("help.ridesListText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'import'" class="help-section">
          <h3>{{ t("help.secImport") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.importFileTitle") }}</strong>
              <p>{{ t("help.importFileText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.importGoogleFitTitle") }}</strong>
              <p>{{ t("help.importGoogleFitText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.importStravaTitle") }}</strong>
              <p>{{ t("help.importStravaText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.importDisconnectTitle") }}</strong>
              <p>{{ t("help.importDisconnectText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'settings'" class="help-section">
          <h3>{{ t("help.secSettings") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.setBackendTitle") }}</strong>
              <p>{{ t("help.setBackendText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setSaveTitle") }}</strong>
              <p>{{ t("help.setSaveText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setFailoverTitle") }}</strong>
              <p>{{ t("help.setFailoverText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setApiTitle") }}</strong>
              <p>{{ t("help.setApiText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setImportKeysTitle") }}</strong>
              <p>{{ t("help.setImportKeysText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setVerifyTitle") }}</strong>
              <p>{{ t("help.setVerifyText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setSyncModeTitle") }}</strong>
              <p>{{ t("help.setSyncModeText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.setExportTitle") }}</strong>
              <p>{{ t("help.setExportText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'athlete'" class="help-section">
          <h3>{{ t("help.secAthlete") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.athNameTitle") }}</strong>
              <p>{{ t("help.athNameText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athBioTitle") }}</strong>
              <p>{{ t("help.athBioText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athFatTitle") }}</strong>
              <p>{{ t("help.athFatText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athYearsTitle") }}</strong>
              <p>{{ t("help.athYearsText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athLevelTitle") }}</strong>
              <p>{{ t("help.athLevelText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athGoalsTitle") }}</strong>
              <p>{{ t("help.athGoalsText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athSaveTitle") }}</strong>
              <p>{{ t("help.athSaveText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.athScoresTitle") }}</strong>
              <p>{{ t("help.athScoresText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'coach'" class="help-section">
          <h3>{{ t("help.secCoach") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.coachChatTitle") }}</strong>
              <p>{{ t("help.coachChatText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.coachReportTitle") }}</strong>
              <p>{{ t("help.coachReportText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.coachClearTitle") }}</strong>
              <p>{{ t("help.coachClearText") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.coachQuickTitle") }}</strong>
              <p>{{ t("help.coachQuickText") }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'zones'" class="help-section">
          <h3>{{ t("help.secZones") }}</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>{{ t("help.zone12Title") }}</strong>
              <p>{{ t("help.zone12Text") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.zone3Title") }}</strong>
              <p>{{ t("help.zone3Text") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.zone4Title") }}</strong>
              <p>{{ t("help.zone4Text") }}</p>
            </div>
            <div class="help-tag">
              <strong>{{ t("help.zone57Title") }}</strong>
              <p>{{ t("help.zone57Text") }}</p>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <button
      v-if="loggedIn"
      class="help-fab"
      :aria-label="open ? t('help.close') : t('help.open')"
      @click="toggle"
    >
      {{ open ? "" : "" }}
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "../composables/useI18n";

const auth = useAuthStore();
const { t } = useI18n();
const open = ref(false);
const activeCategory = ref("navigation");

const categories = [
  { key: "welcome", label: "help.categoryWelcome", icon: "" },
  { key: "navigation", label: "help.categoryNavigation", icon: "" },
  { key: "tracking", label: "help.categoryTracking", icon: "" },
  { key: "rides", label: "help.categoryRides", icon: "" },
  { key: "import", label: "help.categoryImport", icon: "" },
  { key: "settings", label: "help.categorySettings", icon: "" },
  { key: "athlete", label: "help.categoryAthlete", icon: "" },
  { key: "coach", label: "help.categoryCoach", icon: "" },
  { key: "zones", label: "help.categoryZones", icon: "" },
];

const loggedIn = computed(() => auth.isLoggedIn);

function toggle() {
  open.value = !open.value;
}

function close() {
  open.value = false;
}
</script>

<style scoped>
.help-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 998;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.help-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: min(420px, 92vw);
  height: 100vh;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  z-index: 999;
  transform: translateX(100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.3);
}
.help-panel.open {
  transform: translateX(0);
}

.help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.help-header h2 {
  margin: 0;
  font-size: 1.2rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.help-close {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.help-close:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.help-categories {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
  overflow-x: auto;
  border-bottom: 1px solid var(--border);
  scrollbar-width: none;
}
.help-categories::-webkit-scrollbar {
  display: none;
}
.cat-btn {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.cat-btn:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}
.cat-btn.active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
  font-weight: 600;
}

.help-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.help-section h3 {
  margin: 0 0 12px;
  font-size: 1rem;
  color: var(--text-primary);
}
.tag-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.help-tag {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
  transition: border-color 0.2s;
}
.help-tag:hover {
  border-color: rgba(0, 255, 204, 0.25);
}
.help-tag strong {
  display: block;
  font-size: 0.9rem;
  color: var(--accent);
  margin-bottom: 4px;
}
.help-tag p {
  margin: 0;
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.help-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--accent);
  color: #000;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  z-index: 997;
  box-shadow: 0 4px 16px rgba(0, 255, 204, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.help-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(0, 255, 204, 0.5);
}

@media (max-width: 480px) {
  .help-panel {
    width: 100vw;
  }
  .help-fab {
    bottom: 16px;
    right: 16px;
    width: 42px;
    height: 42px;
    font-size: 1.1rem;
  }
}
</style>
