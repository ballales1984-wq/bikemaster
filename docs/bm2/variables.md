# BikeMaster 2.0 — Dizionario delle Variabili

**Versione:** 1.0 (bozza)
**Ambito:** motore `bike_analyzer/bm2/` (Deluxe Simulation Engine)
**Scopo:** il "vocabolario" del sistema. Per ogni variabile: unità canonica interna,
stato reale nel codice, dove vive, e le variabili derivate che alimenta.

> Questo documento è **ancorato al codice esistente**, non alla sola visione.
> È il ponte tra la bozza di architettura (`ROADMAP.md`,
> `ROADMAP.md` Track D) e l'implementazione reale in `bm2/`.

---

## 0. Come leggere le tabelle

**Colonna "Stato":**
- ✅ **presente** — esiste già un campo/algoritmo dedicato nel codice
- 🟡 **parziale** — esiste in forma limitata (solo via `extra` dict, solo output secondario, non persistito)
- ❌ **gap** — nella visione ma NON ancora modellato

**Unità canoniche interne** (fonte: `bm2/units.py`, `_CANONICAL`):

| Dimensione | Unità canonica | Dimensione | Unità canonica |
|---|---|---|---|
| massa | `kg` | pendenza | `%` |
| lunghezza | `m` | angolo | `deg` |
| velocità | `m/s` | temperatura | `°C` |
| tempo | `s` | pressione | `Pa` |
| energia | `J` | densità | `kg/m^3` |
| potenza | `W` | coppia | `Nm` |
| frequenza | `bpm` | | |

Ogni grandezza nel sistema è una `Quantity` = **valore + unità + precisione + fonte + timestamp**
(`bm2/units.py:45`). Le conversioni (kg/lb, km/h/mph, °C/°F, %/gradi…) sono in `UnitRegistry`.

---

## 1. Dominio TEMPO

Competenza: `TransformerEngine.time` + `Activity.metrics()` (`bm2/models.py:223`).

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| timestamp punto | ISO 8601 → `s` | ✅ | `GeoPoint.timestamp` |
| durata sessione | `s` | ✅ | `Activity.metrics()["duration_s"]` |
| ora inizio / fine | ISO 8601 | 🟡 | derivabile da `points[0/-1].timestamp` | non esposto come campo |
| tempo movimento | `s` | ❌ | — | serve soglia velocità > 0 |
| tempo pausa | `s` | ❌ | — | complementare a movimento |
| tempo recupero (necessario) | `h` | ✅ (derivata) | `FatigueModel` → `details["recovery_hours"]` |
| giorno settimana / stagione | enum | ❌ | — | feature per pattern storici |

---

## 2. Dominio POSIZIONE / GPS

Competenza: `GeoPoint` (`bm2/transformer.py`) + `TransformerEngine.geo`.

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| latitudine | `deg` | ✅ | `GeoPoint.lat` |
| longitudine | `deg` | ✅ | `GeoPoint.lon` |
| altitudine / quota | `m` | ✅ | `GeoPoint.altitude` |
| distanza | `m` | ✅ | `metrics()["distance_m"]` |
| dislivello positivo | `m` | ✅ | `metrics()["gain_m"]` |
| dislivello negativo | `m` | ✅ | `metrics()["loss_m"]` |
| traccia percorso | lista `GeoPoint` | ✅ | `Activity.points` |
| direzione / bearing | `deg` | ❌ | — | non calcolato da `track_metrics` |
| velocità GPS | `m/s` | ✅ | `GeoPoint.speed` (opzionale) |
| quota iniziale / finale | `m` | 🟡 | derivabile da `points[0/-1].altitude` | non esposto |

---

## 3. Dominio MOVIMENTO

Competenza: `MovementModel` (`bm2/algorithms/movement.py`).

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| velocità media | `m/s` | ✅ | `MovementModel._compute` |
| velocità massima | `m/s` | ✅ | `MovementModel` → `details["max_speed_ms"]` |
| velocità istantanea | `m/s` | ✅ | `GeoPoint.speed` per punto |
| accelerazione (max) | `m/s²` | 🟡 | `details["max_accel_ms2"]` | solo massima, non serie |
| decelerazione | `m/s²` | ❌ | — | non distinta dall'accelerazione |
| cambi ritmo | conteggio | ❌ | — | serve analisi varianza velocità |
| fermate | conteggio | ❌ | — | serve rilevamento v≈0 |

---

## 4. Dominio TERRITORIO

Competenza: `WorldObject` (`bm2/models.py:324`) + `RouteDifficultyModel`.

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| pendenza media | `%` | ✅ | `WorldObject.avg_slope_percent` / `metrics()["avg_slope_percent"]` |
| pendenza istantanea | `%` | ❌ | — | serve grade punto-punto |
| pendenza massima | `%` | ❌ | — |
| lunghezza salita | `m` | 🟡 | derivabile da `gain_m` | non segmentato |
| tipo strada / fondo | enum | ✅ | `WorldObject.surface` (`asphalt/gravel/dirt/trail`) |
| indice rugosità | adim. | ✅ | `WorldObject.roughness_index` + `ROUGHNESS_FACTOR` |
| curvatura percorso | `1/m` | ❌ | — |
| difficoltà segmento | score 0-100 | ✅ (derivata) | `RouteDifficultyModel` |

---

## 5. Dominio ATLETA

Competenza: `Athlete` (`bm2/models.py:57`). Suddiviso nei sotto-domini della bozza.

### 5.1 Identità e profilo
| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| età | anni | ✅ | `Athlete.age` |
| altezza | `m` | ✅ | `Athlete.height_m` |
| peso | `kg` | ✅ | `Athlete.weight_kg` (obbligatorio) |
| livello esperienza | enum | ✅ | `Athlete.experience_level` (`Beginner/Intermediate/Advanced/Elite`) |
| sesso | enum | ❌ | — | serve per modelli fisiologici |
| obiettivi (dimagr./perf./salute/gara) | enum | ❌ | — | guida la personalizzazione |
| anni di bici / storico esperienza | anni | ❌ | — |

### 5.2 Corpo e composizione
| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| peso | `kg` | ✅ | `Athlete.weight_kg` |
| massa grassa | `%` o `kg` | ❌ | — |
| massa muscolare | `kg` | ❌ | — |
| circonferenze | `cm` | ❌ | — |
| idratazione | `%` | ❌ | — |

### 5.3 Stato quotidiano (readiness)
| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| FC riposo | `bpm` | ✅ | `Athlete.resting_hr_bpm` |
| ore sonno | `h` | 🟡 | `RecoveryModel` via `extra["sleep_hours"]` | **non persistito su `Athlete`** |
| HRV (rMSSD) | `ms` | 🟡 | `RecoveryModel` via `extra["hrv_rmssd"]` + `baseline_hrv` | non persistito |
| qualità sonno | score | ❌ | — |
| stress percepito | score | ❌ | — |
| dolori / segnali rischio | enum | ❌ | — |

### 5.4 Prestazione sportiva
| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| frequenza cardiaca | `bpm` | ✅ | `GeoPoint.heart_rate` per punto |
| FC massima | `bpm` | ✅ | `Athlete.max_hr_bpm` |
| potenza | `W` | ✅ | `GeoPoint.power` + `PowerModel` |
| cadenza | `rpm` | ✅ | `GeoPoint.cadence` |
| velocità | `m/s` | ✅ | vedi §3 |
| FTP | `W` | ✅ | `Athlete.ftp_w` |
| VO2max | `ml/kg/min` | ❌ | — | citato nella visione, non modellato |
| zone cardio | enum | ❌ | — | derivabili da `max_hr_bpm` |
| CTL / ATL / TSB | score | ✅ | `Athlete.ctl/atl/tsb_stress_score` + `TrainingLoadModel` |

---

## 6. Dominio AMBIENTE

Competenza: `WorldObject` (`bm2/models.py:324`).

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| temperatura | `°C` | ✅ | `WorldObject.temperature_c` |
| vento | `m/s` | ✅ | `WorldObject.wind_speed_ms` (usato in Energy/Power) |
| umidità | `%` | ❌ | — |
| pressione | `Pa` | ❌ | — (unità già supportata in `UnitRegistry`) |
| meteo (condizione) | enum | ❌ | — |
| sole / ombra, luce/buio | enum | ❌ | — |
| qualità aria | indice | ❌ | — |

---

## 7. Dominio BICI

Competenza: `Bike` (`bm2/models.py:157`).

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| peso bici | `kg` | ✅ | `Bike.weight_kg` (obbligatorio) |
| tipo / categoria | enum | ✅ | `Bike.category` (`road/gravel/mtb/other`) |
| Crr (resistenza rotolamento) | adim. | ✅ | `Bike.crr` |
| CdA (area aerodinamica) | `m²` | ✅ | `Bike.cda` |
| efficienza trasmissione | adim. | ✅ | `Bike.drivetrain_efficiency` |
| rapporto (gear ratio) | adim. | ✅ | `Bike.gear_ratio` (opzionale) |
| ruote / copertoni | testo | ❌ | — |
| manutenzione / km componenti | `km` | ❌ | — |

---

## 8. Dominio STORICO

Competenza: oggi **solo** via `extra["activity_history"]` in `TrainingLoadModel`.

| Variabile | Unità canonica | Stato | Dove nel codice | Note |
|---|---|:--:|---|---|
| storico attività (per TSS) | lista | 🟡 | `TrainingLoadModel` via `extra["activity_history"]` | non un modello di dominio |
| numero uscite | conteggio | ❌ | — |
| km totali | `m` | ❌ | — |
| ore totali | `s` | ❌ | — |
| dislivello totale | `m` | ❌ | — |
| record personali | vari | ❌ | — |
| trend / progressi | serie | ❌ | — |
| recuperi personali storici | `h` | ❌ | — | chiave per "Persona A 24h / B 48h" |

---

## 9. Variabili DERIVATE e STATI INTERPRETATI

Questa è la parte "il valore è nei collegamenti". Ogni algoritmo dichiara i suoi
`required_inputs` e produce un `ModelResult` (**valore + formula + dati usati +
precisione + confidence + fonte**, `bm2/algorithms/base.py:24`).

| Stato / derivata | Algoritmo | Unità | Input richiesti (`required_inputs`) | Stato input |
|---|---|:--:|---|---|
| velocità/accelerazione | `MovementModel` | `m/s` | gps_points, distanza, durata | ✅ tutti |
| consumo energetico | `EnergyModel` | `kcal` | massa_totale, velocità, pendenza, durata, crr, cda | ✅ tutti |
| potenza | `PowerModel` | `W` | ftp, massa_totale, pendenza, crr, cda, efficienza | ✅ tutti |
| **FatigueState** | `FatigueModel` | score 0-10 | durata, intensità, velocità, dislivello, peso | ✅ tutti (+ `recovery_hours`) |
| **RecoveryState** (readiness) | `RecoveryModel` | score 0-100 | fatica, **sonno_ore**, **hrv** | 🟡 sonno/hrv solo via `extra` |
| **PerformancePrediction** | `PerformanceModel` | score 0-120 | velocità_media, experience_level | ✅ tutti |
| **RouteDifficulty** | `RouteDifficultyModel` | score 0-100 | distanza, dislivello, pendenza, rugosità, capacità_atleta | ✅ tutti |
| carico allenamento | `TrainingLoadModel` | TSS/CTL/ATL/TSB | ftp, **storico_attivita** | 🟡 storico solo via `extra` |
| nutrizione | `NutritionModel` | g / L | durata, intensità, massa_corpo | ✅ tutti |

**Knowledge Layer** (`bm2/knowledge.py`): `KnowledgeEngine.explain()` trasforma i
`ModelResult` sopra in `Insight` (concept + detail + severity) per l'AI Coach —
esattamente il passaggio "numeri → concetti" della bozza.

### 9.1 Catena delle dipendenze reali (chi legge chi)

```
FatigueModel ──► RecoveryModel (usa il fatigue score)
FatigueModel ──► NutritionModel (usa intensity_factor)
EnergyModel  ──► NutritionModel (usa kcal)
tutti ───────► KnowledgeEngine.explain() ──► Insight ──► AI Coach
```

---

## 10. Sintesi dei GAP prioritari

Variabili della visione **non ancora modellate**, raggruppate per valore/sforzo:

**Alto valore, basso sforzo (campi mancanti su dataclass esistenti):**
1. `Athlete`: `sex`, `vo2max`, e **persistere** `sleep_hours` / `hrv` / `sleep_quality` / `perceived_stress` (oggi solo via `extra`).
2. `WorldObject`: `humidity`, `pressure`, `weather`, `air_quality`.
3. `Bike`: `wheels`, `tires`, `maintenance_km` (per componente).

**Medio valore, medio sforzo (nuove derivate):**
4. Movimento: `bearing`, decelerazione, cambi ritmo, fermate.
5. Territorio: pendenza istantanea/max, curvatura, segmentazione salite.
6. Zone cardio da `max_hr_bpm`.

**Alto valore, alto sforzo (nuovo dominio):**
7. **Modello STORICO** come dominio di prima classe (uscite, totali, record, trend,
   recuperi personali) — è il substrato dell'apprendimento "Persona A 24h / B 48h".
8. Composizione corporea (massa grassa/muscolare, circonferenze, idratazione).

---

*Documento di lavoro. Aggiornare quando i gap vengono chiusi (spostare le righe da ❌/🟡 a ✅ con il riferimento al file).*
