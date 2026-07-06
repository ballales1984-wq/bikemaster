<template>
  <div class="coach-panel">
    <div class="coach-header">
      <div class="coach-title">
        <span class="coach-avatar">🧠</span>
        <div>
          <h2>{{ t('coach.title') }}</h2>
          <span class="coach-status">{{ connected ? '🟢 ' + t('coach.online') : '⚪ ' + t('coach.offline') }}</span>
        </div>
      </div>
      <div class="header-actions">
         <button class="btn btn-sm btn-secondary" @click="loadFullReport" :disabled="loadingReport" :title="t('coach.report')" :aria-label="t('coach.report')">
           {{ loadingReport ? '⏳' : '📊' }} {{ t('coach.report') }}
         </button>
         <button class="btn btn-sm btn-secondary" @click="clearChat" :title="t('coach.clear')" :aria-label="t('coach.clear')">🗑️</button>
      </div>
    </div>

    <!-- Score cards -->
    <div class="score-strip" v-if="scores.length">
      <div class="score-pill" v-for="s in scores" :key="s.label">
        <span class="pill-val" :style="{ color: s.color }">{{ s.value }}</span>
        <span class="pill-lbl">{{ s.label }}</span>
      </div>
    </div>

    <!-- Chat window -->
    <div class="chat-window" ref="chatWindow">
      <!-- Welcome message -->
      <div class="message bot-msg" v-if="messages.length === 0">
        <div class="msg-avatar">🧠</div>
        <div class="msg-content">
          <div class="msg-bubble">
            {{ t('coach.welcome') }}
          </div>
          <div class="quick-actions">
            <button class="quick-btn" v-for="q in quickQuestions" :key="q" @click="sendQuick(q)">{{ q }}</button>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role === 'user' ? 'user-msg' : 'bot-msg'"
      >
        <div class="msg-avatar">{{ msg.role === 'user' ? '🚴' : '🧠' }}</div>
        <div class="msg-content">
          <div class="msg-bubble" v-html="formatMsg(msg.content)"></div>
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>

      <!-- Typing indicator -->
      <div class="message bot-msg" v-if="thinking">
        <div class="msg-avatar">🧠</div>
        <div class="msg-content">
          <div class="msg-bubble typing-bubble">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input-area">
      <textarea
        v-model="userInput"
        ref="inputRef"
        class="chat-input"
        :placeholder="t('coach.placeholder')"
        rows="1"
        @keydown.enter.prevent="sendMessage"
        @input="autoResize"
        :disabled="thinking"
        :aria-label="t('coach.ask')"
      ></textarea>
      <button class="send-btn" @click="sendMessage" :disabled="!userInput.trim() || thinking">
        <span v-if="!thinking">➤</span>
        <span v-else class="spinner" style="width:16px;height:16px;border-width:2px;"></span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useI18n } from '../composables/useI18n'
import { apiGet, apiPost } from '../utils/api'
import DOMPurify from 'dompurify'

const { t } = useI18n()

const messages = ref([])
const userInput = ref('')
const thinking = ref(false)
const loadingReport = ref(false)
const connected = ref(true)
const chatWindow = ref(null)
const inputRef = ref(null)
const coachData = ref(null)
const athleteId = ref(null)

const quickQuestions = [
  '💪 Prossimo allenamento consigliato',
  '😴 Quanto recupero mi serve?',
  '📈 Analizza le mie ultime uscite',
  '🎯 Come aumentare il FTP?',
]

const scores = computed(() => {
  const s = coachData.value?.training_scores
  if (!s) return []
  const colors = { Performance: '#00ffcc', Endurance: '#0088ff', Efficiency: '#ff6b35', Recovery: '#a855f7' }
  return s.map(sc => ({ label: sc.label, value: Number(sc.value || 0).toFixed(1), color: colors[sc.label] || '#fff' }))
})

function formatMsg(text) {
  if (!text) return ''
  const html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
  return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['strong', 'em', 'br', 'li', 'ul'], ALLOWED_ATTR: [] })
}

function getTime() {
  return new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}

async function scrollToBottom() {
  await nextTick()
  if (chatWindow.value) {
    chatWindow.value.scrollTop = chatWindow.value.scrollHeight
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || thinking.value) return

  messages.value.push({ role: 'user', content: text, time: getTime() })
  userInput.value = ''
  if (inputRef.value) { inputRef.value.style.height = 'auto' }
  thinking.value = true
  await scrollToBottom()

  try {
    const params = {}
    if (athleteId.value) params.athlete_id = athleteId.value
    const resp = await apiPost('/api/v1/coach/chat', { message: text, ...params })
    const reply = resp.response || resp.message || resp.advice || JSON.stringify(resp)
    messages.value.push({ role: 'assistant', content: reply, time: getTime() })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '⚠️ Errore nella risposta. Verifica la configurazione di GROQ_API_KEY nel backend.',
      time: getTime()
    })
    connected.value = false
  } finally {
    thinking.value = false
    await scrollToBottom()
  }
}

async function sendQuick(question) {
  userInput.value = question
  await sendMessage()
}

async function loadFullReport() {
  if (!athleteId.value) return
  loadingReport.value = true
  try {
    const data = await apiGet('/api/v1/coach/full', { athlete_id: athleteId.value })
    coachData.value = data
    if (data.training_advice) {
      messages.value.push({
        role: 'assistant',
        content: `**📊 Report Completo**\n\n**Allenamento:**\n${data.training_advice}\n\n**Recupero:**\n${data.recovery_advice || '—'}`,
        time: getTime()
      })
      await scrollToBottom()
    }
  } catch (e) {
    console.error('coach full', e)
  } finally {
    loadingReport.value = false
  }
}

function clearChat() {
  messages.value = []
}

async function init() {
   try {
     const me = await apiGet('/api/v1/athletes/me')
     athleteId.value = me.athlete?.id ?? null
     if (athleteId.value) {
       const scores = await apiGet('/api/v1/coach/full', { athlete_id: athleteId.value })
       coachData.value = scores
     }
   } catch (e) {
     console.warn('init coach', e)
   }
 }

onMounted(() => init())
</script>

<style scoped>
.coach-panel {
  display: flex;
  flex-direction: column;
  height: 70vh;
  min-height: 500px;
}

.coach-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.coach-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.coach-avatar {
  font-size: 2rem;
  background: var(--bg-secondary);
  border: 2px solid var(--accent);
  border-radius: 50%;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.coach-title h2 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--accent);
}

.coach-status {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Score strip */
.score-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.score-pill {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 14px;
  display: flex;
  align-items: center;
  gap: 6px;
 }

.pill-val {
  font-size: 1rem;
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
}

.pill-lbl {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Chat window */
.chat-window {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.chat-window::-webkit-scrollbar {
  width: 4px;
}
.chat-window::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

/* Messages */
.message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  animation: msgIn 0.3s ease;
}

.user-msg {
  flex-direction: row-reverse;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-avatar {
  font-size: 1.4rem;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: 50%;
  border: 1px solid var(--border);
}

.msg-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 80%;
}

.user-msg .msg-content { align-items: flex-end; }

.msg-bubble {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 10px 14px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-primary);
}

.user-msg .msg-bubble {
  background: rgba(0, 255, 204, 0.12);
  border-color: rgba(0, 255, 204, 0.25);
  color: var(--text-primary);
  border-radius: 16px 16px 4px 16px;
}

.bot-msg .msg-bubble {
  border-radius: 16px 16px 16px 4px;
}

.msg-time {
  font-size: 0.68rem;
  color: var(--text-muted);
  padding: 0 4px;
}

/* Typing indicator */
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 16px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: bounce 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* Quick actions */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.quick-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
}

.quick-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(0, 255, 204, 0.08);
  transform: translateY(-1px);
}

/* Input area */
.chat-input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  margin-top: 8px;
}

.chat-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 12px 18px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  resize: none;
  outline: none;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  min-height: 46px;
  max-height: 120px;
  line-height: 1.5;
}

.chat-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(0, 255, 204, 0.1);
}

.chat-input::placeholder { color: var(--text-muted); }
.chat-input:disabled { opacity: 0.5; }

.send-btn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: var(--accent-gradient);
  color: #000;
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: var(--transition);
  box-shadow: 0 4px 12px rgba(0, 255, 204, 0.3);
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 6px 18px rgba(0, 255, 204, 0.4);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .coach-panel { height: 60vh; }
  .msg-content { max-width: 90%; }
  .quick-actions { gap: 4px; }
  .quick-btn { font-size: 0.72rem; padding: 5px 10px; }
}
</style>
