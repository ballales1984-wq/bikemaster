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
        <h2>📖 Guida BikeMaster</h2>
        <button class="help-close" @click="close" aria-label="Close">
          ✕
        </button>
      </div>

      <div class="help-categories">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['cat-btn', { active: activeCategory === cat.key }]"
          @click="activeCategory = cat.key"
        >
          {{ cat.icon }} {{ cat.label }}
        </button>
      </div>

      <div class="help-body">
        <div v-if="activeCategory === 'welcome'" class="help-section">
          <h3>🏠 Pagina iniziale</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Inizia</strong>
              <p>Crea un nuovo account. Dopo la registrazione verrai reindirizzato al profilo atleta per completare i dati.</p>
            </div>
            <div class="help-tag">
              <strong>Accedi</strong>
              <p>Effettua il login con username e password già registrati.</p>
            </div>
            <div class="help-tag">
              <strong>Accedi con Google</strong>
              <p>Usa il tuo account Google per autenticarti velocemente senza inserire password.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'navigation'" class="help-section">
          <h3>🧭 Navigazione</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>🏍️ Uscite</strong>
              <p>Visualizza la lista di tutte le tue uscite registrate, con filtri per data e distanza.</p>
            </div>
            <div class="help-tag">
              <strong>📊 Dashboard</strong>
              <p>Riepilogo KPI principali: distanza totale, calorie, velocità media e trend recenti.</p>
            </div>
            <div class="help-tag">
              <strong>📍 Tracciamento</strong>
              <p>Avvia una nuova uscita in tempo reale con GPS. Mostra mappa live e metriche istantanee.</p>
            </div>
            <div class="help-tag">
              <strong>📥 Importa</strong>
              <p>Carica file GPX/FIT o sincronizza da servizi esterni (Strava, Google Fit, Wahoo).</p>
            </div>
            <div class="help-tag">
              <strong>🏃 Atleta</strong>
              <p>Compila il tuo profilo: peso, altezza, esperienza e obiettivi. Necessario per i calcoli personalizzati.</p>
            </div>
            <div class="help-tag">
              <strong>🧠 AI Coach</strong>
              <p>Chatta con il coach digitale per consigli su allenamento, recupero e strategia di gara.</p>
            </div>
            <div class="help-tag">
              <strong>📚 Knowledge</strong>
              <p>Base di conoscenza con principi fisiologici e regole di allenamento usate dal coach.</p>
            </div>
            <div class="help-tag">
              <strong>🧮 BM2</strong>
              <p>Motore di simulazione BikeMaster 2.0: modelli predittivi e algoritmi di performance.</p>
            </div>
            <div class="help-tag">
              <strong>📅 Calendario</strong>
              <p>Pianifica gli allenamenti settimanali e visualizza il carico di lavoro nel tempo.</p>
            </div>
            <div class="help-tag">
              <strong>🚴‍♂️ Granfondo</strong>
              <p>Strumento di pianificazione per granfondo e eventi ciclistici multi-giorno.</p>
            </div>
            <div class="help-tag">
              <strong>🗺️ Mappe</strong>
              <p>Visualizza i percorsi delle tue uscite su mappa interattiva con elevation profile.</p>
            </div>
            <div class="help-tag">
              <strong>🌐 AetherMap</strong>
              <p>Mappa cartografica avanzata per esplorazione e analisi territoriale (progetto R&D).</p>
            </div>
            <div class="help-tag">
              <strong>📍 POI</strong>
              <p>Itinerari e punti di interesse: fontane, ristori, panorami e punti tecnici.</p>
            </div>
            <div class="help-tag">
              <strong>🔥 Heatmap</strong>
              <p>Mappa di densità delle uscite: zone più percorse, frequenza e intensità.</p>
            </div>
            <div class="help-tag">
              <strong>🏅 Badge</strong>
              <p>Sistema di achievement: badge e obiettivi sbloccati in base alle tue performance.</p>
            </div>
            <div class="help-tag">
              <strong>⚖️ Confronto</strong>
              <p>Confronta due uscite o periodi diversi per vedere miglioramenti e differenze.</p>
            </div>
            <div class="help-tag">
              <strong>🌤️ Meteo</strong>
              <p>Previsioni meteo per la località di uscita. Include vento, umidità e consigli.</p>
            </div>
            <div class="help-tag">
              <strong>⚙️ Impostazioni</strong>
              <p>Configura URL backend, chiavi API personali e modalità di sincronizzazione.</p>
            </div>
            <div class="help-tag">
              <strong>🔌 Connessioni</strong>
              <p>Gestisci i servizi esterni: connetti/disconnetti Strava, Google Fit, Wahoo e salva API key.</p>
            </div>
            <div class="help-tag">
              <strong>🚪 Esci</strong>
              <p>Termina la sessione e torna alla schermata di login.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'tracking'" class="help-section">
          <h3>📍 Tracciamento uscita</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Tipo attività</strong>
              <p>Seleziona la disciplina: Bici, Corsa, Passeggiata, Trekking, Indoor o Altro. Influenza le metriche calcolate.</p>
            </div>
            <div class="help-tag">
              <strong>Avvia tracciamento</strong>
              <p>Inizia la registrazione GPS. Richiede permessi di localizzazione. La mappa si aggiorna in tempo reale.</p>
            </div>
            <div class="help-tag">
              <strong>⏸️ Pausa</strong>
              <p>Metti in pausa la registrazione senza perdere i dati accumulati. Riprendi quando vuoi.</p>
            </div>
            <div class="help-tag">
              <strong>▶️ Riprendi</strong>
              <p>Ripristina il tracciamento dopo una pausa. Il tempo di pausa non viene conteggiato.</p>
            </div>
            <div class="help-tag">
              <strong>⏹️ Ferma</strong>
              <p>Termina la sessione e genera il file GPX. Potrai caricarlo su BikeMaster o esportarlo.</p>
            </div>
            <div class="help-tag">
              <strong>Carica su BikeMaster</strong>
              <p>Invia automaticamente l'uscita appena tracciata al backend per salvarla nel tuo account.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'rides'" class="help-section">
          <h3>🏍️ Le mie uscite</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Traccia Uscita</strong>
              <p>Vai direttamente alla schermata di tracciamento GPS per iniziare una nuova uscita.</p>
            </div>
            <div class="help-tag">
              <strong>📅 Pianifica</strong>
              <p>Apri il calendario per organizzare gli allenamenti della settimana.</p>
            </div>
            <div class="help-tag">
              <strong>🧠 AI Coach</strong>
              <p>Chiedi consigli al coach digitale basati sui dati delle tue uscite recenti.</p>
            </div>
            <div class="help-tag">
              <strong>Lista uscite</strong>
              <p>Ogni riga mostra data, distanza, durata e velocità media. Clicca per vedere i dettagli completi.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'import'" class="help-section">
          <h3>📥 Importa uscite</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Carica file GPX/FIT</strong>
              <p>Trascina i file nella zona di upload o clicca per selezionarli. Supporta file multipli.</p>
            </div>
            <div class="help-tag">
              <strong>Importa da Google Fit</strong>
              <p>Connetti il tuo account Google Fit per importare automaticamente tutte le attività.</p>
            </div>
            <div class="help-tag">
              <strong>Connetti Strava</strong>
              <p>Autorizza Strava tramite OAuth per sincronizzare le tue uscite ciclistiche.</p>
            </div>
            <div class="help-tag">
              <strong>Disconnetti servizio</strong>
              <p>Revoca l'accesso al servizio esterno. I dati già importati rimangono salvati.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'settings'" class="help-section">
          <h3>⚙️ Impostazioni</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>URL Backend</strong>
              <p>Inserisci l'indirizzo del tuo backend locale (es. https://tuo-pc:8000). Lascia vuoto per usare lo stesso origine.</p>
            </div>
            <div class="help-tag">
              <strong>Salva / Predefinito</strong>
              <p>Salva l'URL personalizzato o ripristina quello predefinito (stesso origine).</p>
            </div>
            <div class="help-tag">
              <strong>Failover Render</strong>
              <p>Abilita il backup cloud su Render se il backend locale non risponde.</p>
            </div>
            <div class="help-tag">
              <strong>Chiavi API personali</strong>
              <p>Inserisci le tue chiavi per Groq (AI Coach), Google Maps, SerpAPI e Weather. Salvate solo sul dispositivo.</p>
            </div>
            <div class="help-tag">
              <strong>Importa chiavi</strong>
              <p>Incolla chiavi in formato JSON o KEY=VALUE per importarle in massa.</p>
            </div>
            <div class="help-tag">
              <strong>Verifica connessione</strong>
              <p>Testa la connettività con il backend e mostra lo stato attuale (locale / cloud / PC).</p>
            </div>
            <div class="help-tag">
              <strong>Modalità sincronizzazione</strong>
              <p>Scegli tra Local (Mai) per uso 100% offline o Cloud sync per backup bidirezionale opzionale.</p>
            </div>
            <div class="help-tag">
              <strong>Esporta / Importa dati</strong>
              <p>Scarica un backup completo delle uscite o ripristina da un file precedentemente esportato.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'athlete'" class="help-section">
          <h3>🏃 Profilo atleta</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Nome</strong>
              <p>Il tuo nome visualizzato. Minimo 3 caratteri.</p>
            </div>
            <div class="help-tag">
              <strong>Età / Peso / Altezza</strong>
              <p>Dati anagrafici per calcoli personalizzati di potenza e soglie.</p>
            </div>
            <div class="help-tag">
              <strong>% Grasso corporeo</strong>
              <p>Opzionale. Migliora la precisione dei modelli di performance.</p>
            </div>
            <div class="help-tag">
              <strong>Anni di attività / Sessioni settimanali</strong>
              <p>Aiutano il coach a calibrare i consigli in base alla tua esperienza.</p>
            </div>
            <div class="help-tag">
              <strong>Livello</strong>
              <p>Da Beginner a Elite. Influenza le soglie di allenamento suggerite.</p>
            </div>
            <div class="help-tag">
              <strong>Obiettivi</strong>
              <p>Descrivi i tuoi obiettivi (es. Gran Fondo, criterium). Il coach li userà per i piani.</p>
            </div>
            <div class="help-tag">
              <strong>Salva atleta</strong>
              <p>Memorizza il profilo. Se è il primo login, verrai reindirizzato automaticamente alle uscite.</p>
            </div>
            <div class="help-tag">
              <strong>📊 Scores</strong>
              <p>Calcola e visualizza i punteggi atleta basati sui dati inseriti.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'coach'" class="help-section">
          <h3>🧠 AI Coach</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Chat</strong>
              <p>Scrivi domande libere su allenamento, recupero, alimentazione o strategia di gara.</p>
            </div>
            <div class="help-tag">
              <strong>📊 Report</strong>
              <p>Genera un report completo dell'atleta con punteggi, suggerimenti e aree di miglioramento.</p>
            </div>
            <div class="help-tag">
              <strong>🗑️ Pulisci chat</strong>
              <p>Cancella la conversazione corrente per iniziare un nuovo dialogo.</p>
            </div>
            <div class="help-tag">
              <strong>Domande rapide</strong>
              <p>Usa i suggerimenti predefiniti per chiedere consigli comuni senza digitare.</p>
            </div>
          </div>
        </div>

        <div v-if="activeCategory === 'zones'" class="help-section">
          <h3>📈 Zone di allenamento</h3>
          <div class="tag-grid">
            <div class="help-tag">
              <strong>Zone 1-2</strong>
              <p>Recupero attivo e fondo lento. Base per costruire la resistenza aerobica.</p>
            </div>
            <div class="help-tag">
              <strong>Zona 3</strong>
              <p>Soglia aerobica. Migliora l'efficienza cardiovascolare.</p>
            </div>
            <div class="help-tag">
              <strong>Zona 4</strong>
              <p>Soglia anaerobica. Aumenta la tolleranza al lattato.</p>
            </div>
            <div class="help-tag">
              <strong>Zona 5-7</strong>
              <p>Interval training e soglia massimale. Sviluppa potenza e velocità.</p>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <button
      v-if="loggedIn"
      class="help-fab"
      :aria-label="open ? 'Chiudi guida' : 'Apri guida'"
      @click="toggle"
    >
      {{ open ? "✕" : "❓" }}
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const open = ref(false);
const activeCategory = ref("navigation");

const categories = [
  { key: "welcome", label: "Inizio", icon: "🏠" },
  { key: "navigation", label: "Navigazione", icon: "🧭" },
  { key: "tracking", label: "Tracciamento", icon: "📍" },
  { key: "rides", label: "Uscite", icon: "🏍️" },
  { key: "import", label: "Import", icon: "📥" },
  { key: "settings", label: "Impostazioni", icon: "⚙️" },
  { key: "athlete", label: "Atleta", icon: "🏃" },
  { key: "coach", label: "AI Coach", icon: "🧠" },
  { key: "zones", label: "Zone", icon: "📈" },
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
