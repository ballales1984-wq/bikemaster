# Hub Module — Cloud Sync & Community

Il modulo **hub** è il backend cloud opzionale di BikeMaster, separato dal modulo locale.

## Quando usarlo

- Sync bidirezionale tra device e cloud.
- Condivisione dati multi-utente / community.
- Backup centralizzato.

## Avvio

```bash
python main.py hub --port 8001
```

Richiede `DATABASE_URL` configurato per PostgreSQL. Vedi `docs/archive/configuration.md` per le variabili d'ambiente specifiche.

## Endpoint

- `/api/v1/auth/*` — login, register, Google OAuth, refresh token
- `/api/v1/admin/*` — stats, backup, audit logs, reset demo
- `/api/v1/knowledge/*` — knowledge base search e stats
- `/api/v1/sync/*` — push/pull sincronizzazione con device locali

## Frontend

Il frontend supporta il modulo hub tramite `BackendMode.hub` in `frontend/src/utils/backend-config.ts`. Configurare `VITE_HUB_API_BASE` per puntare all'istanza hub.
