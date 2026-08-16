# Sync Contract

BikeMaster è offline-first. Il sync tra device (SQLite locale) e hub cloud
(PostgreSQL su Render) è opzionale, controllato dall'utente, e non deve mai
interrompere il funzionamento locale.

## 1. Payload format

### ChangeDelta (push)

Ogni modifica locale viene impacchettata in un `ChangeDelta`:

```json
{
  "entity_type": "ride",
  "entity_id": 42,
  "operation": "update",
  "data": {
    "distance_km": 35.0,
    "duration_minutes": 90
  },
  "source": "device",
  "reliability_score": 1.0,
  "last_modified": "2026-08-16T08:30:00+00:00",
  "external_source": "strava",
  "external_id": "1001"
}
```

Campi:

| Campo | Tipo | Note |
|---|---|---|
| `entity_type` | string | `ride`, `athlete`, `chat_message`, `training_goal`, `planned_workout`, `fitness_state`, `calendar_event`, `poi` |
| `entity_id` | int | ID locale dell'entità |
| `operation` | string | `create`, `update`, `delete` |
| `data` | object | I campi modificati (solo quelli inviati, non l'intera riga) |
| `source` | string | `device`, `cloud`, `import` |
| `reliability_score` | float | 0.0–1.0, fiducia della sorgente |
| `last_modified` | ISO8601 | Timestamp della modifica |
| `external_source` | string | opzionale: `strava`, `garmin`, `wahoo` |
| `external_id` | string | opzionale: ID nella sorgente esterna |

### SyncCheckResult

```json
{
  "last_sync_ts": "2026-08-15T10:00:00+00:00",
  "server_changes_count": 3,
  "server_changes": [...],
  "server_version": "hub-0.1"
}
```

### SyncPushResult

```json
{
  "accepted": 2,
  "conflicts": [...],
  "errors": []
}
```

## 2. Conflict resolution strategy

Il sync usa una strategia a tre livelli:

1. **Affidabilità (`reliability_score`)**: vince la sorgente con score più alto.
   Soglia di autorità: `0.8`. Se una sorgente è ≥ 0.8 e l'altra no, la prima vince automaticamente.
2. **Tempo (`last_modified`)**: a parità di affidabilità, vince il timestamp più recente.
3. **Merge field-level**: se entrambi i campi sono uguali o uno è `null`, il merge è automatico.
   Se i campi differiscono e sono entrambi non-null, il conflitto è ambiguo e richiede
   revisione utente (`needs_user_review = true`).

Non esiste un "last-write-wins" globale; la risoluzione dipende sempre da
`reliability_score` + `last_modified` + merge field-level.

## 3. TTL

Il sync non usa TTL esplicito per i delta. I conflitti persistenti vengono
conservati in `sync_conflicts` finché non sono risolti o eliminati dal
meccanismo di rotazione (se implementato).

## 4. Autorità server-vs-client

- **Device**: autorità primaria per i dati generati localmente (ride, chat, note).
- **Cloud**: autorità primaria per i dati di configurazione condivisa (obiettivi,
  piani di allenamento).
- **Import esterni** (Strava/Garmin/Wahoo): affidabilità inferiore (0.6–0.7)
  rispetto ai dati manuali del device (1.0).

## 5. Semantica offline queue

Quando il device è offline:

1. Le modifiche locali vengono scritte su SQLite normalmente.
2. Lo stato `sync_entity_state` viene marcato `PENDING` o `LOCAL`.
3. Alla riconnessione, il servizio di sync recupera tutti gli stati `PENDING`/`LOCAL`,
  costruisce i `ChangeDelta` e li invia in batch a `/sync/push`.
4. Il server risponde con `accepted` + eventuali `conflicts`.
5. I conflitti vengono salvati in `sync_conflicts` e risolti automaticamente
   quando possibile, altrimenti richiesti all'utente.

## 6. Idempotenza

- **Push**: ogni `ChangeDelta` include `entity_id` + `last_modified`. Il server
  usa `ON CONFLICT` (PostgreSQL) o `INSERT OR REPLACE` (SQLite) per garantire
  che un delta ri-inviato non crei duplicati.
- **Pull**: le modifiche remote sono identificate da `cloud_id`. Se lo stesso
  `cloud_id` viene applicato due volte, l'operazione è sicura perché il merge
  è deterministico.
- **Entity state**: `upsert_entity_state` usa `UNIQUE(entity_type, entity_id)`
  per garantire idempotenza negli aggiornamenti di stato.

## 7. Entity directions

| Entity | Direction | Note |
|---|---|---|
| `ride` | PUSH | Le ride sono create localmente e pushate al cloud |
| `athlete` | BIDIRECTIONAL | Profilo atleta sincronizzato bidirezionalmente |
| `chat_message` | PUSH | La chat è principalmente locale |
| `training_goal` | PUSH | Gli obiettivi sono gestiti localmente |
| `planned_workout` | PUSH | I piani sono gestiti localmente |
| `fitness_state` | PUSH | Derivato localmente |
| `calendar_event` | PUSH | Gestito localmente |
| `poi` | PUSH | I POI sono creati localmente |

## 8. Endpoint

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/sync/check` | Verifica modifiche sul server since timestamp |
| POST | `/sync/push` | Invia delta locali al server |
| GET | `/sync/pull` | Ricevi modifiche remote since timestamp |
| GET | `/api/v1/sync/status` | Stato sync per l'utente corrente |
| PUT | `/api/v1/sync/settings` | Aggiorna impostazioni sync |
| POST | `/api/v1/sync/trigger` | Trigger manuale sync |
| GET | `/api/v1/sync/conflicts` | Lista conflitti aperti |
| POST | `/api/v1/sync/conflicts/{id}/resolve` | Risolvi conflitto |
