<template>
  <div class="legal-page">
    <div class="legal-header">
      <h1>Termini di Servizio</h1>
      <p class="last-updated">Ultimo aggiornamento: Giugno 2025</p>
    </div>

    <div class="legal-content">
      <h2>1. Accettazione dei Termini</h2>
      <p>
        Utilizzando BikeMaster, l'utente accetta integralmente i presenti
        Termini di Servizio. Se non si accettano i termini, si prega di non
        utilizzare il servizio.
      </p>

      <h2>2. Descrizione del Servizio</h2>
      <p>
        BikeMaster è un sistema di analisi intelligente delle performance
        ciclistiche che consente di:
      </p>
      <ul>
        <li>Importare file GPX e FIT di uscite ciclistiche</li>
        <li>Analizzare metriche di potenza, velocità, elevazione e calorie</li>
        <li>Ricevere consigli personalizzati tramite AI Coach</li>
        <li>Visualizzare percorsi su mappe interattive</li>
        <li>
          Sincronizzare attività con servizi terzi (Strava, Garmin, Google Fit)
        </li>
        <li>Tracciare uscite in tempo reale da dispositivo mobile</li>
      </ul>

      <h2>3. Account Utente</h2>
      <ul>
        <li>
          L'utente è responsabile della sicurezza delle proprie credenziali
        </li>
        <li>
          L'utente deve fornire informazioni accurate e aggiornate nel profilo
          atleta
        </li>
        <li>
          Ogni utente è responsabile di tutte le attività svolte tramite il
          proprio account
        </li>
        <li>È vietato condividere l'account con terzi non autorizzati</li>
      </ul>

      <h2>4. Dati e Contenuti dell'Utente</h2>
      <ul>
        <li>
          L'utente mantiene la proprietà di tutti i dati di attività caricati
        </li>
        <li>
          Concedendo una licenza limitata a BikeMaster per elaborare e
          visualizzare i dati
        </li>
        <li>
          I dati geolocalizzati sono trattati nel rispetto della Privacy Policy
        </li>
        <li>
          L'utente può esportare o cancellare i propri dati in qualsiasi momento
        </li>
      </ul>

      <h2>5. Uso Accettabile</h2>
      <p>È vietato:</p>
      <ul>
        <li>Utilizzare il servizio per attività illegali o non autorizzate</li>
        <li>Tentare di accedere a dati di altri utenti</li>
        <li>
          Eseguire scraping, crawling o uso automatizzato non autorizzato delle
          API
        </li>
        <li>
          Utilizzare il servizio per sovraccaricare i server con richieste
          eccessive
        </li>
        <li>Caricare contenuti dannosi, offensivi o illegali</li>
      </ul>

      <h2>6. Servizi di Terze Parti</h2>
      <p>
        BikeMaster si integra con servizi di terze parti (Strava, Garmin
        Connect, Google Fit). L'utilizzo di tali servizi è regolato dai
        rispettivi termini di servizio. BikeMaster non è responsabile per il
        funzionamento o l'accuratezza dei dati forniti da terze parti.
      </p>

      <h2>7. Proprietà Intellettuale</h2>
      <ul>
        <li>BikeMaster e il suo logo sono di proprietà del team di sviluppo</li>
        <li>
          Tutti i diritti sui contenuti generati automaticamente (mappe,
          analisi, report) rimangono all'utente
        </li>
        <li>
          Il codice sorgente è rilasciato sotto licenza MIT (vedi file LICENSE)
        </li>
      </ul>

      <h2>8. Limitazione di Responsabilità</h2>
      <p>BikeMaster è fornito "così com'è". Il team non garantisce:</p>
      <ul>
        <li>L'accuratezza delle metriche sportive calcolate</li>
        <li>L'assenza di errori o interruzioni del servizio</li>
        <li>La compatibilità con tutti i dispositivi e piattaforme GPS</li>
      </ul>
      <p>
        Il servizio non sostituisce consulenza medica o coaching professionale.
        L'utente è responsabile delle proprie attività fisiche.
      </p>

      <h2>9. Modifiche al Servizio</h2>
      <p>
        Ci riserviamo il diritto di modificare, sospendere o interrompere il
        servizio in qualsiasi momento, con o senza preavviso. Non saremo
        responsabili verso l'utente o terzi per eventuali modifiche, sospensioni
        o interruzioni.
      </p>

      <h2>10. Risoluzione</h2>
      <p>
        Ci riserviamo il diritto di sospendere o terminare l'accesso al servizio
        per qualsiasi utente che violi i presenti termini, a nostra esclusiva
        discrezione.
      </p>

      <h2>11. Legge Applicabile e Foro Competente</h2>
      <p>
        I presenti termini sono regolati dalla legislazione italiana. Per
        qualsiasi controversia sarà competente il foro del luogo di residenza
        del titolare del servizio.
      </p>

      <h2>12. Contatti</h2>
      <p>
        Per domande relative ai presenti termini:
        <a href="mailto:support@bikemaster.app">support@bikemaster.app</a>
      </p>

      <h2>13. Integrazione con Altre Policy</h2>
      <ul>
        <li>
          <RouterLink to="/privacy"> Privacy Policy </RouterLink>
        </li>
        <li>
          <RouterLink to="/cookies"> Cookie Policy </RouterLink>
        </li>
      </ul>
    </div>

    <div class="cta-section">
      <RouterLink
to="/" class="btn btn-primary"
>
        🏠 Torna all'Accedi
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
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
