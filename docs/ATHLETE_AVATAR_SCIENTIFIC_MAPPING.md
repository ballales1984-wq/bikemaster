# Base Scientifica — AthleteAvatarPanel

## Documento di progetto per il mapping fisiologico del manichino atleta

**Componente**: `frontend/src/components/AthleteAvatarPanel.vue`  
**Motore**: `bike_analyzer/backend/analytics/athlete_state/`  
**Stato**: Read-only, nessuna modifica al codice esistente.  
**Data**: 2026-07-20

---

## 1. Giustificazione fisiologica per area corporea

Il manichino umano non è una mappa arbitraria: ogni zona deve rappresentare un sistema fisiologico o metabolico con un significato clinico/sportivo riconoscibile. La scelta delle sei aree (head, neck, chest, core, arms, legs) rispetta la topografia neuro-funzionale usata in medicina dello sport e nella valutazione del carico ciclistico.

| Zona | Sistema fisiologico rappresentato | Motivazione scientifica |
|------|----------------------------------|-------------------------|
| **Head** (testa) | **Sistema nervoso centrale (SNC) + recupero cognitivo** | La readiness è lo stato aggregato del SNC: la capacità di concentrazione, la percezione dello sforzo (RPE), la coordinazione e la reattività. In ciclismo, un basso livello di readiness si manifesta prima di tutto come stanchezza mentale, difficoltà di concentrazione e sovra-stimolazione del sistema nervoso simpatico. La letteratura sportiva usa la "readiness" come proxy dello stato del SNC (McLean et al., 2023; Appenzeller-Herzog et al., 2022). |
| **Neck** (collo) | **Tensione muscolare + sistema autonomo (tono simpatico/parasimpatico)** | Il collo è il punto in cui si manifesta la tensione muscolare da affaticamento posturale e da stress autonomico. In ciclismo, una posizione aerodinamica prolungata carica i muscoli del collo (trapezio, sternocleidomastoideo). Un fatigue score elevato indica iper-attività simpatica e accumulo di tensioni miofasciali che riducono il recupero notturno. La FC variabilità (HRV) — non ancora disponibile nel backend — è un biomarker diretto del tono autonomico. |
| **Chest** (torace) | **Sistema cardiovascolare + fitness aerobica (CTL)** | Il CTL (Chronic Training Load) è l'EWMA 42 giorni del carico. Rappresenta la **fitness aerobica strutturale**: la capacità del cuore, dei polmoni e del sistema cardiovascolare di trasportare ossigeno. In ciclismo, il CTL è il miglior predittore della performance di endurance. Il torace è la metafora visiva corretta perché rappresenta il motore cardiopolmonare. |
| **Core** (addome) | **Stabilità neuromuscolare + acute workload ratio (ACWR)** | L'ACWR (Acute:Chronic Workload Ratio) misura il rapporto tra carico recente e carico strutturale. Rappresenta la **stabilità** del sistema muscolo-scheletrico: un ACWR > 1.3 indica che il carico acuto sta crescendo troppo velocemente rispetto alla base cronica, aumentando il rischio di infortunio muscolare/tendineo. L'addome (core) è il centro di gravità e stabilità del ciclista: un core instabile (ACWR sbilanciato) si traduce in perdita di efficienza pedalata e in sovraccarichi localizzati. |
| **Arms** (braccia) | **Fatica acuta (ATL) + affaticamento neuromuscolare** | L'ATL (Acute Training Load) è l'EWMA 7 giorni del carico. Rappresenta la **fatica acuta accumulata**: il sistema neuromuscolare è sotto stress per sforzi recenti. Le braccia sono coinvolte in modo massivo nel ciclismo (sostegno del peso, controllo della bici, frenate). Un ATL elevato si manifesta come tensione nelle braccia, crampi e perdita di sensibilità. |
| **Legs** (gambe) | **Forma corrente (TSB) + potenza specifica** | Il TSB (Training Stress Balance = CTL - ATL) misura la **forma corrente**: quanto l'atleta è "fresco" rispetto alla sua fitness. Le gambe sono il motore del ciclista: un TSB elevato significa gambe fresche e pronte per lo sforzo; un TSB negativo indica gambe cariche, con domande di recruiting motorio più alte e rischio di strappi/crampi. |

---

## 2. Proposta di metriche per zona, soglie e colori

### 2.1 Head — Recupero cognitivo / Readiness

**Metrica primaria**: `readiness` (0-100)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | >= 70 | Verde brillante | `#00ffcc` | Readiness > 70: il SNC è recuperato, prontezza cognitiva ottimale. Corrisponde a TSB > 5 e fatigue_score < 4. |
| WARNING | 40-69 | Ambra | `#ffb800` | Readiness 40-69: deficit cognitivo lieve-moderato. L'atleta percepisce fatica mentale, tempi di reazione rallentati. |
| DANGER | < 40 | Rosso | `#ff3366` | Readiness < 40: deficit cognitivo severo. Rischio di errori di guida, scarsa valutazione del rischio. |

**Logica**: La readiness è calcolata nel backend con una formula composita (TSB, fatigue_score, ACWR). Le soglie 70/40 sono coerenti con le soglie usate in `compute_risk_level()` e `compute_recommendation()` del backend.

### 2.2 Neck — Tensione muscolare / Fatigue Score

**Metrica primaria**: `fatigue_score` (0-10)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | <= 4 | Verde brillante | `#00ffcc` | Fatigue score <= 4: affaticamento muscolare/neuromuscolare lieve. Nessuna tensione patologica. |
| WARNING | 5-7 | Ambra | `#ffb800` | Fatigue score 5-7: affaticamento moderato. Tensione muscolare significativa, possibile irrigidimento cervicale in posizione aerodinamica. |
| DANGER | >= 8 | Rosso | `#ff3366` | Fatigue score >= 8: affaticamento elevato. Rischio di contratture, riduzione della ROM cervicale, impatto sul recupero notturno. |

**Logica**: Il backend usa fatigue_score >= 7 come soglia di warning e >= 8 come high/block. La soglia OK è stata abbassata a 4 per catturare meglio la zona di "pre-allarme".

### 2.3 Chest — Fitness aerobica / CTL

**Metrica primaria**: `ctl` (Chronic Training Load)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | >= 60 | Verde brillante | `#00ffcc` | CTL >= 60: fitness aerobica solida. L'atleta ha una base cronica sufficiente per sostenere volumi elevati. Valori tipici per amatori: 40-80; per elite: 100+. |
| WARNING | 30-59 | Ambra | `#ffb800` | CTL 30-59: fitness aerobica in costruzione o in fase di manutenzione. L'atleta può sostenere sforzi medio-lunghi ma non ha margine per aumenti bruschi. |
| DANGER | < 30 | Rosso | `#ff3366` | CTL < 30: fitness aerobica insufficiente per carichi da ciclismo strutturato. Rischio di infortunio se si aumenta troppo velocemente. |

**Logica**: Le soglie sono derivate dai benchmark del modello Banister (CTL tipico per amatori: 40-70). La soglia OK 60 separa gli atleti con base solida da quelli in costruzione.

### 2.4 Core — Stabilità del carico / ACWR

**Metrica primaria**: `acwr` (Acute:Chronic Workload Ratio)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | 0.8 - 1.3 | Verde brillante | `#00ffcc` | ACWR nella "sweet spot" della ricerca (Gabbett, 2016; Hulin et al., 2016). Rapporto tra carico acuto e cronico ottimale per adattamento senza sovraccarico. |
| WARNING | 0.5-0.79 o 1.31-1.5 | Ambra | `#ffb800` | ACWR < 0.8: detraining (carico acuto troppo basso rispetto alla base). ACWR 1.31-1.5: carico acuto crescente, rischio moderato di infortunio da sovraccarico. |
| DANGER | < 0.5 o > 1.5 | Rosso | `#ff3366` | ACWR < 0.5: detraining marcato (fitness in calo rapido). ACWR > 1.5: rischio alto di infortunio muscolare/tendineo (Blanch & Gabbett, 2016). Il backend già usa ACWR > 1.5 come high risk. |

**Logica**: La letteratura scientifica identifica la finestra 0.8-1.3 come zona di sicurezza. ACWR < 0.5 indica che l'atleta non sta mantenendo il livello di carico necessario per la sua base cronica.

### 2.5 Arms — Fatica acuta / ATL

**Metrica primaria**: `atl` (Acute Training Load)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | <= 60 | Verde brillante | `#00ffcc` | ATL <= 60: fatica acuta contenuta. Il sistema neuromuscolare ha risorse per rispondere a stimoli aggiuntivi. |
| WARNING | 61-85 | Ambra | `#ffb800` | ATL 61-85: fatica acuta moderata. L'atleta percepisce affaticamento nelle braccia, rigidità, possibile riduzione della forza esplosiva. |
| DANGER | > 85 | Rosso | `#ff3366` | ATL > 85: fatica acuta elevata. Il sistema neuromuscolare è in debito di recupero. Rischio di crampi, perdita di sensibilità, compromissione della tecnica di guida. |

**Logica**: Le soglie sono proporzionali al CTL: un ATL > CTL * 1.3 è la condizione di overtraining risk usata nel backend. ATL > 85 è un valore assoluto che, per un amatore con CTL ~60, corrisponde esattamente a 1.41x.

### 2.6 Legs — Forma corrente / TSB

**Metrica primaria**: `tsb` (Training Stress Balance = CTL - ATL)

| Classe | Soglia | Colore | Codice esadec. | Evidenza |
|--------|--------|--------|----------------|----------|
| OK | >= 10 | Verde brillante | `#00ffcc` | TSB >= 10: gambe fresche, forma buona. L'atleta ha margine per sforzi intensi o gara. |
| WARNING | -20 a 9 | Ambra | `#ffb800` | TSB -20 a 9: gambe cariche ma non critiche. L'atleta può sostenere allenamenti di intensità media ma dovrebbe evitare sforzi massimali. |
| DANGER | < -20 | Rosso | `#ff3366` | TSB < -20: gambe molto cariche. Rischio di strappi muscolari, crampi, prestazioni significativamente ridotte. Il backend usa TSB < -20 come soglia di overtraining risk. |

**Logica**: Le soglie -20/10 sono coerenti con il backend: TSB > 15 = fresh, TSB > 5 = ready for hard effort, TSB < -20 = low form / recovery priority.

---

## 3. Mappatura valore numerico → classe di stato (ok/warning/danger)

### Matrice riassuntiva

| Zona | Metrica | Range OK | Range WARNING | Range DANGER |
|------|---------|----------|---------------|--------------|
| **Head** | readiness (0-100) | >= 70 | 40 - 69 | < 40 |
| **Neck** | fatigue_score (0-10) | <= 4 | 5 - 7 | >= 8 |
| **Chest** | ctl (0-150+) | >= 60 | 30 - 59 | < 30 |
| **Core** | acwr (0-2+) | 0.8 - 1.3 | 0.5 - 0.79, 1.31 - 1.5 | < 0.5, > 1.5 |
| **Arms** | atl (0-150+) | <= 60 | 61 - 85 | > 85 |
| **Legs** | tsb (-50 to +50) | >= 10 | -20 - 9 | < -20 |

### Logica di classifica per ACWR (Core)

L'ACWR è l'unica metrica bidirezionale: valori troppo bassi (detraining) e valori troppo alti (overtraining) sono entrambi pericolosi.

```
if acwr < 0.5:     DANGER  (detraining marcato)
elif acwr < 0.8:   WARNING (detraining lieve-moderato)
elif acwr <= 1.3:  OK      (sweet spot)
elif acwr <= 1.5:  WARNING (carico acuto elevato)
else:              DANGER  (rischio alto di infortunio)
```

### Note sulle soglie

- **Readiness**: le soglie 70/40 sono coerenti con `compute_readiness()` e `compute_risk_level()` del backend.
- **Fatigue score**: le soglie 4/7/8 sono coerenti con `calculate_fatigue_score()` e `build_risk_indicators()`.
- **CTL**: la soglia 60 corrisponde a un amatore con 3-4 anni di esperienza; per élite la soglia OK potrebbe essere 100. In futuro, il modello individuale deve adattare questa soglia al livello dell'atleta.
- **ACWR**: le soglie 0.8/1.3/1.5 sono quelle della letteratura scientifica (Gabbett, 2016; Blanch & Gabbett, 2016).
- **ATL**: le soglie 60/85 sono proporzionali al CTL; in futuro, il rapporto ATL/CTL potrebbe essere usato direttamente.
- **TSB**: le soglie 10/-20 sono coerenti con le proprietà `is_fresh` e `is_ready_for_hard_effort` del backend.

---

## 4. Proposta di evoluzione UI

### 4.1 Tooltip per zona

Ogni tooltip deve mostrare **tre livelli di informazione**:

1. **Identificativo**: nome zona + emoji/metáfora visiva.
2. **Valore numerico**: metrica primaria con unità di misura.
3. **Stato**: classe (OK/WARNING/DANGER) con colore associato.
4. **Contesto scientifico**: breve spiegazione di cosa significa quel valore per l'atleta.
5. **Raccomandazione derivata**: consiglio tratto dal backend o da regole base.

**Esempio — Core / ACWR:**

```
🛡️ Core / Stabilità
ACWR: 1.42 — WARNING
Carico acuto crescente rispetto alla base.
Rischio moderato di infortunio da sovraccarico.
Consiglio: riduci volume 10-20% questa settimana.
```

**Esempio — Legs / TSB:**

```
🦵 Gambe / Forma
TSB: -28 — DANGER
Gambe molto cariche. Forma negativa.
Rischio di strappi/crampi.
Consiglio: recupero attivo o riposo totale.
```

### 4.2 Card stile giocatore — evoluzione

La card esistente mostra già dati preziosi. L'evoluzione scientifica prevede:

| Sezione attuale | Evoluzione proposta | Dati da aggiungere |
|-----------------|---------------------|--------------------|
| **Attributi** (Potenza, Resistenza, Recupero, Forza, Forma, Stabilità) | Rinominare con termini scientifici | Potenza → `ftp_watts`; Resistenza → `ctl`; Recupero → `readiness`; Forza → `atl`; Forma → `tsb`; Stabilità → `acwr` |
| **Fitness State** (Readiness, Fatigue, TSB, ACWR) | Aggiungere trend e indicatori | `trend_7d`, `trend_30d`, `risk_indicators[]`, `recommendation` |
| **Footer** (Sessioni/sett, Ore/mese, Ore/anno) | Aggiungere carico interno | `weekly_tss`, `monthly_tss`, `recovery_hours_needed` |
| **Risk badge** | Mostrare dettaglio per zona | Quando risk_level è `warning` o `high`, evidenziare quale zona è in criticità |

### 4.3 Manichino — visualizzazione scientifica

Il manichino SVG attuale usa colori fissi per categoria. L'evoluzione scientifica prevede:

1. **Colore dinamico per zona**: il colore di ogni area corporea deve cambiare in base alla classe di stato (ok/warning/danger), non più basato su colori statici.
   - Sostituire i colori fissi in `categoryConfig` con mapping basato sullo stato.
   - Esempio: head è verde se readiness >= 70, ambra se 40-69, rossa se < 40.

2. **Intensità del colore**: usare opacity o saturazione per indicare la gravità entro la stessa classe.
   - Esempio: readiness 75 = verde brillante; readiness 72 = verde meno saturo.

3. **Indicatori visivi aggiuntivi**:
   - **Head**: un alone (glow) attorno alla testa per indicare il livello di SNC. Verde = chiaro, rosso = scuro.
   - **Neck**: linee di tensione (path aggiuntive) che appaiono quando fatigue_score > 5.
   - **Core**: una "corona" o anello attorno all'addome che si restringe quando ACWR si allontana da 1.0.
   - **Legs**: un'ombra o un alone sotto i piedi che si scurisce quando TSB è negativo.

4. **Animazioni**:
   - Nessuna animazione quando OK.
   - Leggera pulsazione (pulse) quando WARNING.
   - Pulsazione rapida + colore lampeggiante quando DANGER.

### 4.4 Legenda scientifica

Sostituire la legenda statica con una legenda dinamica che mostra:

- Nome zona + metrica primaria + valore attuale.
- Classe di stato con colore.
- Breve interpretazione scientifica.

---

## 5. Controlli di coerenza con il backend attuale e gap da colmare

### 5.1 Metriche disponibili nel backend

Il backend espone già tutte le metriche necessarie per il mapping proposto:

| Metrica | Campo backend | Disponibile | Note |
|---------|---------------|-------------|------|
| Readiness | `readiness` | Sì | 0-100, calcolata in `calculators.py` |
| Fatigue score | `fatigue_score` | Sì | 0-10, calcolata in `fatigue.py` |
| CTL | `ctl` | Sì | EWMA 42g, in `fitness_state_service.py` |
| ACWR | `acwr` | Sì | In `load_manager/chronic_load.py` |
| ATL | `atl` | Sì | EWMA 7g |
| TSB | `tsb` | Sì | CTL - ATL |
| Recovery hours | `recovery_hours_needed` | Sì | Stimata in `fatigue.py` + correzione TSB |
| Weekly TSS | `weekly_tss` | Sì | Ultimi 7 giorni |
| Monthly TSS | `monthly_tss` | Sì | Ultimi 30 giorni |
| Trend 7d/30d | `trend_7d`, `trend_30d` | Sì | In `fitness_state_service.py` |
| Risk indicators | `risk_indicators[]` | Sì | In `calculators.py` |
| Recommendation | `recommendation` | Sì | In `calculators.py` |
| FTP | `profile.ftp_watts` | Sì | In `AthleteProfile` |
| HRV / tono autonomo | — | **NO** | Non calcolato. Gap critico per zona Neck. |
| Dislivello / elevazione | `elevation_gain_m` | Sì (per ride) | Non aggregato per ACWR/stress. |
| FC media | `heart_rate_avg` | Sì (per ride) | Usata in `fatigue.py` per fatigue score. |
| Potenza normalizzata (NP) | — | **NO** | Non calcolata; TSS usa speed-based IF approximation. |

### 5.2 Gap da colmare

| Gap | Priorità | Descrizione | Impatto sul manichino |
|-----|----------|-------------|------------------------|
| **HRV / tono autonomo** | Alta | Il backend non calcola la variabilità della frequenza cardiaca. Senza HRV, la zona **Neck** (tensione/tono autonomo) si basa solo sul fatigue_score, che è un proxy indiretto. | Neck ha una metrica meno precisa; in futuro, integrare HRV da sensori o da dati di recovery. |
| **Potenza normalizzata (NP)** | Media | Il backend stima l'IF (Intensity Factor) dalla velocità media, non dalla potenza. Questo introduce errore nel TSS quando mancano i dati di potenza. | ACWR e CTL sono distorti per uscite senza power meter. |
| **Modello individuale di recupero** | Alta | Il backend ha `PersonalResponseModel` come concetto ma non è implementato nel calcolo di `recovery_hours_needed`. Attualmente, le ore di recupero sono stimate con una formula generica. | Le soglie per tutte le zone potrebbero essere adattive in futuro, non statiche. |
| **FTP dinamica** | Bassa | L'FTP è un campo statico nel profilo. Non si aggiorna automaticamente con i progressi dell'atleta. | La zona Chest (CTL) e le barre FTP nel componente sono meno precise nel lungo periodo. |
| **Sleep / meteo / fattori esterni** | Media | Non ci sono campi per sonno, temperatura, umidità. | Il modello di recupero è incompleto; readiness potrebbe essere più precisa con questi input. |

### 5.3 Coerenza delle soglie attuali vs. proposte

Il componente `AthleteAvatarPanel.vue` usa attualmente queste soglie:

| Zona | Metrica | Soglia attuale | Proposta | Delta |
|------|---------|----------------|----------|-------|
| head | readiness | >=70 ok, >=40 warning, <40 danger | IDENTICA | — |
| neck | fatigue_score | <=5 ok, <=7 warning, >7 danger | <=4 ok, 5-7 warning, >=8 danger | Warning abbassata da 5 a 4 per maggiore granularità |
| chest | ctl | >=50 ok, >=30 warning, <30 danger | >=60 ok, 30-59 warning, <30 danger | OK alzata da 50 a 60 per coerenza con benchmark |
| core | acwr | 0.8-1.3 ok, else warning | 0.8-1.3 ok, 0.5-0.79/1.31-1.5 warning, <0.5/>1.5 danger | Aggiunge classe DANGER per ACWR estremi |
| arms | atl | <=80 ok, <=100 warning, >100 danger | <=60 ok, 61-85 warning, >85 danger | Soglie ribassate per coerenza con ATL/CTL ratio |
| legs | tsb | >=-20 ok, >=-40 warning, <-40 danger | >=10 ok, -20-9 warning, <-20 danger | OK alzata da -20 a 10; WARNING spostata |

**Nota**: Le soglie proposte sono più stringenti per le gambe (legs) e le braccia (arms) perché riflettono meglio la letteratura scientifica e le proprietà del backend. TSB >= 10 è la soglia per "ready for hard effort", non TSB >= -20.

---

## 6. Roadmap minima per raffinare il manichino

### Fase 1 — Allineamento scientifico (senza rompere l'implementazione attuale)

**Obiettivo**: rendere il mapping esistente coerente con le soglie del backend.

- [ ] Aggiornare `categoryStatus` in `AthleteAvatarPanel.vue` con le soglie della Sezione 3.
- [ ] Sostituire i colori statici in `categoryConfig` con colori dinamici basati sullo stato.
- [ ] Aggiungere la classe `danger` per `core` (ACWR).
- [ ] Aggiornare i tooltip con il formato della Sezione 4.1.
- [ ] Aggiungere `trend_7d`/`trend_30d` nella card.

**Criterio di successo**: nessuna modifica al backend, solo adattamento del frontend alle soglie esistenti.

### Fase 2 — Arricchimento dati (minime modifiche backend)

**Obiettivo**: colmare i gap critici senza stravolgere l'architettura.

- [ ] Implementare `recovery_hours` adattivo in `PersonalResponseModel` (Bayesian smoothing su storico risposte).
- [ ] Aggiungere calcolo `hrv_estimate` (se disponibile da dispositivo) come campo opzionale in `AthleteState`.
- [ ] Aggiungere campo `sleep_hours` in `AthleteProfile` o in un modello separato `RecoveryFactors`.
- [ ] Implementare soglie adattive in base al livello di esperienza (`experience_level`).

**Criterio di successo**: il manichino usa dati più granulari senza breaking changes.

### Fase 3 — Visualizzazione avanzata

**Obiettivo**: evoluzione UI basata sulla base scientifica definita.

- [ ] Introdurre animazioni per classe di stato (pulse warning/danger).
- [ ] Aggiungere indicatori visivi aggiuntivi nel SVG (linee di tensione per neck, alone per legs, corona per core).
- [ ] Implementare drill-down: click su una zona → mostra grafico storico della metrica.
- [ ] Aggiungere modalità "confronto": overlay con stato di 7/30 giorni fa.

### Fase 4 — Modello predittivo

**Obiettivo**: il manichino non mostra solo lo stato attuale, ma predice lo stato futuro.

- [ ] Integrare proiezione TSB/CTL a 7 giorni basata sul piano di allenamento.
- [ ] Mostrare "stato previsto dopo la prossima uscita" come tooltip secondario.
- [ ] Aggiungere alert proattivi: "Se fai questa uscita domani, il tuo TSB scenderà a -25".

---

## Appendice A — Fonti logiche per le soglie

| Soglia | Fonte logica | Riferimento backend |
|--------|--------------|---------------------|
| Readiness >= 70 OK | `compute_risk_level()` + `compute_recommendation()` | `calculators.py` |
| Readiness < 40 DANGER | Soglia sotto la quale readiness < 50 (low readiness indicator) | `build_risk_indicators()` |
| Fatigue <= 4 OK | Soglia sotto la quale non si attiva alcun decremento readiness | `fatigue.py` |
| Fatigue >= 8 DANGER | Soglia di alto rischio nel backend | `calculators.py`, `adaptation_rules.py` |
| CTL >= 60 OK | Benchmark Banister per amatori avanzati | Letteratura |
| CTL < 30 DANGER | Sotto il minimo per carichi ciclistici strutturati | Letteratura |
| ACWR 0.8-1.3 OK | Sweet spot scientifico (Gabbett, 2016) | Letteratura |
| ACWR > 1.5 DANGER | Soglia di alto rischio infortunio (Blanch & Gabbett, 2016) | `adaptation_rules.py` |
| ATL <= 60 OK | Sotto la soglia di allarme per fatica acuta | `calculators.py` |
| TSB >= 10 OK | Soglia "ready for hard effort" con margine | `fitness_state.py`, `calculators.py` |
| TSB < -20 DANGER | Soglia di recovery priority / overtraining risk | `adaptation_rules.py`, `fitness_state.py` |

## Appendice B — Glossario

| Termine | Definizione |
|---------|-------------|
| **CTL** | Chronic Training Load: fitness aerobica a lungo termine (EWMA 42 giorni). |
| **ATL** | Acute Training Load: fatica a breve termine (EWMA 7 giorni). |
| **TSB** | Training Stress Balance = CTL - ATL. Forma corrente. |
| **ACWR** | Acute:Chronic Workload Ratio = ATL / CTL. Rapporto tra carico recente e carico strutturale. |
| **Readiness** | Punteggio 0-100 che sintetizza prontezza all'allenamento basato su TSB, fatigue_score e ACWR. |
| **Fatigue Score** | Punteggio 0-10 basato su durata, intensità (FC/IF), velocità, dislivello e peso. |
| **TSS** | Training Stress Score: carico interno di una singola uscita. |
| **EWMA** | Exponentially Weighted Moving Average: media mobile pesata esponenzialmente. |
| **SNC** | Sistema Nervoso Centrale. |
| **HRV** | Heart Rate Variability: variabilità della frequenza cardiaca, proxy del tono autonomo. |
