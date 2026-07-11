# AetherMap Engine — Phase 2: Modello Dati

> **Agente:** Fase 2 (Modello dati)
> **Tipo:** Design Doc — nessun codice eseguibile oltre snippet Pydantic
> **Vincoli ereditati:** coordinata primaria cube-sphere `(face, level, u, v)` + ECEF-relative, S2/H3 come spatial keys, double storage / float32 render, backend Python, I/O GeoJSON / 3D Tiles / CityGML, LOD adattivo, separazione geometria/stato.

## 1. Classe base Oggetto (7 campi)

Ogni entità del mondo deriva da `Oggetto`. I primi 7 campi sono obbligatori e non cambiano tra le gerarchie.

| # | Campo | Tipo | Descrizione |
|---|-------|------|-------------|
| 1 | `posizione` | `OggettoPosizione` | Coordinate nel sistema primario: `(face, level, u, v)` + `(ecef_relative_x, ecef_relative_y, ecef_relative_z)` + altitudine geodetica se nota. |
| 2 | `geometria` | `OggettoGeometria` | Riferimento alla geometria immutabile: shape primitivo (linea/mesh/punto), vertici in double, `confidence` geometrica. Usa S2 cell ID come chiave spaziale. |
| 3 | `proprieta` | `OggettoProprieta` | Metadati etichetta: nome, classe semantica (`Strada`, `Albero`, `Montagna`, ...), dimensioni, materiale, categoria utente. |
| 4 | `affidabilita` | `OggettoAffidabilita` | `(confidence: double, ultimo_aggiornamento: datetime, sorgente_affidabilita: str, errore_modello: double | null)`. Metadato primo. |
| 5 | `sorgenti` | `list[OggettoSorgente]` | Provenienza: dataset (OSM, Copernicus, LiDAR, sensore), `source_hash`, `stale_after`. |
| 6 | `cronologia` | `list[OggettoStato]` | Storico temporale degli stati; ogni voce ha `t`, `confidence`, `hash_stato`. Append-only. |
| 7 | `relazioni` | `list[OggettoRelazione]` | Collegamenti: `(tipo, id_oggetto, peso)` — es. Strada->Albero (ombra), Albero->Strada (radice). |

## 2. Separazione Geometria / Stato

La geometria di un oggetto è **immutabile** dopo lingest. Lo stato è **mutabile** e **temporale**.

- **Geometria:** risiede in `OggettoGeometria`. Shape primitivo (linee per Strade, punti per Alberi, mesh heightfield per Montagne). Coordinate in `double`. S2 cell ID come spatial key. Index: S2 + H3.
- **Stato:** risiede in `OggettoStato` append-only nella cronologia. Contiene dati dinamici: `traffico` (Strada), `altezza_fogliame` (Albero), `manto_nevoso` (Montagna). Ogni record: `{ t: datetime, campi_dinamici: dict, confidence: double }`.
- **Principio:** non si sovrascrive lo stato, si accoda. Questo rende lo storage partizionabile per tempo e compatibile con stream real-time.

## 3. Gerarchia Strada / Albero / Montagna

Tutte derivano da `Oggetto`, specializzano i campi di geometria e proprieta.

```
Oggetto
+-- Strada (geometry: LineString/MultiLineString)
|   +-- geometria.shape = segmenti ECEF-relative (double)
|   +-- proprieta.larghezza, pendenza, categoria_viario
|   +-- stato.corrente = { traffico: float, velocita_media: float, incidenti: list }
+-- Albero (geometry: Point + canopy_radius)
|   +-- geometria.shape = punto ECEF-relative (double)
|   +-- proprieta.specie, altezza_max, diametro_fusto
|   +-- stato.corrente = { salute: float, altezza_fogliame: float, ombra_calcolata: bool }
+-- Montagna (geometry: mesh heightfield)
    +-- geometria.shape = facce triangolari con mappa quota F(lambda, phi)
    +-- proprieta.nome, quota_cima, pendenza_media
    +-- stato.corrente = { manto_nevoso: float, temperatura_superficie: float, rischio_valanga: str }
```

## 4. Spatial Key: S2 + H3

- **S2 Cell ID:** ogni `Oggetto.geometria` espone `s2_cell_id` (token). E la chiave primaria per query spaziali e LOD. Deriva da `(face, level, u, v)` con curva di Hilbert.
- **H3 Index:** ogni entità espone `h3_indexes` (multirisoluzione). Usato per aggregazioni digital twin (es. traffico medio per cella esagonale). Non sostituisce S2 per geometria.
- **Double-resolution vs Tiling:** S2 gerarchico copre LOD; H3 copre aggregazione analitica. Coesistono come in §2.5 della Fase 1.

## 5. Storage / DB: confronto + raccomandazione

| Opzione | Pro | Contro | Raccomandazione |
|---------|-----|--------|-----------------|
| PostgreSQL + PostGIS | maturo, SQL standard, GeoJSON nativo | add-on, performance su punti globali degradante con scala | Scartare come storage primario per layer entità massivo. Usabile per metadati relazionali e amministrazione. |
| MongoDB | schema flessibile, geospatial index | non ottimizzato per S2/H3 nativo | Accettabile per batch ingest e staging. |
| Redis + RedisSearch | velocità, semantica live | costo memoria, no native 3D | Usare come **cache stato real-time** (solo gli ultimi N stati per oggetto). Non è sorgente di verità. |
| **DuckDB** + estensioni spaziali | in-process, zero-dep, `double` nativo, supporta H3/S2 via UDF, ottimo per analytical queries su dati geospaziali, compatibile con GeoJSON/Parquet | non distribuito di default | **Raccomandazione primaria per il backend Python**. Single-binary, testabile, adatto a pipeline IA Fase 3. |
| **ClickHouse** | columnar, eccellente per serie temporali (cronologia), H3 nativo, distribuito, compressione | curva di apprendimento, overkill per dataset piccoli | **Raccomandazione per storage storico + telemetria** se la scala supera 10M oggetti/report real-time. |
| GeoPackage / FlatGeobuf | portabile, senza server | non adatto a stato mutabile massivo | Usare per export batch e I/O offline. |

**Raccomandazione finale:**
- **Statements of truth:** ClickHouse per oggetti, geometrie e cronologia (serie temporali massive).
- **Cache real-time + computation:** DuckDB per pipeline di calcolo e aggregazioni in-process nel backend Python.
- **Metadati relazionale piccolo:** PostgreSQL/PostGIS per amministrazione utenti, permessi, mapping dataset.

## 6. Schema Pydantic (snippet)

```
from pydantic import BaseModel
from datetime import datetime

class OggettoPosizione(BaseModel):
    face: int
    level: int
    u: float
    v: float
    ecef_relative: tuple[float, float, float]

class OggettoGeometria(BaseModel):
    s2_cell_id: str
    shape_type: str  # "Point", "LineString", "Polygon", "MeshPatch"
    ecef_vertices: list[tuple[float, float, float]]
    confidence: float

class OggettoStato(BaseModel):
    t: datetime
    campi_dinamici: dict
    confidence: float

class Oggetto(BaseModel):
    id: str
    posizione: OggettoPosizione
    geometria: OggettoGeometria
    proprieta: dict[str, Any]
    affidabilita: OggettoAffidabilita
    sorgenti: list[dict]
    cronologia: list[OggettoStato]
    relazioni: list[dict]
```

## 7. Note I/O standard

- **GeoJSON:** formato di interscambio per entità semplici. Coordinate: Lat/Lon/Alt WGS84. Conversione gestita dalla libreria coordinate condivisa (§6.3 Fase 1). No proprietà dinamiche complesse nel GeoJSON standard; si usa `properties` con estensioni.
- **3D Tiles (b3dm / i3dm / pnts):** formato di streaming per il frontend. Gli oggetti sono impacchettati in tile secondo la struttura S2. Geometria in ECEF-relative; stato aggiornabile via texture/batch table.
- **CityGML:** I/O per edifici e volumetrie urbane. GML come boundary; interno convertito in entità Albero/Montagna/Volumetrico locale. CityGML è lossy → si conserva il `target_hash` originale per riconciliazione.
- **Principio I/O:** nessun formato è rappresentazione nativa. Tutti sono serializer/deserializer al confine. Dentro AetherMap: modello ibrido.

## 8. Contratti per Fasi 3/4/5

- **Fase 3 (Sensori + IA):** ogni nuovo sensore produce `OggettoStato`. La libreria coordinate condivisa è obbligatoria per convertire coordinate grezze in cube-sphere + S2. DuckDB consulta batch; ClickHouse riceve stream. Stato fillato entro `max_latenza` (configurato per oggetto).
- **Fase 4 (Rendering):** il layer entità legge stato da cache (Redis/ClickHouse) senza toccare geometria. ECEF-relative a `float32` con origine camera. Geometria immutabile non viene riscritta. LOD adattivo: cella S2 con entità semantiche dense ottiene livello superiore.
- **Fase 5 (Ottimizzazione):** compressione cronologia (delta su `campi_dinamici`), retention policy per `stale_after`. Archiviazione su S3/Parquet; indice S2 per recall rapido.

## 9. Open Questions

1. **Risoluzione minima S2:** quale livello di profondità del cube-sphere è il minimo accettabile per layer urbano? Dipende da asset reale (LiDAR 10 cm -> livello 25+, OSM -> livello 15).
2. **Retention cronologia:** quanti stati per oggetto conservare prima di comprimere/archiviare? Determina dimensione ClickHouse e costo storage.
3. **Egemonia H3 o S2 per aggregazione:** per traffico/meteo predomina look-up punto (S2) o aree di analisi (H3)? Deve essere configurabile per dominio (urban vs naturale).
4. **Relazioni dinamiche:** le `relazioni` sono statiche o ridefinite da IA Fase 3? Se dinamiche, servono indici inversi (oggetto->zone che lo influenzano).
5. **GeoPackage vs FlatGeobuf:** quale formato scegliere per export mobile offline? FlatGeobuf è più leggero ma meno supportato da tool GIS desktop.
---

## 10. Decisioni vincolanti dal checkpoint utente

1. **Storage = Tutto Python / Parquet + S2** (gratuito, zero server). Nessun ClickHouse/PostGIS/Redis per il prototipo: entità in strutture Python + file Parquet (`pyarrow`/`duckdb`), indice spaziale via libreria **S2** in Python. Si migra a PostGIS/ClickHouse in seguito senza modificare il modello `Oggetto`. Conseguenza: la "libreria coordinate condivisa" (§6.3 Fase 1) è implementata in Python puro + `s2geometry`; lo storage è file-based.
2. **Aggregazione = S2 primario + H3 analisi.** S2 è la chiave spaziale primaria (geometria/LOD/lookup, allineata al cube-sphere di Fase 1); H3 è il layer di analisi sopra (traffico/meteo/vegetazione). Entrambi adottati, ruoli distinti.
3. **Retention cronologia = politica per-oggetto.** Ogni entità espone `stale_after`/retention configurabile; stati oltre soglia compressi in delta e archiviati (Parquet/S3). Coerente con `affidabilità`/`cronologia` di `Oggetto`.

### Stato delle Open Questions (§9) dopo il checkpoint

| # | Domanda | Stato |
|---|---------|-------|
| 1 | Risoluzione minima S2 (profondità) | APERTA — da fissare in Fase 4 (renderer) in base a LOD |
| 2 | Retention cronologia | **RISOLTA** → politica per-oggetto (`stale_after`) |
| 3 | Egemonia H3/S2 | **RISOLTA** → S2 primario, H3 analisi |
| 4 | Relazioni dinamiche (IA?) | APERTA — Fase 3 (IA) deciderà se ridefinisce relazioni |
| 5 | GeoPackage vs FlatGeobuf (export offline) | APERTA — rimandato a Fase 4/5 |

---

*Fine Fase 2 — il database del mondo è definito e vincolato. La geometria è immutabile, lo stato scorre, le chiavi sono S2 (primario) / H3 (analisi).*
