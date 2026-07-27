<!--
  Strumenti pagina tracking: toolbar con controlli mappa e azioni itinerario.
  Props: mapStyle, showPois. Eventi: update:mapStyle, update:showPois, save-itinerary, add-stage.
  UI: selettore stile mappa, toggle POI, azioni creazione itinerario dalla traccia corrente.
-->
<template>
  <div class="tracking-tools">
    <div class="tools-group">
      <label class="control">
        <span>{{ t("trackingTools.mapStyle") }}</span>
        <select
          id="tracking-map-style"
          :value="modelValueMapStyle"
          class="form-input"
          @change="onMapStyleChange"
        >
          <option value="osm">{{ t("trackingTools.styleOsm") }}</option>
          <option value="cyclosm">{{ t("trackingTools.styleCyclosm") }}</option>
        </select>
      </label>

      <label class="checkbox-control">
        <input
          id="tracking-show-pois"
          type="checkbox"
          :checked="modelValueShowPois"
          @change="
            $emit(
              'update:showPois',
              ($event.target as HTMLInputElement).checked,
            )
          "
        />
        <span>{{ t("trackingTools.showPois") }}</span>
      </label>

      <button
        class="btn btn-secondary btn-sm"
        :disabled="!hasRoute"
        @click="$emit('center-map')"
      >
        {{ t("trackingTools.centerMap") }}
      </button>
    </div>

    <div class="tools-group">
      <button
        class="btn btn-primary btn-sm"
        :disabled="!canSaveItinerary"
        @click="$emit('save-itinerary')"
      >
        {{ t("trackingTools.saveAsItinerary") }}
      </button>

      <label v-if="itineraries.length" class="control">
        <span>{{ t("trackingTools.addToItinerary") }}</span>
        <select
          id="tracking-itinerary"
          class="form-input"
          :value="selectedItineraryId"
          @change="onItineraryChange"
        >
          <option :value="null">
            {{ t("trackingTools.selectItinerary") }}
          </option>
          <option v-for="it in itineraries" :key="it.id" :value="it.id">
            {{ it.name }}
          </option>
        </select>
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "../composables/useI18n";
import type { Itinerary } from "../types/index";

const { t } = useI18n();

defineProps<{
  modelValueMapStyle: string;
  modelValueShowPois: boolean;
  hasRoute: boolean;
  canSaveItinerary: boolean;
  itineraries: Itinerary[];
  selectedItineraryId: number | null;
}>();

const emit = defineEmits<{
  "update:mapStyle": [value: string];
  "update:showPois": [value: boolean];
  "save-itinerary": [];
  "add-stage": [itineraryId: number];
  "center-map": [];
}>();

function onMapStyleChange(e: Event) {
  emit("update:mapStyle", (e.target as HTMLSelectElement).value);
}

function onItineraryChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value;
  const id = val ? Number(val) : null;
  if (id) {
    emit("add-stage", id);
  }
}
</script>

<style scoped>
.tracking-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 14px;
}

.tools-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
  flex: 1 1 auto;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  min-width: 160px;
}

.checkbox-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
}

.form-input {
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  font: inherit;
}

.btn {
  padding: 9px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  transition: all 0.15s;
}

.btn-primary {
  background: var(--accent-gradient);
  border-color: transparent;
  color: #000;
}

.btn-secondary {
  background: var(--bg-secondary);
  border-color: var(--border);
}

.btn-sm {
  padding: 7px 12px;
  font-size: 0.85rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .tracking-tools {
    gap: 12px;
  }
  .control {
    min-width: 140px;
  }
}
</style>
