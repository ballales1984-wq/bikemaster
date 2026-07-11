# AetherMap Engine — Phase 1: Modello Matematico della Terra

> **Agente:** Fase 1 (Fondamenta matematiche)
> **Tipo:** Design Doc — nessun codice
> **Principio guida:** "Se oggi inventassimo il miglior motore cartografico del mondo, come lo progetteremmo?" Ogni assunzione ereditata dal settore (WGS84, ECEF, mesh triangolari, proiezioni) viene messa sotto interrogatorio, non accettata.

---

## 0. Introduzione: la domanda sbagliata che tutti si fanno

La cartografia moderna parte da una domanda tacita e mai discussa: *"Come adattiamo la Terra a un foglio piano (o a una GPU che vuole triangoli)?"*. Questa domanda è sbagliata perché accetta come vincolo immutabile la tecnologia del XIX secolo (la stampa su carta) e del XX (la rasterizzazione a triangoli).

AetherMap parte dalla domanda inversa: **"Come è fatta la Terra, e quale struttura dati la rappresenta fedelmente senza forzarla in una forma che le è estranea?"**

La Terra non è:
- una sfera (errore ~21 km di raggio polare);
- un ellissoide (ignora montagne, oceani, gravità anomala);
- una superficie 2D (ha volume, atmosfera, sottosuolo, dinamica temporale).

La Terra è un **campo scalare/dinamico a 3+1 dimensioni**: una distribuzione di massa, elevazione, materia e metadati che evolve nel tempo. Il "modello matematico" di AetherMap deve quindi rispondere a tre domande gerarchiche:

1. **Geometria** — quale primitiva descrive lo *shape* del pianeta con il miglior rapporto fedeltà/costo?
2. **Coordinate** — in quale spazio numerico indirizziamo un punto senza introdurre distorsioni di proiezione?
3. **Semantica** — come appendiamo a quella geometria i dati "vivi" (traffico, neve, ombra)?

Questo documento non sceglie a priori: confronta, misura, e arriva a una **raccomandazione ibrida** motivata dai trade-off.

---

## 1. Confronto delle rappresentazioni geometriche

Per ogni rappresentazione valutiamo quattro assi: adeguatezza geometrica, costo computazionale, adattabilità a un digital twin "vivo", e limiti/innovazioni possibili.

### 1.1 Sfera

**Definizione.** Superficie di raggio costante `R` (per AetherMap ideale: `R ≈ 6371 km`, raggio medio volumico). Punto individuato da `(θ, φ)` (colatitudine, longitudine).

**1.1.1 Adeguatezza geometrica.** Pessima ma onesta: la Terra si scosta dall'equivalente sferico di fino a ~21 km (schiacciamento `f ≈ 1/298.257`). A scala umana (una città) l'errore di "sfericità" è trascurabile; a scala geodetica è inaccettabile per misure di distanza/area.

**1.1.2 Costo computazionale.** Eccellente. Distanze su grande cerchio = formula di haversine O(1); nessuna non-linearità. Rendering: sfera UV-mappata, banale per GPU. Memoria: zero (parametrica).

**1.1.3 Digital twin "vivo".** Neutra: la sfera è solo il contenitore; i dati vivi vanno attaccati altrove (texture, punti). Non porta informazione per sé.

**1.1.4 Limiti e innovazione.** Il limite è concettuale: tratta la Terra come un guscio vuoto. Innovazione possibile: usare la sfera solo come **LOD 0 / skybox di sfondo**, non come modello dati. Utile come livello "planet overview" a bassissimo costo.

---

### 1.2 Ellissoide (geode di riferimento)

**Definizione.** Superficie di rivoluzione `x²/a² + y²/a² + z²/b² = 1` (semi-assi `a` equatore, `b` polo). WGS84 è un ellissoide specifico, ma **WGS84 non è la Terra**: è una *superficie di riferimento matematica* su cui si misura l'altitudine geodetica.

**1.2.1 Adeguatezza geometrica.** Buona per la *forma media* del geoide (errore residuo vs geoide reale ≈ ±100 m, correggibile col geoide EGM). Ma resta una superficie liscia: montagne, oceani e città non esistono.

**1.2.2 Costo computazionale.** Mediocre. Le formule di distanza su ellissoide (Vincenty, Karney) sono iterative o con serie di Legendre; le normali geodetiche richiedono il calcolo del raggio di curvatura locale `N(φ)`. Più costoso della sfera di ~1-2 ordini di grandezza in query spaziali.

**1.2.3 Digital twin "vivo".** Neutra: anche l'ellissoide è un guscio. La vera domanda è **che cos'è l'altezza?** In WGS84 l'altezza geodetica `h` è la distanza lungo la normale dall'ellissoide — concetto astratto, non fisico. Il digital twin ha bisogno di **altezza ortometrica** (dal geoide, legata alla gravità reale) o almeno di un `h` coerente. Qui sta l'errore concettuale del settore: misuriamo l'altitudine rispetto a una superficie che non corrisponde al "livello del mare medio".

**1.2.4 Limiti e innovazione.** Il limite è che l'ellissoide è **statico e liscio**. Innovazione AetherMap: trattare l'ellissoide non come "il modello" ma come **superficie di parametrizzazione** su cui mappiamo la quota reale `Z(λ, φ, t)` come campo, trasformandolo di fatto nel caso 1.5 (campo sulla superficie). Vedere §1.6.

---

### 1.3 Mesh (superficie poligonale — triangoli/quads)

**Definizione.** Discretizzazione della superficie in elementi (tipicamente triangoli) con vertici `(x,y,z)` e attributi per-vertex/per-face.

**1.3.1 Adeguatezza geometrica.** Arbitraria: dipende dalla densità di campionamento (LOD). Può rappresentare qualsiasi rilievo con errore ~ densità vertices. È la rappresentazione "universale" del rendering GPU.

**1.3.2 Costo computazionale.** Dipende da **come** si genera la mesh. Due famiglie:

- *Mesh cartesiana proiettata* (es. tile UTM, planare): introducono **singolarità ai poli** e giunzioni tra zone (cuciture visibili). Scartata per AetherMap.
- *Mesh su sfera/ellissoide* (icosphere, quad-tree geografico, cubemap): distribuzione uniforme, niente poli speciali. Costo: `O(n)` vertici, query spaziali in `O(log n)` con strutture ad albero.

Il problema nascosto: **le mesh triangolari standard soffrono di "T-junction" e cracking ai confini LOD** — un classico dolore del settore (es. problemi di CLOD in terreni planetari). Va risolto a priori con regole di stitching o con schemi come *clipmap* / *hedron*.

**1.3.3 Digital twin "vivo".** Buona ma limitata: gli attributi per-vertex sono *statici per frame* e la topologia triangolare è rigida. Un albero che cresce, una strada il cui traffico cambia, una valanga: la mesh non ha "oggetti", ha solo vertici. Serve un **layer semantico separato** che proietta oggetti sulla mesh (vedi §4). La mesh è la "pelle", non il "corpo".

**1.3.4 Limiti e innovazione.** Limite: la mesh è una *superficie* — non rappresenta volumi (caverne, palazzi con interni, atmosfera). Innovazione: **mesh adattiva guidata dai dati**, non da una griglia fissa: raffina dove c'è semantica (una città), resta grossolana sull'oceano aperto. Questo è un passo oltre le griglie regolari.

---

### 1.4 Nuvola di punti (point cloud / LiDAR)

**Definizione.** Insieme non strutturato di punti `(x,y,z, attributi)` campionati dalla realtà (LiDAR, fotogrammetria).

**1.4.1 Adeguatezza geometrica.** La più fedele alla realtà *misurata*: è il dato grezzo, senza assunzioni di superficie. Risoluzione = densità di scansione (cm-scale con LiDAR aereo).

**1.4.2 Costo computazionale.** Alto. Niente topologia → niente rasterizzazione diretta: serve ricostruzione di superficie (ball-pivoting, Poisson) o rendering come *splat* (gaussian splatting). Memoria: gigantesca (milioni–miliardi di punti). Query spaziali: richiedono indici (KD-tree, octree) costosi da mantenere dinamici.

**1.4.3 Digital twin "vivo".** Ambivalente. Ogni punto può portare metadati ricchissimi (intensità LiDAR → materiale, colore, classe). Ma i punti sono **istantanei e muti**: non sono "oggetti", sono campioni. Un punto non "sa" di essere parte di una strada. Il digital twin richiede *segmentazione* (ML) per trasformare punti in oggetti — costoso e fragile.

**1.4.4 Limiti e innovazione.** Limite: non è una superficie né un volume, è un campionamento. Innovazione: usare il point cloud come **sorgente di verità** per generare le altre rappresentazioni (mesh, voxel), non come modello primario. E come **layer di dettaglio fine** in prossimità dell'osservatore (nebula/point-cloud LOD). Gaussian splatting 3D è la frontiera 2024+ per rendering fotorealistico senza mesh.

---

### 1.5 Voxel (volume 3D)

**Definizione.** Griglia 3D di celle (voxel) ciascuna con valore scalare/vettoriale. Estensione naturale della mesh in 3D.

**1.5.1 Adeguatezza geometrica.** Può rappresentare **tutto**: superficie, sottosuolo, atmosfera, edifici con interni, nuvole. È il modello più "completo" geometricamente perché non limita a una superficie 2D.

**1.5.2 Costo computazionale.** Esplosivo. Volume `V` con risoluzione `r` → `~r³` celle. Anche con strutture sparse (Sparse Voxel Octree, SVO) e compressione, il costo memoria/query scala cubicamente. Il rendering di volumi (ray marching) è costoso per frame rate interattivi su larga scala planetaria.

**1.5.3 Digital twin "vivo".** Eccellente *potenzialmente*: ogni voxel è un piccolo stato — può contenere temperatura, umidità, neve, traffico 3D, vento. È il modello che più naturalmente rappresenta un pianeta "vivo" e volumetrico. Ma il costo lo rende impraticabile come primario su scala globale.

**1.5.4 Limiti e innovazione.** Limite: cubicità del costo. Innovazione: **SVO gerarchico + voxel solo dove necessario** (sottosuolo urbanistico, atmosfera, interni). AetherMap lo adotta come **layer volumetrico locale**, non globale.

---

### 1.6 Il "sesto" modello nascosto: Campo parametrizzato (Heightfield come campo su superficie)

Nessuno dei modelli sopra è "il" modello: tutti confondono *contenitore geometrico* e *dato*. AetherMap propone di trattare la Terra come:

> **Una superficie di base (sfera o ellissoide) + un campo di altezza e attributi `F(λ, φ, t)` definito sopra di essa.**

Questo è concettualmente un *heightfield geografico continuo*, ma la chiave è che `F` non è una griglia fissa: è una **funzione campionabile a risoluzione arbitraria** (come un'immagine procedurale/SDF). Così si ottiene:
- fedeltà arbitraria (campiona dove serve);
- niente distorsione di proiezione (coordinate native su superficie);
- digital twin naturale (`F` include anche `traffico(λ,φ,t)`, `neve(λ,φ,t)`, ...).

Questo modello unifica §1.2 e §1.3 ed è la base della raccomandazione (§5).

---

## 2. Sistema di coordinate di riferimento

Il sistema di coordinate è la scelta più irreversibile: tutto (query, rendering, storage) dipende da esso. Esaminiamo le opzioni senza dare nulla per scontato.

### 2.1 Lat/Lon/Alt (geodetico) — lo standard WGS84

- **Pro:** intuitivo per l'uomo, compatibile col mondo esterno (GPS, API, dataset).
- **Contro:** **non uniforme** — un grado di longitudine a latitudine 60° copre metà della distanza che a 0°. Distorsione intrinseca che infetta ogni calcolo di distanza/area. Altitudine ambigua (geodetica vs ortometrica, §1.2.3).
- **Verdetto:** eccellente come **interfaccia uomo/dati**, pessimo come **spazio di lavoro interno**. AetherMap lo usa solo all'ingresso/uscita (I/O), non nei calcoli core.

### 2.2 ECEF cartesiano (Earth-Centered, Earth-Fixed)

`(X, Y, Z)` rispetto al centro di massa terrestre, assi ruotanti con la Terra.

- **Pro:** metrica uniforme (metri ovunque), niente distorsione, naturale per fisica/collisioni 3D, rendering diretto su GPU.
- **Contro:** coordinate "grandi" (milioni di metri) → **precisione float a rischio** (vedi §3.1). Non gerarchico: niente nozione di "regione".
- **Verdetto:** ottimo per **posizionamento e fisica**, ma va accoppiato a un sistema di **origine locale** (relative-to-camera) per evitare la perdita di precisione float. Non è indicizzabile per regione da solo.

### 2.3 Coordinate geocentriche sferiche (r, θ, φ)

- **Pro:** minimali, naturali sulla sfera.
- **Contro:** stesse distorsioni angolari del lat/lon; `r` non è altitudine fisica.
- **Verdetto:** scartate a favore di un ibrido cubemap/quadtree.

### 2.4 Cubemap / Quad-tree geografico (es. sistema a facce di cubo, tipo Google's S2-ish o cube sphere)

Si proietta la sfera su **6 facce di un cubo**, ciascuna con coordinate `(face, u, v)` e si suddivide ricorsivamente in quadtree.

- **Pro:** **niente poli speciali**, distribuzione uniforme della risoluzione, gerarchia naturale (LOD = livello del quadtree), indicizzazione spaziale eccellente (`(face, level, x, y)` = chiave univoca e ordinabile). Cache-friendly.
- **Contro:** distorsione ai bordi delle facce (gestione delle "seams"); mapping non banale.
- **Verdetto:** **candidato principale per lo spazio di lavoro interno** di AetherMap. Unisce uniformità (su faccia) e gerarchia (quadtree).

### 2.5 S2 (Google) e H3 (Uber) — sistemi a cella gerarchica

- **S2:** cells su sfera (quadtree su cubemap), eccellente gerarchia, usato da Google Maps. Proprietà: curve di Hilbert per locality.
- **H3:** esagoni su icosaedro, niente "quadranti" squadrati, copertura più uniforme per analisi (nessun confine rettilineo lungo). Ottimo per aggregazioni (traffico, griglie di sensori).
- **Contro S2/H3:** sono sistemi di **indicizzazione/aggregazione**, non spazi di rendering. Vanno usati come **chiavi spaziali** (spatial keys) sopra un contenitore geometrico, non come geometria.
- **Verdetto:** AetherMap adotta **S2 (o equivalente cube-quadtree) come spatial key** per indicizzare tutti i dati e oggetti, e **H3** come livello di aggregazione per il digital twin (es. "traffico medio nella cella esagonale"). I due coesistono: S2 per la geometria/LOD, H3 per l'analisi.

### 2.6 Raccomandazione coordinate (sintesi)

| Uso | Sistema |
|-----|---------|
| I/O con mondo esterno (GPS, API) | Lat/Lon/Alt (geodetico) |
| Fisica, posizionamento, rendering GPU | ECEF cartesiano **relativo** (origine mobile vicino alla camera) |
| Spazio di lavoro geometrico interno / LOD | **Cube-sphere quad-tree** `(face, level, u, v)` |
| Indicizzazione spaziale & query per regione | **S2 cell ID** (derivabile da cube-sphere) |
| Aggregazione digital-twin (traffico, meteo) | **H3 hex** |

**Principio:** nessun sistema solo. Lat/lon è l'interfaccia, ECEF-relative è il motore fisico, cube-sphere è la struttura, S2/H3 sono le chiavi. La conversione tra essi deve essere una libreria a sé, testata e banale.

---

## 3. Gestione degli errori e delle approssimazioni

Un motore cartografico è, sotto la superficie, una macchina da errori: floating-point, proiezioni, LOD. AetherMap li tratta come **cittadini di prima classe**, non come bug.

### 3.1 Precisione a virgola mobile

- Coordinate ECEF in metri: `~6.37e6`. Con `float32` (24 bit mantissa) la risoluzione assoluta è `~0.5–1 m` vicino all'equatore → **inaccettabile** per posizionamento centimetrico (auto, droni).
- **Soluzione AetherMap:** uso di **`float64`/`double`** per lo storage e il calcolo core; conversione a **`float32` relativo** per il rendering, con **origine locale** spostata con la camera (camera-relative rendering). Questo riporta le coordinate a ordini di grandezza `O(1e3)`, recuperando precisione float32 a livello sub-centimetro.
- Alternativa avanzata (non nella Fase 1, ma documentata): **integer-based fixed-point** in unità di micrometri per sistemi embedded.

### 3.2 Distorsioni di proiezione

Ogni proiezione piana (Mercator, UTM) distorce area/distanza/angolo. AetherMap **rifiuta le proiezioni piane come spazio di lavoro** (§2.4): lavorando su cube-sphere, la distorsione è confinata ai bordi di faccia e correggibile con stitching. La distorsione non è eliminata ma **localizzata e prevedibile**, invece di essere globale e invisibile (il vero pericolo di Mercator).

### 3.3 Livelli di dettaglio (LOD) e coerenza

- LOD gerarchico su quad-tree: ogni cella ha una risoluzione adatta alla distanza/semantica.
- **Problema classico:** cracking ai confini tra LOD diversi (T-junction). AetherMap specifica *a priori* regole di stitching o l'uso di **clipmap/skirts** (falde verticali sui bordi delle tile) per nascondere il cracking senza topologia complessa.
- **LOD semantico:** una cella con una città ha LOD più alto di una cella oceanica, indipendentemente dalla distanza. Il LOD è guidato da **importanza dei dati**, non solo da distanza geometrica.

### 3.4 Errore di modello (vs verità)

- Ellissoide vs geoide: errore ~±100 m nell'altitudine. AetherMap specifica un **modello di geoide** opzionale (EGM96/2008) per convertire `h` geodetica → ortometrica dove richiesto (es. idrologia, livello del mare).
- Point cloud / mesh: errore di ricostruzione documentato per cella (metadato di incertezza). Il digital twin espone `confidence` per ogni dato.

### 3.5 Tempo come dimensione (4D)

L'errore più grande del settore: trattare la mappa come statica. AetherMap modella `F(λ,φ,t)` — l'errore temporale (quanto è "fresca" la neve/traffico) è un **metadato primo** accanto alla posizione. Stale data ≠ errore silenzioso, ma etichettato.

---

## 4. Digital Twin "vivo": dove vivono i dati

La domanda chiave: *gli oggetti (strade, alberi) sono parte della geometria o vivono altrove?*

**Risposta AetherMap:** separazione netta tra **geometria** (la pelle planetaria, §1.6) e **entità semantiche** (gli oggetti vivi). Motivazione:

- La geometria cambia raramente (rilievo). Gli oggetti cambiano continuamente (traffico, neve, cantieri).
- Mischiarli (vertici della mesh che portano "traffico") distrugge la cache e la scalabilità.

Architettura proposta (contratto per Fase 2):
- **Layer geometrico:** cube-sphere heightfield continuo (geometria + texture/normal).
- **Layer entità:** oggetti con `(id, geometry_ref, state, t)` dove `geometry_ref` è un S2/H3 cell o un bounding volume. Stato = dati vivi (traffico, ombra calcolata, pendenza derivata, neve).
- **Layer volumetrico (opzionale, locale):** voxel/SVO per sottosuolo/atmosfera/interni urbani.

"Vivo" = il layer entità è **aggiornabile per cella indipendente**, alimentato da stream (es. sensori, simulazioni). La geometria resta immutabile; solo lo stato muta.

---

## 5. Raccomandazione finale

### 5.1 Modello adottato: **Ibrido a tre strati**

```
[ Strato 1 ] Geometria di base  → Cube-sphere + heightfield continuo F(λ,φ)
             (sfera/ellissoide come superficie di parametrizzazione)
[ Strato 2 ] Entità semantiche  → oggetti vivi indicizzati per S2/H3 con stato temporale
[ Strato 3 ] Volumetrico locale → SVO/voxel solo dove serve (città, atmosfera, sottosuolo)
```

### 5.2 Perché questo ibrido

1. **Nessuna distorsione globale nascosta.** Lavorando su cube-sphere invece di proiezioni piane, la distorsione è localizzata e gestibile. Rispetta la regola guida: sfidiamo Mercator.
2. **Fedeltà arbitraria.** L'heightfield come campo campionabile permette LOD infinito senza griglie fisse.
3. **Digital twin nativo.** Separando geometria ed entità, gli oggetti "vivono" senza appesantire la geometria.
4. **Scalabilità.** S2/H3 danno gerarchia e aggregazione; ECEF-relative risolve il float.
5. **Onestà sull'errore.** Precisione, distorsione, staleness sono metadati espliciti.

### 5.3 Trade-off accettati (dichiarati)

- **Complessità del cubemap:** gestione delle seams tra facce. Accettato: complessità locale, guadagno globale.
- **Conversione multi-sistema:** paghiamo una libreria di conversione robusta. Accettato: evita errori silenti peggiori.
- **Voxel non-globale:** rinunciamo a un volume planetario completo. Accettato: cubicità del costo lo rende impraticabile; lo usiamo solo localmente.
- **Point cloud non-primario:** rinunciamo al "fotorealismo grezzo" come default. Accettato: lo usiamo come sorgente di verità e LOD fine vicino all'osservatore.

### 5.4 Cosa scartiamo esplicitamente

- Proiezioni piane (Mercator/UTM) come spazio di lavoro interno.
- Mesh cartesiana planare con tile giunte (cuciture ai poli/zone).
- Ellissoide come "modello finale" (è solo parametrizzazione).
- Single-system thinking: nessun sistema di coordinate da solo basta.

---

## 6. Contratti per le fasi successive

Questo documento fissa le seguenti **invarianti** che Fase 2 e Fase 4 ereditano e NON devono violare.

### 6.1 Contratto per Fase 2 (Modello Dati)

- **Tipo di coordinate primario interno:** `(face, level, u, v)` su cube-sphere + `ECEF-relative` per fisica. Lat/Lon/Alt solo come I/O.
- **Spatial key:** ogni entità deve essere indicizzabile per **S2 cell ID**; aggregazioni per **H3**.
- **Struttura spaziale:** gerarchia quad-tree; LOD guidato da *distanza + importanza semantica*.
- **Separazione obbligatoria:** geometria (immutabile) ≠ stato entità (mutabile, temporale). Ogni entità espone `state` e `t` (timestamp) e `confidence`.
- **Errore esplicito:** ogni dato porta metadato di incertezza (spaziale/temporale).
- **Float:** storage/calcolo in `double`; rendering in `float32` relativo.

### 6.2 Contratto per Fase 4 (Rendering)

- **Spazio di lavoro GPU:** coordinate `float32` **relative all'origine mobile** (camera-relative), derivate da ECEF.
- **Superficie:** cube-sphere heightfield; **clipmap/skirts** obbligatori per evitare cracking LOD.
- **LOD:** gerarchico su quad-tree; livello minimo di dettaglio per cella oceanica vs urbana diverso (semantico).
- **Layer entità:** rendering degli oggetti vivi sopra la pelle geometrica, con stato aggiornabile per cella (no rewrite della geometria).
- **Layer volumetrico:** ray-marching su SVO solo per regioni locali selezionate.
- **Distorsione:** confinata ai bordi di faccia; nessuna proiezione piana globale ammessa nel pipeline di rendering.

### 6.3 Contratto trasversale (libreria coordinate)

- Una **libreria di conversione** unica e testata: `LatLonAlt ⇄ ECEF ⇄ CubeSphere ⇄ S2 ⇄ H3`. Qualsiasi fase usa SOLO questa. Nessun calcolo "fatto a mano" con formule WGS84 sparse.

---

## 7. Open Questions per l'utente (background tecnico richiesto)

Punti su cui il design deve essere integrato/corretto dall'esperienza umana:

1. **Gravità vs geometria:** quanto ci interessa il geoide reale (EGM) rispetto all'ellissoide? Serve altitudine ortometrica per gli use-case previsti (es. ciclismo/idrologia) o basta geodetica?
2. **Risoluzione target:** quale è la risoluzione massima richiesta (10 m globale? 1 m urbano? cm con LiDAR)? Determina la profondità del quad-tree e i costi memoria.
3. **Sorgente dati reale:** da dove arrivano i dati (Copernicus, LiDAR open, OSM, sensori privati)? Il formato di ingresso vincola il layer entità?
4. **Scale temporale del "vivo":** quanto velocemente devono aggiornarsi traffico/neve/meteo? Real-time (stream) o batch giornaliero? Influenza l'architettura dello stato.
5. **Target hardware:** GPU desktop, mobile, web (WebGL/WebGPU)? Vincola float32-relative e complessità del cubemap.
6. **Cube-sphere vs icosphere:** preferenza per quadtree (facce di cubo) o triangolazione icosaedrica? La prima è più semplice per tiling/texture; la seconda più uniforme (niente seams rettangolari).
7. **H3 vs S2 per aggregazione:** per i vostri use-case di digital twin, gli esagoni (H3) o le celle quadrate (S2) sono più adatte? Dipende se predominano analisi areali o lookup punto.
8. **Volumetrico:** serve davvero il layer voxel (interni edifici, sottosuolo, atmosfera 3D) o è over-engineering per la Fase 1? Definisce se lo teniamo come contratto o lo rimandiamo.
9. **Precisione richiesta posizionamento:** auto-drone richiede sub-decimetro (float64/double obbligatorio) o metro è sufficiente?
10. **Interoperabilità esterna:** quanto è vincolante il supporto di standard esistenti (GeoJSON, 3D Tiles, CityGML) vs libertà totale di "reinventare"?

---

## 8. Decisioni vincolanti dal checkpoint utente

Il Lead ha presentato questo documento all'utente (che porta il background tecnico GIS/grafica/DB/IA). Le seguenti 4 decisioni sono **vincolanti** per le fasi successive e non contraddicono la raccomandazione §5:

1. **Hardware target = Ibrido web + Python backend.** La *vista* gira nel browser (WebGL2/WebGPU) su `float32` camera-relative; i *calcoli pesanti* (pipeline IA Fase 3, conversioni coordinate, simulazioni) stanno nel backend Python (stack riusato da BikeMaster: Vue + FastAPI). Conseguenza su §2.6/§6.2: ECEF-relative vive nel frontend, ma la libreria coordinate condivisa (§6.3) deve essere implementata in Python ed esposta al frontend; i formati di scambio rete usano `double`.
2. **Risoluzione = Adattiva per zona (LOD semantico).** La profondità del quad-tree non è fissa ma guidata dall'importanza dei dati (città → LOD alto, oceano → LOD basso). Conferma la §3.3: il LOD è funzione di *distanza + semantica*, non solo geometria.
3. **Digital twin = real-time con latenza tollerata.** Gli stream di stato (traffico/meteo/manutenzione) aggiornano le entità con un buffer che permette calcoli e trasmissione; la geometria/rilievo resta in batch. Aggiorna §3.5/§4: lo `state` delle entità è *eventualmente coerente* (stream + latenza), non sincrono istantaneo.
4. **Interoperabilità = Supportare standard.** Il motore legge/scrive **GeoJSON, 3D Tiles, CityGML** (I/O). Il modello interno resta ibrido cube-sphere/S2/H3 (§6); questi formati sono gestiti come serializer/deserializer al confine, non come rappresentazione nativa.

### Stato delle Open Questions (§7) dopo il checkpoint

| # | Domanda | Stato |
|---|---------|-------|
| 1 | Geoide reale (EGM) vs ellissoide | APERTA — decidere se serve altitudine ortometrica per use-case ciclismo/idrologia |
| 2 | Risoluzione target | **RISOLTA** → adattiva per zona (LOD semantico) |
| 3 | Sorgente dati reale | APERTA — da stabilire (Copernicus/LiDAR/OSM/sensori) in Fase 3 |
| 4 | Scale temporale del "vivo" | **RISOLTA** → real-time con latenza tollerata (stream+buffer) |
| 5 | Target hardware | **RISOLTA** → ibrido web + Python backend |
| 6 | Cube-sphere vs icosphere | **RISOLTA** → cube-sphere confermato (§5) |
| 7 | H3 vs S2 per aggregazione | APERTA — entrambi adottati (S2 geometria/LOD, H3 aggregazione §2.5); da confermare bilanciamento use-case |
| 8 | Layer volumetrico voxel | APERTA → rimandato a valutazione Fase 5 (possibile over-engineering) |
| 9 | Precisione posizionamento | **RISOLTA** → `double` nel backend, `float32` relativo nel frontend |
| 10 | Interoperabilità standard | **RISOLTA** → supportare GeoJSON / 3D Tiles / CityGML |

---

*Fine Fase 1 — il terreno (matematico) è stato preparato e vincolato dal checkpoint. Le fasi successive camminano su queste coordinate.*
