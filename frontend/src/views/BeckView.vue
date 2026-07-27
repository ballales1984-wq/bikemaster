<template>
  <div class="beck">
    <h2>Analisi Beck — Depressione</h2>
    <div class="layout">
      <div class="questionnaire">
        <div v-if="!isComplete" class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }" />
          <span>{{ answered }} / {{ store.items.length }}</span>
        </div>
        <div v-if="showResult" class="result-card">
          <h3>Risultato</h3>
          <p class="score">
            Punteggio: <strong>{{ totalScore }}</strong>
          </p>
          <p class="severity">
            Livello: <strong :class="severityClass">{{ severityLabel }}</strong>
          </p>
          <p class="disclaimer">
            Questo strumento è solo un indicatore di screening e non sostituisce
            una valutazione professionale.
          </p>
          <div class="actions">
            <button class="btn btn-primary" @click="showResult = false">
              Rispondi
            </button>
            <button class="btn btn-secondary" @click="reset">
              Nuovo tentativo
            </button>
          </div>
        </div>
        <div v-else-if="store.items.length" class="questions">
          <div
            v-for="(item, index) in visibleItems"
            :key="index + page * pageSize"
            class="question"
          >
            <p class="question-text">{{ item[0] }}</p>
            <div class="options">
              <button
                v-for="score in scores"
                :key="score"
                class="option"
                :class="{ 'option--selected': selectedScore(index) === score }"
                @click="
                  store.setAnswer(
                    index + page * pageSize,
                    score as BeckItemScore,
                  )
                "
              >
                {{ score }}
              </button>
            </div>
          </div>
          <div class="pagination">
            <button
              class="btn btn-secondary"
              :disabled="page === 0"
              @click="page--"
            >
              Indietro
            </button>
            <span>Pagina {{ page + 1 }} / {{ totalPages }}</span>
            <button
              class="btn btn-secondary"
              :disabled="page >= totalPages - 1"
              @click="page++"
            >
              Avanti
            </button>
          </div>
        </div>
        <div class="notes">
          <label for="notes">Note aggiuntive:</label>
          <textarea
            id="notes"
            v-model="store.currentNotes"
            rows="4"
            placeholder="Opzionale..."
          />
        </div>
        <div class="actions">
          <button
            class="btn btn-primary"
            :disabled="!store.isComplete || store.saving"
            @click="submit"
          >
            {{ store.saving ? "Salvataggio..." : "Invia assessment" }}
          </button>
          <button class="btn btn-secondary" @click="reset">Reset</button>
        </div>
      </div>
      <aside class="sidebar">
        <div class="card">
          <h3>Ultimo risultato</h3>
          <div v-if="store.latest" class="latest">
            <p>
              {{ store.latest.total_score }} punti —
              <strong :class="severityClassFor(store.latest.severity)">{{
                severityLabelFor(store.latest.severity)
              }}</strong>
            </p>
            <p class="date">{{ formatDate(store.latest.created_at) }}</p>
          </div>
          <p v-else class="empty">Nessun assessment salvato.</p>
        </div>
        <div class="card">
          <h3>Consigli</h3>
          <p>
            Se il punteggio è elevato o hai pensieri di autolesionismo, contatta
            immediatamente un professionista della salute mentale o un servizio
            di emergenza.
          </p>
        </div>
      </aside>
    </div>
    <div v-if="store.error" class="error">{{ store.error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useBeckStore } from "../stores/beck";
import type { BeckItemScore } from "../types/index";

const store = useBeckStore();

const page = ref(0);
const pageSize = 7;
const showResult = ref(false);

const scores = [0, 1, 2, 3] as const;

const severityLabels: Record<string, string> = {
  minimal: "Minimo",
  mild: "Lieve",
  moderate: "Moderato",
  severe: "Grave",
};

const visibleItems = computed(() =>
  store.items.slice(page.value * pageSize, (page.value + 1) * pageSize),
);
const totalPages = computed(() =>
  Math.max(1, Math.ceil(store.items.length / pageSize)),
);
const answered = computed(() => store.answers.size);
const progress = computed(() => store.progress);
const isComplete = computed(() => store.isComplete);
const totalScore = computed(() => store.totalScore);
const severity = computed(() => store.severity);
const severityLabel = computed(
  () => severityLabels[store.severity] || store.severity,
);
const severityClass = computed(() => `severity-${store.severity}`);

function selectedScore(index: number): BeckItemScore | undefined {
  return store.answers.get(index);
}

function severityLabelFor(value: string) {
  return severityLabels[value] || value;
}

function severityClassFor(value: string) {
  return `severity-${value}`;
}

function formatDate(value: string | undefined | null) {
  if (!value) return "";
  return new Date(value).toLocaleString("it-IT");
}

async function submit() {
  try {
    await store.submit();
    showResult.value = true;
  } catch {
    // handled by store
  }
}

function reset() {
  store.reset();
  showResult.value = false;
  page.value = 0;
}

onMounted(async () => {
  try {
    await store.fetchLatest();
  } catch {
    // handled by store
  }
});
</script>

<style scoped>
.beck {
  max-width: 1100px;
  margin: 0 auto;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 1.5rem;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
.progress-bar {
  position: relative;
  height: 1.5rem;
  background: var(--border);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress-fill {
  position: absolute;
  inset: 0;
  background: #2563eb;
  transition: width 0.2s ease;
}
.progress-bar span {
  position: relative;
  color: #fff;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
.question {
  padding: 1rem 0;
  border-bottom: 1px solid var(--border);
}
.question-text {
  margin: 0 0 0.75rem;
}
.options {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.option {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.4rem 0.75rem;
  background: var(--surface);
  cursor: pointer;
}
.option--selected {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 1rem 0;
}
.notes {
  margin-top: 1rem;
}
.notes label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 600;
}
.notes textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 0.5rem;
  background: var(--surface);
  color: inherit;
  resize: vertical;
}
.actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.5rem;
}
.error {
  margin-top: 1rem;
  color: #b91c1c;
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.card {
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1rem;
  background: var(--surface);
}
.card h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}
.latest p {
  margin: 0.25rem 0;
}
.empty {
  color: var(--text-muted);
}
.result-card {
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1rem;
  background: var(--surface);
  margin-bottom: 1rem;
}
.score {
  font-size: 1.25rem;
  margin: 0.25rem 0;
}
.severity {
  font-size: 1.1rem;
  margin: 0.25rem 0;
}
.disclaimer {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
}
.severity-minimal {
  color: #16a34a;
}
.severity-mild {
  color: #d97706;
}
.severity-moderate {
  color: #dc2626;
}
.severity-severe {
  color: #7f1d1d;
}
</style>
