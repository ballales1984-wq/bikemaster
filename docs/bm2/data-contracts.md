# BikeMaster 2.0 — Contratti Dati tra Engine (JSON)

**Versione:** Bozza 1.0
**Scopo:** definire il formato esatto degli oggetti scambiati da un Engine all'altro, così che ogni Engine possa essere sviluppato e testato in modo indipendente rispettando i confini fissati nel documento di architettura.

Convenzione: ogni contratto indica **Engine produttore** e **Engine consumatore/i** ammessi.

---

## 1. RawGPSPoint

**Produce:** Import Engine, Tracking Engine
**Consuma:** Data Layer

```json
{
  "type": "RawGPSPoint",
  "session_id": "sess_456",
  "timestamp": "2026-07-13T09:15:32Z",
  "latitude": 45.4064,
  "longitude": 11.8768,
  "altitude_m": 24.5,
  "sensors": {
    "heart_rate": 142,
    "power_w": 210,
    "cadence_rpm": 88
  },
  "source": "strava"
}
```

---

## 2. NormalizedMovementPoint

**Produce:** Measurement Engine
**Consuma:** Analysis Engine, Territory Engine

```json
{
  "type": "NormalizedMovementPoint",
  "session_id": "sess_456",
  "timestamp": "2026-07-13T09:15:32Z",
  "position": { "lat": 45.4064, "lon": 11.8768, "altitude_m": 24.5 },
  "movement": {
    "speed_ms": 12.0,
    "speed_kmh": 43.2,
    "acceleration_ms2": 0.4,
    "direction_deg": 187.5,
    "slope_pct": 3.2
  },
  "athlete": {
    "heart_rate": 142,
    "power_w": 210,
    "cadence_rpm": 88
  }
}
```

Nota: corrisponde alla struttura `MovementPoint` definita nel documento di architettura, sezione 6.1.

---

## 3. SessionSummary

**Produce:** Analysis Engine
**Consuma:** Knowledge Layer, Data Layer (per storicizzazione)

```json
{
  "type": "SessionSummary",
  "session_id": "sess_456",
  "athlete_id": "ath_1",
  "duration_moving_s": 5400,
  "duration_paused_s": 300,
  "distance_km": 42.3,
  "elevation_gain_m": 680,
  "avg_speed_kmh": 28.2,
  "max_speed_kmh": 54.1,
  "avg_hr": 138,
  "max_hr": 172,
  "avg_power_w": 195,
  "calories_kcal": 890,
  "trimp": 112.4,
  "zones": {
    "hr": { "z1_s": 300, "z2_s": 1800, "z3_s": 2400, "z4_s": 800, "z5_s": 100 },
    "power": { "z1_s": 400, "z2_s": 2000, "z3_s": 2200, "z4_s": 700, "z5_s": 100 }
  }
}
```

---

## 4. TerritorySegment

**Produce:** Territory Engine
**Consuma:** Knowledge Layer, AI Coach (in lettura tramite Knowledge Layer)

```json
{
  "type": "TerritorySegment",
  "segment_id": "seg_789",
  "geometry": {
    "type": "LineString",
    "coordinates": [[11.8768, 45.4064], [11.8790, 45.4102]]
  },
  "slope_avg_pct": 5.4,
  "slope_max_pct": 11.2,
  "length_m": 3200,
  "surface_type": "asfalto",
  "traffic_level": "medio",
  "difficulty_score": 62
}
```

Corrisponde a `WorldObject` (documento di architettura, sezione 6.2), specializzato per il caso "strada/segmento".

---

## 5. FitnessState / FatigueState / RecoveryState

**Produce:** Knowledge Layer
**Consuma:** AI Coach

```json
{
  "type": "AthleteKnowledgeState",
  "athlete_id": "ath_1",
  "date": "2026-07-13",
  "fitness_state": { "ctl": 68.4, "trend": "stabile" },
  "fatigue_state": { "atl": 74.1, "trend": "in_aumento" },
  "recovery_state": {
    "form": -5.7,
    "recupero_previsto_ore": 30,
    "confidenza": "media"
  },
  "generated_at": "2026-07-13T07:00:00Z"
}
```

---

## 6. RouteDifficulty

**Produce:** Knowledge Layer (a partire da TerritorySegment + condizioni meteo)
**Consuma:** AI Coach

```json
{
  "type": "RouteDifficulty",
  "segment_id": "seg_789",
  "score": 62,
  "fattori": {
    "pendenza": 0.7,
    "dislivello": 0.6,
    "lunghezza": 0.5,
    "fondo": 0.3,
    "meteo": 0.4
  }
}
```

---

## 7. PerformancePrediction

**Produce:** Knowledge Layer
**Consuma:** AI Coach

```json
{
  "type": "PerformancePrediction",
  "athlete_id": "ath_1",
  "segment_id": "seg_789",
  "predicted_time_min": 14.2,
  "predicted_avg_speed_kmh": 13.5,
  "condizioni_assunte": {
    "meteo": "vento_contrario_leggero",
    "peso_atleta_kg": 74,
    "potenza_sostenibile_w": 250
  }
}
```

---

## 8. CoachRequest / CoachResponse

**Produce (request):** client / utente, tramite AI Coach
**Produce (response):** AI Coach, a partire esclusivamente da oggetti del Knowledge Layer (mai da dati grezzi)

```json
{
  "type": "CoachRequest",
  "athlete_id": "ath_1",
  "question": "Sono pronto per la salita di sabato?"
}
```

```json
{
  "type": "CoachResponse",
  "answer": "In base al recupero stimato e alla difficoltà del percorso, sì, ma con margine ridotto.",
  "based_on": ["recovery_state", "route_difficulty", "performance_prediction"],
  "generated_at": "2026-07-13T09:20:00Z"
}
```

---

## 9. Regola di validazione

Ogni contratto è la superficie di confine tra due Engine. In fase di implementazione:

1. Ogni Engine valida in **ingresso** i contratti che riceve (schema JSON, tipi, range plausibili).
2. Nessun Engine produce un campo che non è di sua competenza (es. il Measurement Engine non deve mai popolare `fatigue_state`).
3. Ogni contratto ha un campo `type` esplicito per facilitare validazione automatica e versionamento futuro (es. `MovementPoint.v2`).
