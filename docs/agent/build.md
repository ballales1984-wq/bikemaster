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
3. **Eseguire dalla cartella del progetto** (evita il blocco della zona download):
   spostare l'exe fuori da `Downloads` se SAC lo blocca come file scaricato da internet.
