# AetherMap Engine — Phase 5: Digital Twin

> **Agente:** Fase 5 (Digital twin, oggetti vivi)
> **Tipo:** Design Doc + prototipo
> **Principio:** il terreno e' immutabile; gli oggetti sono "vivi" (stato mutabile).

## 1. Cos'e' il digital twin in AetherMap

Il digital twin e' la sintesi di Fasi 1-4:

- Fase 1: geometria cube-sphere + coordinate.
- Fase 2: modello dati (Oggetto con stato temporale).
- Fase 3: pipeline IA che arricchisce lo stato.
- Fase 4: rendering della scena.

La domanda chiave: dove vivono i dati "vivi"? Risposta AetherMap: nello stato dell'Oggetto, mai nella geometria.

```
[ Geometria immutabile ]   [ Stato temporale append-only ]
[ cube-sphere mesh    ]    [ cronologia: {t, campi, confidence} ]
                              ^
                              |
                       [ Pipeline IA ]
                       [ Ambiente ]
```

## 2. Layer volumetrico SVO

AetherMap adotta un `SparseVolume` (SVO) per la rappresentazione volumetrica locale di oggetti come Montagna.

- Griglia N^3 (N=16 nel prototipo, configurabile).
- Materiali: ROCK (0), SNOW (1), VEG (2), EMPTY (3).
- Snow line dinamica in base a temperatura: `base_alt + 1500 + (temp_c - 15) * 100`.
- `fraction_per_versant()`: percentuale neve per versante (N/S/E/W).

## 3. Entita' specializzate

### 3.1 Strada

- Geometria: LineString (punti GPX).
- Proprieta' calcolate: `pendenza()` (delta quota / distanza ortodromica), `ombrata(solar_elev_deg)` (sotto soglia 12 gradi).
- Stato dinamico: traffico (da sensore), asfalto, manutenzione.

### 3.2 Albero

- Geometria: Point.
- Proprieta' calcolate: `altezza()` (crescita: `base + 0.002 * giorni`), `ombra(solar_elev_deg)` (se altezza > 0 e sole < 18 gradi).
- Specie e altezza da proprieta'.

### 3.3 Montagna

- Geometria: heightfield sulla sfera (altezza + versanti).
- Proprieta' calcolate: `neve(temp_c)` (sotto 1 grado), `neve_interna(temp_c)` (SVO), `volume_stats(temp_c)` (snow_%, rock_%, veg_%).
- Interno: `_volume(temp_c)` crea SVO con parametri da proprieta'.

## 4. Ambiente

Classe `Environment` con:

- `temp_c`: temperatura dell'aria.
- `solar_elev_deg`: elevazione solare (0=orizzonte, 90=zenit).
- `ora`: stringa orario.

`DigitalTwin.step(env)`:

- Esegue stream sensori -> proposte -> flush (aggiorna traffico etc.).
- Per ogni oggetto chiama `_apply_env(obj, env)` che aggiorna proprieta' dinamiche (ombrata, ombra, neve).

## 5. Sintesi H3

`DigitalTwin.h3_summary(resolution)` aggrega oggetti per cella H3:

- Ogni oggetto contribuisce al parent H3 della sua cella.
- Output: `{h3_cell: {tipo: count, ...}}`.
- Utile per heatmap e analytics spaziali.

## 6. Contratti per Fase 6

- Il digital twin mantiene stato e cronologia separati da geometria.
- Generazione/aggiornamento proposta avviene solo via Pipeline (nessuna modifica diretta allo stato).
- Le relazioni tra oggetti sono esplicite (Relazione model) e aggiornabili via IA.
- Il SVO e' locale: una Montagna genera il proprio volume; non e' un volume globale. Il ray-marching (Fase 4) tocca solo il volume richiesto.

## 7. File

- `twin/objects.py` --- `Strada`/`Albero`/`Montagna` che estendono `Oggetto` (Fase 2).
- `twin/svo.py` --- `SparseVolume`: griglia N^3 + voxel pieni, materiali rock/snow/veg/vuoto.
- `twin/world.py` --- `DigitalTwin` + `Environment`: `step()`/`snapshot()`/`h3_summary()`.
- `twin/demo.py` --- simula 3 istanti (giorno/sera/notte).

## 8. Test suite

Test in `src/tests/test_twin.py`: 68 test covering:

- `Strada`: pendenza, ombrata, traffico, asfalto, manutenzione.
- `Albero`: specie, altezza, ombra, crescita.
- `Montagna`: neve, versanti, vegetazione, sentieri, neve_interna, volume_stats.
- `SparseVolume`: build, material_at, snow_fraction, stats, fraction_per_versant.
- `DigitalTwin`: add/snapshot, step sensor, step environment, snapshot fields.
- `H3 summary`: aggregazione per cella.

## 9. Esegui

```bash
python -m aethermap.twin.demo
```

Output previsto: `traffico` aggiornato, `ombrata`/`ombra` vera di sera, `neve=True` sulla montagna di notte gelata, `volume_stats` con percentuali neve/rock/veg.
