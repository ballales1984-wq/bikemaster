<template>
  <div class="about-page">
    <div class="about-header">
      <h1>🚴 BikeMaster</h1>
      <p class="tagline">Cycling Performance Intelligence</p>
    </div>

    <div class="about-content">
      <section class="hero">
        <h2>Chi Siamo</h2>
        <p>
          BikeMaster è un progetto open-source dedicato all'analisi avanzata
          delle performance ciclistiche. La nostra missione è fornire strumenti
          professionali per ciclisti di ogni livello, dai principianti agli
          atleti agonistici, per comprendere e migliorare le proprie performance
          attraverso dati, algoritmi e intelligenza artificiale.
        </p>
      </section>

      <section class="features">
        <h2>Cosa Facciamo</h2>
        <div class="feature-grid">
          <div class="feature-card">
            <h3>📊 Analisi Performance</h3>
            <p>
              Analisi completa delle uscite con metriche avanzate: Normalized
              Power, TSS, FTP, Critical Power, CTL/ATL/TSB.
            </p>
          </div>
          <div class="feature-card">
            <h3>🤖 AI Coach</h3>
            <p>
              Consigli personalizzati di allenamento e recupero tramite modelli
              LLM e conoscenze basate su dati scientifici.
            </p>
          </div>
          <div class="feature-card">
            <h3>🗺️ Mappe Interattive</h3>
            <p>
              Visualizzazione percorsi colorati per velocità, heatmap GPS, e
              analisi della sicurezza stradale.
            </p>
          </div>
          <div class="feature-card">
            <h3>📱 Tracking Mobile</h3>
            <p>
              Registrazione uscite direttamente dal telefono Android con
              servizio GPS in foreground.
            </p>
          </div>
          <div class="feature-card">
            <h3>🔄 Integrazioni</h3>
            <p>
              Sincronizzazione con Strava, Garmin Connect e Google Fit per
              importare tutte le tue attività.
            </p>
          </div>
          <div class="feature-card">
            <h3>📈 Benchmarking</h3>
            <p>
              Confronta le tue performance con atleti della tua categoria per
              capire il tuo livello.
            </p>
          </div>
        </div>
      </section>

      <section class="tech">
        <h2>Tecnologia</h2>
        <p>Costruiamo BikeMaster con tecnologie moderne e open-source:</p>
        <ul>
          <li><strong>Backend:</strong> FastAPI, Python 3.11+</li>
          <li><strong>Frontend:</strong> Vue 3, TypeScript, Vite</li>
          <li><strong>Database:</strong> SQLite / PostgreSQL con SQLAlchemy</li>
          <li><strong>AI/ML:</strong> NumPy, Pandas, SciPy, Groq LLM</li>
          <li><strong>Maps:</strong> Leaflet.js, Folium, OpenStreetMap</li>
          <li><strong>Mobile:</strong> Android Kotlin, Capacitor</li>
        </ul>
      </section>

      <section class="values">
        <h2>I Nostri Valori</h2>
        <ul>
          <li>
            <strong>Open Source:</strong> il codice è pubblico su GitHub sotto
            licenza MIT
          </li>
          <li>
            <strong>Privacy First:</strong> i tuoi dati sono tuoi, non li
            vendiamo a terzi
          </li>
          <li>
            <strong>Community Driven:</strong> sviluppiamo con e per la comunità
            ciclistica
          </li>
          <li>
            <strong>Scientific Approach:</strong> algoritmi basati su principi
            fisiologici e scientifici
          </li>
        </ul>
      </section>

      <section class="cta">
        <p>Vuoi contribuire o saperne di più?</p>
        <RouterLink
to="/contact" class="cta-button"> Contattaci </RouterLink>
      </section>

      <div class="login-cta">
        <RouterLink to="/" class="btn btn-secondary">
          🏠 Accedi a BikeMaster
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.about-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}
.about-header {
  text-align: center;
  margin-bottom: 2rem;
}
.about-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}
.tagline {
  color: #888;
  font-size: 1.1rem;
}
.about-content section {
  margin-bottom: 2.5rem;
}
.about-content h2 {
  border-bottom: 2px solid #42b983;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
  font-size: 1.4rem;
}
.about-content p {
  line-height: 1.8;
  margin-bottom: 0.75rem;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.feature-card {
  background: #1a1a1a;
  padding: 1.2rem;
  border-radius: 8px;
  border: 1px solid #333;
}
.feature-card h3 {
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
}
.feature-card p {
  font-size: 0.9rem;
  color: #bbb;
  margin: 0;
}
.tech ul,
.values ul {
  margin-left: 1.5rem;
}
.tech li,
.values li {
  line-height: 1.8;
  margin-bottom: 0.4rem;
}
.values li strong {
  color: #42b983;
}
.cta {
  text-align: center;
  padding: 2rem;
  background: #1a1a1a;
  border-radius: 8px;
  border: 1px solid #333;
}
.cta-button {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.75rem 2rem;
  background: #42b983;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: bold;
  transition: background 0.2s;
}
.cta-button:hover {
  background: #349a6e;
}
a {
  color: #42b983;
}
.login-cta {
  text-align: center;
  margin-top: 1rem;
}
.btn.btn-secondary {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: #2a2a2a;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}
.btn.btn-secondary:hover {
  background: #3a3a3a;
}
</style>
