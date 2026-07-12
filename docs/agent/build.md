# Build

## Windows — problema EPERM

`vite build` su Windows può fallire con `EPERM` per colpa del lock di Windows Defender / Antivirus. Il lock colpisce sia i file generati (`dist/registerSW.js`) sia i file sorgente appena riscritti (es. `src/components/CalendarPanel.vue`) durante la trasformazione di Rollup/PWA. Sintomi tipici: `EPERM, Permission denied` o `EPERM: operation not permitted, realpath '<file>'`.

Mitigazioni applicate/consigliate:
- **Wrapper di retry**: `frontend/scripts/build.mjs` esegue `vite build --emptyOutDir` e, in caso di `EPERM`, ripulisce `dist` e ritenta fino a 3 volte (attesa 4s). `package.json` deve puntare `build` a questo script.
- **Esclusione Defender** (richiede admin): `Add-MpPreference -ExclusionPath "<repo>\frontend"` — risolve alla radice i lock persistenti.
- **Alternativa**: `vite build --emptyOutDir` (svuota `dist` prima di scrivere).

Se anche il retry fallisce in modo persistente, il file è bloccato a livello OS: servono i permessi admin per l'esclusione, oppure attendere il rilascio del lock.
