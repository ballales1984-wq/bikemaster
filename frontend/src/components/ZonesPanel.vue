<!-- Pannello zone di allenamento: distribuzione % del tempo per zone di potenza (FTP) e zone di frequenza cardiaca.
     Props: nessuna. Eventi: nessuno (usa /api/v1/analytics/zones). Mostra due grafici a barre (Power Zones / HR Zones) con range negli hover.
     UI: sottotitolo con FTP e FC max, griglia di due BaseChart e gestione stato errore; label "vuoto" se mancano power meter/FC. -->
<template>
  <section class="zones-panel">
    <div class="panel">
      <h2>Zone di Allenamento</h2>
      <p class="zones-sub">
        Distribuzione del tempo per zona (FTP {{ data.ftp_watts }}W · FC max
        {{ data.max_hr }}bpm)
      </p>

      <div v-if="error" class="error-state">
        <p>{{ error }}</p>
      </div>

      <div v-else class="zones-grid">
        <div class="zone-card">
          <h3>Power Zones</h3>
          <BaseChart
            :config="powerConfig"
            height="240px"
            :empty-label="powerEmpty"
          />
        </div>
        <div class="zone-card">
          <h3>Heart-Rate Zones</h3>
          <BaseChart :config="hrConfig" height="240px" :empty-label="hrEmpty" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import { apiGet } from "../utils/api";
import BaseChart from "./BaseChart.vue";

interface Zone {
  zone: string;
  label: string;
  lower_w?: number;
  upper_w?: number;
  lower_bpm?: number;
  upper_bpm?: number;
  count: number;
  pct_time: number;
  color: string;
}

interface ZoneGroup {
  available: boolean;
  total_samples: number;
  zones: Zone[];
}

interface ZonesResponse {
  ftp_watts: number;
  max_hr: number;
  rides_with_power: number;
  rides_with_hr: number;
  power: ZoneGroup;
  hr: ZoneGroup;
}

const data = ref<ZonesResponse>({
  ftp_watts: 0,
  max_hr: 0,
  rides_with_power: 0,
  rides_with_hr: 0,
  power: { available: false, total_samples: 0, zones: [] },
  hr: { available: false, total_samples: 0, zones: [] },
});

const loading = ref(false);
const error = ref("");

const powerEmpty = computed(() =>
  data.value.power.available
    ? "Nessun campione power"
    : "Dati power non disponibili (serve un power meter)",
);

const hrEmpty = computed(() =>
  data.value.hr.available
    ? "Nessun campione FC"
    : "Dati frequenza cardiaca non disponibili",
);

function buildConfig(group: ZoneGroup, unit: string): ChartConfiguration {
  return {
    type: "bar",
    data: {
      labels: group.zones.map((z) => `${z.zone} ${z.label}`),
      datasets: [
        {
          label: `% tempo (${unit})`,
          data: group.zones.map((z) => z.pct_time),
          backgroundColor: group.zones.map((z) => z.color),
          borderRadius: 6,
        },
      ],
    },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: (ctx: { dataIndex: number }) => {
              const z = group.zones[ctx.dataIndex];
              if (!z) return "";
              if (unit === "W") {
                return `Range ${z.lower_w}–${z.upper_w} W`;
              }
              return `Range ${z.lower_bpm}–${z.upper_bpm} bpm`;
            },
          },
        },
      },
      scales: {
        y: { ticks: { callback: (v: number | string) => `${v}%` } },
      },
    },
  } as ChartConfiguration;
}

const powerConfig = computed(() => buildConfig(data.value.power, "W"));
const hrConfig = computed(() => buildConfig(data.value.hr, "bpm"));

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const payload = await apiGet<ZonesResponse | undefined>(
      "/api/v1/analytics/zones",
    );
    if (payload && typeof payload === "object") {
      data.value = payload;
    }
  } catch (e) {
    error.value = "Impossibile caricare le zone di allenamento.";
    console.error("zones load failed", e);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.zones-panel {
  margin: 1rem 0;
}
.error-state {
  color: var(--error);
  background: var(--alert-bg, rgba(255, 51, 102, 0.15));
  border: 1px solid var(--alert-border, rgba(255, 51, 102, 0.4));
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}
.zones-sub {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin: 0 0 1rem;
}
.zones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.2rem;
}
.zone-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 1rem;
}
.zone-card h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  color: var(--text-primary);
}
</style>
