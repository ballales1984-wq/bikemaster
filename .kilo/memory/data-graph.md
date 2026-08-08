# Data Graph — Grafo delle Relazioni

Grafo che traccia il viaggio dei dati: da dove nascono, come vengono trasformati,
dove vengono usati e cosa influenzano (§14, §15, §16, §25).

L'agente **RELATION ANALYZER** mantiene e aggiorna questo grafo.

## Tipi di relazione (§15)

| Tipo | Descrizione | Esempio |
|---|---|---|
| DEPENDS_ON | A dipende da B per funzionare | API dipende da DB |
| CALCULATED_FROM | A è calcolato da B, C | `calories` ← `weight`, `distance`, `duration` |
| CALLS | A chiama B (funzione) | `calculate_stats()` chiama `calc_ftp()` |
| READS | A legge B (variabile/sorgente) | `calculate_calories()` legge `weight` |
| WRITES | A scrive B | `save_ride()` scrive `rides.db` |
| TRANSFORMS | A trasforma B in C | parser GPX → `GPSPoint[]` |
| AGGREGATES | A aggrega B | `daily_stats` aggrega `rides` |
| FILTERS | A filtra B | `recent_rides` filtra `rides` per data |
| NORMALIZES | A normalizza B | `normalize_heart_rate()` |
| COMPARES | A confronta B | `compare_rides()` |
| INFLUENCES | A influenza B (causale) | `weight` influenza `calories` |

## Distinzione (§19, §49)

- **VERIFIED RELATION** — supportata da evidenza (test, log, trace).
- **HYPOTHESIZED RELATION** — ipotesi da validare. Non inventare formule
  non supportate.
- **CORRELATION ≠ CAUSATION** — una correlazione osservata nei dati non è
  causalità senza evidenza sufficiente.

## Schema di una entry

```
[VARIABILE/FUNZIONE]
  born:        sorgente (file:line)
  depends_on:  [elenco]
  calculated_from: [elenco]
  reads:       [elenco]
  writes:      [elenco]
  transforms:  [elenco]
  influences:  [catena di impatto]
  evidence:    [file:line, test, log]
  status:      VERIFIED | HYPOTHESIZED | OBSOLETE
  last_verified: ISO 8601
```

## Esempi (§16)

### Data Lineage — calories

```
dashboard.calories
  ↓ READS
stats.calories
  ↓ CALCULATED_FROM
StatsService.calculate_calories()
  ↓ CALLS
  weight, distance, duration
  ↓ READS
weight (db: athlete.weight_kg)
  ↓ READS
database (athlete_profile / rides.db)
```

### Impatto — weight (§17)

```
weight
  → calories          (CALCULATED_FROM)
  → energy_balance    (CALCULATED_FROM)
  → fatigue           (INFLUENCES)
  → training_score    (INFLUENCES)
  → recommendation    (INFLUENCES)
```

> La modifica a `weight` potrebbe propagarsi a queste componenti.

### Relazione matematica (§19)

```
speed = distance / time                  [VERIFIED] (frontend/src/composables/useRides.ts:44)
calories = weight × distance × coeff     [VERIFIED] (bike_analyzer/analytics/calories.py:12)
ftp = weighted_avg(rides.power, decay)   [VERIFIED] (bm2/algorithms/ftp.py)
```

## Relazioni temporali (§20)

```
A(t)
  → B(t+1)     [DEPENDS_ON/temporal]
  → C(t+2)     [INFLUENCES/temporal]
```

Identifica: precedenze, dipendenze temporali, aggiornamenti, ritardi,
effetti nel tempo.

(nuove relazioni vengono aggiunte qui dal RELATION ANALYZER)
