# Monitoring

## Rate limiting

- `bike_analyzer/backend/rate_limiter.py` espone `limiter` (slowapi) con chiave `get_limiter_key` (rispetta `X-Forwarded-For` dai proxy trusted).
- Già cablato sulle route di auth per prevenire brute force:
  - `POST /api/v1/auth/login` → `5/minute` (routes.py:302)
  - `POST /api/v1/auth/register` → `3/minute` (routes.py:417)
- Requisito slowapi: la route decorata deve avere `request: Request` come primo parametro (entrambe le route lo soddisfano).
- Altri endpoint limitati: OAuth Google (`10/minute`), `/api/v1/rides` (`10/minute`), ecc. Cercare `@limiter.limit` in `routes.py` per l'elenco completo.

## Redis su Render (free plan) — WARNING ATTESO, NON UN BUG

- L'istanza Redis su Render è su **piano free** ed è una connessione **solo demo** (usata per verificare la connettività, non per produzione).
- Sintomo atteso nei log di avvio del web service: `WARNING bike_analyzer.backend.redis_client Redis unavailable: Error 111 connecting to red-<hash>:6379. Connection refused. — cache disabled`
- `Error 111` / `Connection refused` significa: l'host Redis è stato risolto e raggiunto (DNS/region OK) ma niente ascolta sulla 6379 perché l'istanza free è in pausa/spenta per inattività. NON è un errore DNS né mismatch di region.
- L'app **degrada con grazie** (`redis_client.py` ritorna `None`, logga `cache disabled`): il servizio va `live` comunque, solo senza cache/rate-limiting Redis. Il WARNING è atteso e non blocca il deploy.
- `REDIS_URL` è l'**Internal Redis URL** (`redis://red-<hash>:6379`, host senza `.render.com`), impostato manualmente nella tab *Environment* del web service.
- Se il WARNING persiste: controllare stato del servizio Redis nel dashboard (Live/Paused) e svegliarlo; verificare che web service e Redis siano nella stessa region; NON usare l'External URL.
