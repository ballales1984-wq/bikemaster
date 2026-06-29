<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Cookie Policy - Politica dei Cookie</h1>
      <p class="last-updated">Ultimo aggiornamento: Giugno 2025</p>
    </div>

    <div class="legal-content">
      <h2>1. Cosa sono i Cookie</h2>
      <p>I cookie sono piccoli file di testo memorizzati sul dispositivo dell'utente durante la navigazione su un sito web. I cookie permettono al sito di riconoscere l'utente e memorizzare determinate informazioni per migliorare l'esperienza di utilizzo.</p>

      <h2>2. Tipologie di Cookie Utilizzati</h2>
      <h3>2.1 Cookie Tecnici (Strettamente Necessari)</h3>
      <p>Questi cookie sono essenziali per il corretto funzionamento del servizio BikeMaster:</p>
      <table class="cookie-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Scopo</th>
            <th>Durata</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>access_token</code></td>
            <td>Autenticazione JWT dell'utente</td>
            <td>Sessione browser</td>
          </tr>
          <tr>
            <td><code>refresh_token</code></td>
            <td>Rinnovo automatico della sessione</td>
            <td>7 giorni</td>
          </tr>
          <tr>
            <td><code>bikemaster_session</code></td>
            <td>Gestione stato sessione utente</td>
            <td>Sessione browser</td>
          </tr>
        </tbody>
      </table>

      <h3>2.2 Cookie Analitici</h3>
      <p>Utilizzati per comprendere come gli utenti interagiscono con il servizio (anonimizzati o aggregati):</p>
      <ul>
        <li><strong>Statistiche di utilizzo:</strong> pagine visitate, durata della sessione, errori riscontrati</li>
        <li><strong>Performance:</strong> tempi di caricamento, chiamate API, metriche di sistema</li>
      </ul>

      <h3>2.3 Cookie di Preferenze</h3>
      <ul>
        <li><strong>Tema dark/light:</strong> preferenza tema dell'interfaccia</li>
        <li><strong>Layout dashboard:</strong> configurazione pannelli preferiti</li>
        <li><strong>Unità di misura:</strong> km/mi, °C/°F, watt/kg</li>
      </ul>

      <h2>3. Cookie di Terze Parti</h2>
      <p>Alcuni cookie possono essere impostati da servizi terzi integrati nel servizio:</p>
      <ul>
        <li><strong>Google Maps / OpenStreetMap:</strong> per la visualizzazione dei percorsi sulle mappe</li>
        <li><strong>Chart.js:</strong> nessun cookie proprio, dati gestiti localmente</li>
      </ul>
      <p>Questi terzi hanno proprie informative sulla privacy, non controllate da BikeMaster.</p>

      <h2>4. Gestione e Disabilitazione dei Cookie</h2>
      <p>L'utente può gestire i cookie direttamente tramite le impostazioni del browser:</p>
      <ul>
        <li><strong>Chrome:</strong> Impostazioni → Privacy e sicurezza → Cookie e altri dati dei siti</li>
        <li><strong>Firefox:</strong> Impostazioni → Privacy e sicurezza → Cookie e dati dei siti</li>
        <li><strong>Safari:</strong> Preferenze → Privacy → Gestione siti web</li>
        <li><strong>Edge:</strong> Impostazioni → Privacy, ricerca e servizi → Cookie</li>
      </ul>
      <p><strong>Nota:</strong> La disabilitazione dei cookie tecnici potrebbe compromettere il funzionamento del servizio e impedire l'accesso all'account.</p>

      <h2>5. Note per l'App Mobile (Android)</h2>
      <p>L'applicazione mobile Android di BikeMaster, installata tramite APK, non utilizza cookie tradizionali. Utilizza invece:</p>
      <ul>
        <li><strong>Shared Preferences Android:</strong> per dati di sessione e preferenze</li>
        <li><strong>Storage locale:</strong> per cache e dati offline</li>
      </ul>
      <p>Il tracciamento GPS in background richiede l'autorizzazione della posizione, gestita dal sistema operativo Android.</p>

      <h2>6. Strumenti di Tracciamento Alternativi</h2>
      <p>Oltre ai cookie, BikeMaster può utilizzare:</p>
      <ul>
        <li><strong>Local Storage:</strong> per la persistenza dei dati sul browser</li>
        <li><strong>Session Storage:</strong> per dati temporanei della sessione</li>
        <li><strong>IndexedDB:</strong> per caching avanzato di dati di attività</li>
      </ul>

      <h2>7. Aggiornamenti della Cookie Policy</h2>
      <p>Eventuali modifiche alla presente policy saranno pubblicate su questa pagina. Si consiglia di consultarla periodicamente.</p>

      <h2>8. Contatti</h2>
      <p>Per domande sui cookie o sulle pratiche di tracciamento: <a href="mailto:privacy@bikemaster.app">privacy@bikemaster.app</a></p>
    </div>

    <div class="cta-section">
      <RouterLink to="/" class="btn btn-primary">🏠 Torna all'Accedi</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.legal-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}
.legal-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #333;
}
.legal-header h1 {
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}
.last-updated {
  color: #888;
  font-size: 0.9rem;
}
.legal-content h2 {
  margin-top: 2rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #333;
  font-size: 1.3rem;
}
.legal-content h3 {
  margin-top: 1.5rem;
  font-size: 1.1rem;
  color: #ccc;
}
.legal-content p {
  line-height: 1.7;
  margin: 0.75rem 0;
}
.legal-content ul {
  margin: 0.75rem 0 0.75rem 1.5rem;
}
.legal-content li {
  line-height: 1.7;
  margin-bottom: 0.4rem;
}
.cookie-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}
.cookie-table th,
.cookie-table td {
  border: 1px solid #444;
  padding: 0.6rem;
  text-align: left;
}
.cookie-table th {
  background: #2a2a2a;
}
.cookie-table code {
  background: #2a2a2a;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-size: 0.9rem;
}
a {
  color: #42b983;
}
.cta-section {
  text-align: center;
  margin: 2rem 0 1rem;
}
.btn {
  display: inline-block;
  padding: 10px 24px;
  background: #42b983;
  color: #fff;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}
.btn:hover {
  background: #349a6e;
}
</style>