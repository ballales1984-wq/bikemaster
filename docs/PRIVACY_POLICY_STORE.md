# BikeMaster — Informativa sulla Privacy (per gli Store App)

_Ultimo aggiornamento: Luglio 2026_

Questa informativa descrive come l'app **BikeMaster** raccoglie, utilizza e
protegge i dati degli utenti. È predisposta per la pubblicazione negli store
(Google Play / Android) e integra l'informativa completa disponibile
all'interno dell'app (`/privacy`).

## 1. Titolare del trattamento

- **App:** BikeMaster — Cycling Performance Intelligence
- **Contatti privacy:** privacy@bikemaster.app

## 2. Dati raccolti

L'app raccoglie le seguenti categorie di dati:

- **Dati di account:** nome, email, password (memorizzata in forma
  crittografata con bcrypt).
- **Dati del profilo atleta:** età, peso, altezza e, se forniti
  volontariamente, dati relativi alla salute/fitness.
- **Dati di attività e salute:** tracciati GPS, velocità, altitudine,
  distanza, dislivello, frequenza cardiaca, potenza, cadenza, calorie.
- **Geolocalizzazione in tempo reale:** posizione GPS durante il
  tracciamento delle uscite da dispositivo mobile.
- **Dati di navigazione:** indirizzo IP, tipo di browser, sistema
  operativo, log.
- **Dati da servizi terzi:** attività provenienti da Strava, Garmin
  Connect e Google Fit, **solo previa autorizzazione OAuth2 dell'utente**.

## 3. Utilizzo dei dati

I dati sono utilizzati esclusivamente per:

- fornire il servizio di analisi delle performance ciclistiche;
- calcolare metriche (calorie, TSS, CTL/ATL/TSB) e generare mappe/report;
- erogare i consigli personalizzati dell'AI Coach;
- gestire autenticazione e account;
- sincronizzare attività con servizi terzi autorizzati;
- statistiche aggregate e anonimizzate per migliorare il servizio;
- sicurezza e protezione da accessi non autorizzati.

## 4. Base giuridica (GDPR)

- **Esecuzione del contratto** (Art. 6.1.b GDPR) per la fornitura del
  servizio.
- **Consenso** (Art. 6.1.a GDPR) per dati sanitari e geolocalizzazione in
  tempo reale.
- **Interesse legittimo** (Art. 6.1.f GDPR) per sicurezza e statistiche
  aggregate.

## 5. Condivisione con terze parti

I dati non sono mai ceduti a terzi a titolo oneroso. Possono essere
condivisi con:

- **Strava, Garmin Connect, Google Fit:** solo previa autorizzazione
  esplicita dell'utente.
- **Google Maps / OpenStreetMap:** per il rendering delle mappe.
- **Groq API / OpenAI API:** per l'AI Coach e la ricerca semantica
  (dati anonimizzati, nessun dato identificativo personale condiviso).

## 6. Geolocalizzazione

L'app richiede l'autorizzazione alla **localizzazione in primo piano**
durante il tracciamento GPS. La posizione è utilizzata per registrare il
percorso dell'uscita e non viene utilizzata per altri scopi né condivisa
senza consenso. L'utente può revocare il permesso in qualsiasi momento
dalle impostazioni del dispositivo.

## 7. Conservazione

- Dati di tracciamento GPS: fino all'eliminazione da parte dell'utente.
- Dati del profilo atleta: fino all'eliminazione dell'account.
- Token di accesso (JWT): per la durata della sessione.
- Token OAuth: fino a revoca esplicita.

## 8. Sicurezza

- Crittografia delle password (bcrypt).
- Token JWT con refresh automatico e comunicazioni HTTPS.
- Rate limiting e accesso ai dati secondo il principio di minimo necessario.
- Backup periodici del database.

## 9. Diritti dell'utente

Ai sensi degli Artt. 15–22 del GDPR, l'utente può in qualsiasi momento
accedere, rettificare, cancellare, limitare, opporsi al trattamento,
ottenere la portabilità dei dati e revocare il consenso scrivendo a
**privacy@bikemaster.app**. È inoltre possibile presentare reclamo al
Garante per la protezione dei dati personali
(https://www.garanteprivacy.it).

## 10. Modifiche

Eventuali modifiche saranno comunicate nell'app e, per gli utenti
registrati, via email. Si consiglia di consultare periodicamente questa
pagina.

---

_Informativa ridotta per gli store. Versione completa e aggiornata
disponibile all'interno dell'app e su https://bikemaster.app/privacy._
