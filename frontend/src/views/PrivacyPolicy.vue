<!--
  Pagina statica della Privacy Policy.
  Informativa completa sul trattamento dei dati personali, GDPR, sicurezza,
  condivisione con terze parti e diritti dell'utente.
  Layout: contenitore centrato con intestazione, testo formattato e link a Cookie Policy.
-->
<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Privacy Policy - Informativa sulla Privacy</h1>
      <p class="last-updated">Ultimo aggiornamento: Giugno 2025</p>
    </div>

    <div class="legal-content">
      <h2>1. Titolare del Trattamento</h2>
      <p>
        Il titolare del trattamento dei dati personali raccolti attraverso
        BikeMaster è:
      </p>
      <ul>
        <li><strong>Denominazione:</strong> BikeMaster Team</li>
        <li><strong>Email:</strong> privacy@bikemaster.app</li>
      </ul>

      <h2>2. Tipologie di Dati Raccolti</h2>
      <p>
        Attraverso l'utilizzo di BikeMaster, raccogliamo le seguenti categorie
        di dati:
      </p>
      <ul>
        <li>
          <strong>Dati di navigazione:</strong> indirizzo IP, tipo di browser,
          sistema operativo, dati di log
        </li>
        <li>
          <strong>Dati personali dell'utente:</strong> nome, email, età, peso,
          altezza, dati medici forniti volontariamente nel profilo atleta
        </li>
        <li>
          <strong>Dati GPS e attività fisica:</strong> coordinate geografiche,
          tracciato percorso, velocità, altitudine, frequenza cardiaca, potenza,
          cadenza, distanza, dislivello
        </li>
        <li>
          <strong>Dati di geolocalizzazione:</strong> posizione in tempo reale
          durante il tracciamento GPS da telefono
        </li>
        <li>
          <strong>Dati da servizi esterni:</strong> dati di attività da Strava,
          Garmin Connect, Google Fit (solo se autorizzati dall'utente)
        </li>
        <li>
          <strong>Credenziali di accesso:</strong> username e password
          (memorizzati in forma crittografata)
        </li>
      </ul>

      <h2>3. Finalità del Trattamento</h2>
      <p>I dati personali sono trattati per le seguenti finalità:</p>
      <ul>
        <li>
          <strong>Fornitura del servizio:</strong> analisi delle performance
          ciclistiche, calcolo metriche (calorie, TSS, CTL/ATL/TSB), generazione
          mappe e report
        </li>
        <li>
          <strong>Funzionalità AI Coach:</strong> consigli personalizzati di
          allenamento e recupero
        </li>
        <li>
          <strong>Autenticazione:</strong> gestione account e accesso al
          servizio
        </li>
        <li>
          <strong>Integrazioni:</strong> sincronizzazione con servizi esterni
          previo consenso
        </li>
        <li>
          <strong>Miglioramento del servizio:</strong> statistica aggregata e
          anonimizzata per migliorare le funzionalità
        </li>
        <li>
          <strong>Sicurezza:</strong> protezione da accessi non autorizzati e
          rilevamento anomalie
        </li>
      </ul>

      <h2>4. Base Giuridica del Trattamento</h2>
      <ul>
        <li>
          <strong>Esecuzione del contratto:</strong> trattamento necessario per
          fornire il servizio richiesto (Art. 6, comma 1, lett. b GDPR)
        </li>
        <li>
          <strong>Consenso:</strong> trattamento dati sanitari e
          geolocalizzazione in tempo reale (Art. 6, comma 1, lett. a GDPR)
        </li>
        <li>
          <strong>Interesse legittimo:</strong> sicurezza dei dati, statistiche
          aggregate (Art. 6, comma 1, lett. f GDPR)
        </li>
      </ul>

      <h2>5. Dati Sensibili e Geolocalizzazione</h2>
      <p>Il servizio raccoglie dati sensibili potenziali tra cui:</p>
      <ul>
        <li>
          <strong>Dati di salute:</strong> frequenza cardiaca, dati di
          affaticamento, punteggi di performance (Art. 9 GDPR)
        </li>
        <li>
          <strong>Geolocalizzazione:</strong> posizione GPS continua durante il
          tracciamento da dispositivo mobile
        </li>
      </ul>
      <p>
        Tali dati sono trattati esclusivamente previo consenso esplicito
        dell'utente e sono utilizzati solo per le finalità indicate nella
        presente informativa.
      </p>

      <h2>6. Condivisione dei Dati e Terze Parti</h2>
      <p>
        I dati personali non sono ceduti a terzi a titolo oneroso. Sono
        condivisi esclusivamente con:
      </p>
      <ul>
        <li>
          <strong>Strava:</strong> previa autorizzazione OAuth2 dell'utente
        </li>
        <li>
          <strong>Garmin Connect:</strong> previa autorizzazione OAuth2
          dell'utente
        </li>
        <li>
          <strong>Google Fit:</strong> previa autorizzazione OAuth2 dell'utente
        </li>
        <li>
          <strong>Google Maps / OpenStreetMap:</strong> dati di
          geolocalizzazione per rendering mappe
        </li>
        <li>
          <strong>Groq API:</strong> dati di allenamento per l'AI Coach (non
          condivide dati identificativi)
        </li>
        <li>
          <strong>OpenAI API:</strong> embedding per ricerca semantica nella
          Knowledge Base (dati anonimizzati)
        </li>
      </ul>

      <h2>7. Conservazione dei Dati</h2>
      <ul>
        <li>
          <strong>Dati di tracciamento GPS:</strong> conservati fino a
          eliminazione da parte dell'utente
        </li>
        <li>
          <strong>Dati profilo atleta:</strong> conservati fino a eliminazione
          account
        </li>
        <li>
          <strong>Dati di accesso (JWT):</strong> conservati per la durata della
          sessione
        </li>
        <li>
          <strong>Token OAuth:</strong> conservati fino a revoca esplicita
        </li>
      </ul>

      <h2>8. Diritti dell'Utente</h2>
      <p>Ai sensi degli articoli 15-22 del GDPR, l'utente ha diritto di:</p>
      <ul>
        <li>Accedere ai propri dati personali</li>
        <li>Richiedere rettifica o aggiornamento</li>
        <li>Richiedere cancellazione (right to be forgotten)</li>
        <li>Limitare il trattamento</li>
        <li>Opporsi al trattamento</li>
        <li>Portabilità dei dati</li>
        <li>Revocare il consenso in qualsiasi momento</li>
      </ul>
      <p>Per esercitare i diritti: <strong>privacy@bikemaster.app</strong></p>

      <h2>9. Misure di Sicurezza</h2>
      <ul>
        <li>Crittografia password con bcrypt</li>
        <li>Token JWT con refresh automatico</li>
        <li>Rate limiting per protezione API</li>
        <li>HTTPS per tutte le comunicazioni</li>
        <li>Database con backup periodici</li>
        <li>Accesso ai dati minimo necessario (least privilege)</li>
      </ul>

      <h2>10. Cookie e Tecnologie Simili</h2>
      <p>
        Per informazioni dettagliate sui cookie, consulta la
        <RouterLink to="/cookies">
Cookie Policy
</RouterLink>.
      </p>

      <h2>11. Modifiche alla Presente Informativa</h2>
      <p>
        Eventuali modifiche saranno comunicate attraverso il servizio o via
        email agli utenti registrati. Si consiglia di consultare periodicamente
        questa pagina.
      </p>

      <h2>12. Autorità di Controllo</h2>
      <p>
        In caso di mancata risposta o insoddisfazione, è possibilepresentare
        reclamo al Garante per la protezione dei dati personali presso
        <a href="https://www.garanteprivacy.it"
target="_blank" rel="noopener">www.garanteprivacy.it</a>.
      </p>
    </div>

    <div class="cta-section">
      <RouterLink to="/" class="btn btn-primary">
        🏠 Torna all'Accedi
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
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
