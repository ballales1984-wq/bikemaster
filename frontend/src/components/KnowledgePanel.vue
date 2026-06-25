<template>
  <div class="knowledge-panel">
    <div class="panel-header">
      <h2>📚 Knowledge Base</h2>
      <div class="kb-stats" v-if="stats">
        <span class="kb-badge">{{ stats.total_documents ?? 0 }} documenti</span>
        <span class="kb-badge">{{ stats.total_topics ?? 0 }} argomenti</span>
      </div>
    </div>

    <!-- Search bar -->
    <div class="search-container">
      <div class="search-box" :class="{ focused: searchFocused }">
        <span class="search-icon">🔍</span>
        <input
          v-model="query"
          ref="searchInput"
          type="text"
          placeholder="Cerca... (es. 'come migliorare resistenza', 'FTP training')"
          class="search-input"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
          @keydown.enter="search"
          @input="onInput"
        />
        <button v-if="query" class="clear-btn" @click="clearSearch">✕</button>
      </div>
      <button class="btn search-btn" @click="search" :disabled="!query.trim() || loading">
        {{ loading ? '⏳' : 'Cerca' }}
      </button>
    </div>

    <!-- Topic pills -->
    <div class="topics-row" v-if="topics.length && !results.length && !loading">
      <div class="topics-label">Argomenti:</div>
      <div class="topics-list">
        <button
          class="topic-pill"
          v-for="t in topics"
          :key="t"
          @click="searchTopic(t)"
        >{{ t }}</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="skeleton-container">
      <div class="skeleton skeleton-card" v-for="i in 3" :key="i" style="height: 90px; margin-bottom: 12px;"></div>
    </div>

    <!-- Results -->
    <div v-else-if="results.length" class="results-section">
      <div class="results-header">
        <span class="results-count">{{ results.length }} risultati per "<strong>{{ lastQuery }}</strong>"</span>
        <button class="btn btn-sm btn-secondary" @click="clearSearch">← Tutti gli argomenti</button>
      </div>
      <div class="result-card" v-for="(r, i) in results" :key="i" :style="{ animationDelay: i * 0.05 + 's' }">
        <div class="result-header">
          <div class="result-topic">{{ r.topic || r.source || 'Documento' }}</div>
          <div class="result-score" v-if="r.score != null">
            <div class="score-bar"><div class="score-fill" :style="{ width: (r.score * 100) + '%' }"></div></div>
            <span>{{ (r.score * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="result-text" v-html="highlightQuery(r.content || r.text || r.chunk || '', lastQuery)"></div>
        <div class="result-meta" v-if="r.source_file">
          <span>📄 {{ r.source_file }}</span>
        </div>
      </div>
    </div>

    <!-- Empty search -->
    <div v-else-if="searched && !loading" class="empty-state">
      <div class="empty-icon">🔎</div>
      <div class="empty-title">Nessun risultato per "{{ lastQuery }}"</div>
      <div class="empty-desc">Prova con altre parole chiave o sfoglia gli argomenti disponibili.</div>
      <button class="btn btn-sm btn-secondary" style="margin-top: 12px;" @click="clearSearch">← Torna agli argomenti</button>
    </div>

    <!-- Topic browser (default view) -->
    <div v-else-if="!loading && topics.length" class="topics-browser">
      <div class="browser-grid">
        <div
          class="topic-card"
          v-for="t in topics"
          :key="t"
          @click="searchTopic(t)"
        >
          <div class="topic-icon">{{ topicIcon(t) }}</div>
          <div class="topic-name">{{ t }}</div>
        </div>
      </div>
    </div>

    <!-- Total empty -->
    <div v-else-if="!loading" class="empty-state">
      <div class="empty-icon">📚</div>
      <div class="empty-title">Knowledge Base vuota</div>
      <div class="empty-desc">Aggiungi documenti nella cartella <code>knowledge_base/</code> e ricarica gli indici.</div>
      <button class="btn btn-sm" style="margin-top: 12px;" @click="reload">🔄 Ricarica indici</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet, apiPost } from '../utils/api'

const query = ref('')
const results = ref([])
const topics = ref([])
const stats = ref(null)
const loading = ref(false)
const searched = ref(false)
const lastQuery = ref('')
const searchFocused = ref(false)
const searchInput = ref(null)

let debounceTimer = null

const TOPIC_ICONS = {
  allenamento: '🏋️', training: '🏋️', recovery: '😴', recupero: '😴',
  potenza: '⚡', power: '⚡', nutrition: '🥗', nutrizione: '🥗',
  gps: '📍', route: '🗺️', percorso: '🗺️', ftp: '⚙️', stress: '📊',
  ciclismo: '🚴', cycling: '🚴', salita: '⛰️', climb: '⛰️',
  cardio: '❤️', hr: '❤️', frequenza: '❤️', speed: '💨', velocità: '💨',
}

function topicIcon(topic) {
  const t = topic.toLowerCase()
  for (const [key, icon] of Object.entries(TOPIC_ICONS)) {
    if (t.includes(key)) return icon
  }
  return '📖'
}

function highlightQuery(text, q) {
  if (!q || !text) return escapeHtml(text)
  const escaped = escapeHtml(text)
  const words = q.split(/\s+/).filter(Boolean)
  let result = escaped
  for (const word of words) {
    const re = new RegExp(`(${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    result = result.replace(re, '<mark>$1</mark>')
  }
  return result
}

function escapeHtml(str) {
  return (str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function onInput() {
  clearTimeout(debounceTimer)
  if (query.value.trim().length >= 3) {
    debounceTimer = setTimeout(search, 600)
  }
}

async function search() {
  const q = query.value.trim()
  if (!q) return
  loading.value = true
  searched.value = true
  lastQuery.value = q
  results.value = []
  try {
    const data = await apiGet('/api/v1/knowledge/search', { q })
    results.value = data.results || data.chunks || data || []
  } catch (e) {
    console.error('search', e)
    results.value = []
  } finally {
    loading.value = false
  }
}

async function searchTopic(topic) {
  query.value = topic
  await search()
}

function clearSearch() {
  query.value = ''
  results.value = []
  searched.value = false
  lastQuery.value = ''
  searchInput.value?.focus()
}

async function reload() {
  loading.value = true
  try {
    await apiPost('/api/v1/knowledge/reload', {})
    await loadTopics()
  } catch (e) {
    console.error('reload', e)
  } finally {
    loading.value = false
  }
}

async function loadTopics() {
  try {
    const data = await apiGet('/api/v1/knowledge')
    topics.value = Array.isArray(data) ? data : (data.topics || [])
  } catch (e) {
    console.warn('topics', e)
    topics.value = []
  }
}

async function loadStats() {
  try {
    stats.value = await apiGet('/api/v1/knowledge/stats')
  } catch (e) {
    console.warn('stats', e)
  }
}

onMounted(async () => {
  await Promise.all([loadTopics(), loadStats()])
})
</script>

<style scoped>
.knowledge-panel { display: flex; flex-direction: column; gap: 20px; }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.panel-header h2 {
  margin: 0;
  color: var(--accent);
  font-size: 1.3rem;
}

.kb-stats { display: flex; gap: 8px; }

.kb-badge {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Search */
.search-container {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0 14px;
  gap: 10px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-box.focused {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(0, 255, 204, 0.1);
}

.search-icon { font-size: 1rem; color: var(--text-muted); flex-shrink: 0; }

.search-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 0.95rem;
  padding: 12px 0;
  font-family: inherit;
}
.search-input::placeholder { color: var(--text-muted); }

.clear-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.9rem;
  padding: 4px;
  line-height: 1;
  flex-shrink: 0;
}
.clear-btn:hover { color: var(--text-primary); }

.search-btn { flex-shrink: 0; min-width: 70px; }

/* Topics row */
.topics-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.topics-label { font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; }
.topics-list { display: flex; gap: 6px; flex-wrap: wrap; }

.topic-pill {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: var(--transition);
}
.topic-pill:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(0, 255, 204, 0.08);
}

/* Results */
.results-section { display: flex; flex-direction: column; gap: 12px; }

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.results-count {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.results-count strong { color: var(--text-primary); }

.result-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  transition: var(--transition);
  animation: fadeUp 0.3s ease both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-card:hover {
  border-color: var(--border-light);
  box-shadow: var(--shadow-sm);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 10px;
}

.result-topic {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-score {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.score-bar {
  width: 60px;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}
.score-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
}

.result-text {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-text :deep(mark) {
  background: rgba(0, 255, 204, 0.2);
  color: var(--accent);
  border-radius: 2px;
  padding: 0 2px;
}

.result-meta {
  margin-top: 8px;
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* Topic browser grid */
.browser-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.topic-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.topic-card:hover {
  border-color: var(--accent);
  background: rgba(0, 255, 204, 0.06);
  transform: translateY(-3px);
  box-shadow: var(--shadow-sm);
}

.topic-icon { font-size: 1.8rem; }

.topic-name {
  font-size: 0.82rem;
  color: var(--text-secondary);
  text-transform: capitalize;
}

code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--accent);
}
</style>
