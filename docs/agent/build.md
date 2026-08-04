# Build

## Windows — problema EPERM

`vite build` su Windows può fallire con `EPERM` per colpa del lock di Windows Defender / Antivirus. Il lock colpisce sia i file generati (`dist/registerSW.js`) sia i file sorgente appena riscritti (es. `src/components/CalendarPanel.vue`) durante la trasformazione di Rollup/PWA. Sintomi tipici: `EPERM, Permission denied` o `EPERM: operation not permitted, realpath '<file>'`.

Mitigazioni applicate/consigliate:
- **Wrapper di retry**: `frontend/scripts/build.mjs` esegue `vite build --emptyOutDir` e, in caso di `EPERM`, ripulisce `dist` e ritenta fino a 3 volte (attesa 4s). `package.json` deve puntare `build` a questo script.
- **Esclusione Defender** (richiede admin): `Add-MpPreference -ExclusionPath "<repo>\frontend"` — risolve alla radice i lock persistenti.
- **Alternativa**: `vite build --emptyOutDir` (svuota `dist` prima di scrivere).

Se anche il retry fallisce in modo persistente, il file è bloccato a livello OS: servono i permessi admin per l'esclusione, oppure attendere il rilascio del lock.

## Windows — Smart App Control block (unsigned .exe)

Il build Tauri produce `bikemaster-desktop.exe` **non firmato**. Windows Smart App
Control (SAC), attivo per default su Windows 10/11, blocca gli eseguibili non firmati,
mostrando il popup "Controllo app intelligente" con parte dell'app bloccata.

### Soluzione 1 — Release firmata (produzione)

Le build di GitHub Release ora supportano la firma Windows. Impostare due secret
su GitHub (`Settings → Secrets and variables → Actions`):

- `WINDOWS_CERTIFICATE` — certificato PKCS#12 (.pfx) codificato in base64
- `WINDOWS_CERTIFICATE_PASSWORD` — password del certificato
- `WINDOWS_TIMESTAMP_SERVER` — (opzionale) server timestamp RFC 3161

Il workflow `tauri-release.yml` inietta automaticamente questi valori in
`tauri-apps/tauri-action@v2`, che firma l'exe durante il build.

Per ottenere un certificato:
- **Gratuito (30/90 giorni)**: ZeroSSL / ssl.com offrono certificati code-signing
  via GitHub Actions.
- **A pagamento**: DigiCert, Sectigo, GoDaddy.

### Soluzione 2 — Sviluppo locale (workaround temporaneo)

Per le build locali non firmate (`npm run tauri build` → `target/release/*.exe`):

1. **Passare Smart App Control in modalità "Controllo"** (audit mode — avverte ma non blocca):
   - `Impostazioni → Sicurezza di Windows → Protezione da virus e minacce → Gestisci impostazioni protezione app e browser → Controllo app intelligente → Imposta su "Off"` (o usa PowerShell come amministratore):
   - `Set-SmartAppControlConfig -Mode AuditMode` (richiede restart)
2. **Aggiungere esclusione al file .exe**:
   - `Impostazioni → Sicurezza di Windows → Protezione da virus e minacce → Impostazioni protezione -> Esclusioni → Aggiungi o rimuovi esclusioni → Cartella/file` → selezionare `frontend\target\release\bikemaster-desktop.exe`
   3. **Firmare l'exe con signtool** (alternativa alla whitelist):
      - Generare un certificato auto-firmato: `pwsh scripts/sign-windows.ps1 -GenerateCert`
      - Firmare: `pwsh scripts/sign-windows.ps1` (firna automaticamente `.exe`, `.msi`, `.nsis` in `target/release/`)
      - Verificare: `signtool verify /pa /v frontend\src-tauri\target\release\bikemaster-desktop.exe`
      - **Importante**: un certificato auto-firmato NON è considerato attendibile da SAC. Serve un certificato emesso da CA (ZeroSSL, DigiCert, Sectigo) per passare il blocco. Usare il cert auto-firmato solo per verificare che la pipeline di firma funzioni.

## Render Deploy — timeout durante lo startup

Il deploy su Render potrebbe far scadere il timeout di health check (9.5 minuti
per il piano gratuito) se il server impiega troppo a mettersi in ascolto.

### Causa
Le migrazioni Alembic (PostgreSQL) venivano eseguite **sintopicamente** durante
lo startup del lifespan FastAPI, bloccando uvicorn da accettare connessioni per
15+ minuti. Inoltre, `init_async_db()` creava 25 tabelle PostgreSQL in modo
sincrono.

### Fix applicato
1. **`render.yaml`**: `startCommand` semplificato a `python main.py api --port $PORT`
   (rimosso il blocco sincrono `run_migrations_on_startup` precedentemente aggiunto).
2. **`app_factory.py` lifespan**: migrazioni e `init_async_db()` ora girano come
   `asyncio.create_task()` (fire-and-forget) con riferimenti salvati in
   `app.state._bg_tasks` per evitare garbage collection.
3. **`/api/v1/health`** restituisce una risposta statica (`{"status": "ok"}`)
   che non richiede database — il server passa il health check immediatamente.
4. **Dockerfile**: `RUN echo "cachebust:...-$(date -u +%s)" > /cache-bust`
   forzato prima dei `COPY bike_analyzer` per invalidare il build cache di Docker
   e garantire che le modifiche al codice vengano incluse nel build successivo.

### Verifica nei log Render
Cercare questi messaggi di log (in ordine):
1. `Migrations scheduled as background task`
2. `Async DB init scheduled as background task`
3. `Lifespan startup complete — uvicorn now accepting connections`
4. `Detected service running on port <PORT>`

Se il passo 3 appare entro ~2-3 minuti dal deploy start, il server è pronto.
