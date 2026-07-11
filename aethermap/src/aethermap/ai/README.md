# AetherMap Engine — Fase 3: Pipeline IA "Ricercatore"

## Cosa fa
Ingesta dati grezzi (GPX, satellite, dati pubblici, sensori) e **propone**
modifiche al mondo con un **livello di confidenza**. Non genera la mappa:
lavora come un ricercatore le cui proposte sono tracciabili e confutabili.

## File
- `models.py` — `Oggetto`, `OggettoStato` (alias `Stato`), `Proposta` (Pydantic, coerenti con Fase 2).
- `ingest.py` — adapter GPX (xml), satellite/pubblico/sensore (stub).
- `researcher.py` — da GPX deduce una `Strada`, da sensore un `traffico`. Usa `models_ml` per la `confidence` (con fallback euristico). Hook ML chiaro.
- `models_ml.py` — **IA reale** (numpy, no sklearn): `RoadPlausibilityEstimator`, ridge regression addestrata su campioni sintetici deterministici, stima `road_score` (0..1) e `confidence` da feature del GPX (`n_punti`, `spanning`, `varianza elevazione`, `regolarita spaziale` via ECEF). Interfaccia stabile `estimate_gpx(points) -> (plausibility, confidence)`.
- `pipeline.py` — `WorldStore` + `Pipeline` con **buffer/latencia tollerata** (stato eventualmente coerente) e retention `stale_after`.
- `demo.py` — esegue l'intero flusso su `sample.gpx`.

## Esegui
```bash
python -m aethermap.ai.demo
```

## IA reale (hook ML)
`models_ml.py` contiene un estimatore ML minimale ma **reale**: una ridge
regression (equazioni normali su feature standardizzate + sigmoide) allenata
offline e in modo deterministico su campioni sintetici generati nel modulo.
Da ogni tracciato GPX estrae 4 feature — `n_punti`, `spanning` spaziale,
`varianza elevazione`, `regolarita spaziale` (distanze ECEF reali) — e ne
deduce `(road_score, confidence)`. `Researcher.propose_from_gpx` chiama
`estimate_gpx` e, in caso di fallimento, ricade sull'euristica. **Punto di
innesto**: rimpiazzare `_DEFAULT_ESTIMATOR` / `estimate_gpx` con un vero
modello (es. segmentazione satellitare + grafo OSM) mantenendo la stessa firma;
il resto della pipeline (buffer, retention, mondo) non cambia.

## Limiti
- Modello allenato su campioni sintetici (non su dati reali OSM/satellite).
- Storage in memoria; il path Parquet/PostGIS e documentato in Fase 2.
