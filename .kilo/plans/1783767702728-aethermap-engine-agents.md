# AetherMap Engine — Piano agenti (Lead Orchestratore)

## Contesto
- Progetto educativo + prototipo: *"Se oggi inventassimo da zero il miglior motore cartografico del mondo, come lo progetteremmo?"*
- **Deliverable ibrido**: Fasi 1-2 producono **design doc** (fondamenta); Fasi 3-5 producono **codice prototipo** (+ breve doc di design).
- **Ubicazione**: `D:\BikeMaster\.kilo\worktrees\inconclusive-pastry\aethermap\` (sottocartella nel worktree).
- **Orchestrazione**: un agente **Lead** spawna gli agenti di fase, gestisce dipendenze, raccoglie deliverable e chiede input utente ai checkpoint critici.
- **Regola guida (mai violata)**: non dare per scontata la tecnologia esistente. Per ogni scelta: *perché oggi si fa così? quali limiti? possiamo progettare di meglio?*

## Struttura directory (da creare dal Lead)
```
aethermap/
  docs/
    phase-1-earth-model.md
    phase-2-data-model.md
    phase-3-ai-design.md
    phase-4-rendering-design.md
  src/aethermap/
    core/      # Fase 1: modello matematico Terra
    data/      # Fase 2: modello/schema dati
    ai/        # Fase 3: pipeline IA
    render/    # Fase 4: renderer
    twin/      # Fase 5: digital twin (sintesi)
  tests/
```

## Roster agenti
- **Lead Orchestratore**: indice fasi + dipendenze, spawna sotto-agenti, raccoglie deliverable, chiede input utente ai checkpoint, esegue sintesi finale. Decide se parallelizzare fasi indipendenti.
- **Agente Fase 1** (Ricercatore modello Terra) — consulta specialista geodesia/GIS.
- **Agente Fase 2** (Architetto modello dati) — consulta specialista DB/spaziale.
- **Agente Fase 3** (Ingegnere pipeline IA) — consulta specialista ML.
- **Agente Fase 4** (Ingegnere rendering) — consulta specialista grafica/GPU/WebGL.
- **Agente Fase 5** (Architetto digital twin) — sintetizza 1-4.
- **Pool specialisti on-demand**: geodesia, algoritmi spaziali (LOD, spatial indexing), DB spaziali, grafica GPU, ML.

## Workflow per fase (pattern comune)
1. Lead spawna agente di fase con brief + vincoli ereditati dalle fasi precedenti.
2. Agente produce deliverable (doc o codice) applicando la regola guida.
3. **Checkpoint utente**: l'utente inietta il background tecnico / corregge / sfida le assunzioni.
4. Agente rivisita il deliverable integrando il feedback.
5. Lead marca la fase completa e sblocca le dipendenze a valle.

## Ordine e dipendenze
`1 → 2 → {3, 4 in parallelo} → 5 (sintesi)`.
Fase 5 dipende da 1, 2, 3, 4. Il Lead può eseguire 3 e 4 in parallelo dopo il completamento di 2 (sono indipendenti).

## Deliverable per fase
- **Fase 1 (doc)**: rappresentazione del pianeta — confronto sfera / ellissoide / mesh / point-cloud / voxel; sistema di coordinate; errori e approssimazioni; **raccomandazione + giustificazione**. (Nessun codice: è la fondamenta.)
- **Fase 2 (doc)**: classe base `Oggetto` con `posizione, geometria, proprietà, affidabilità, sorgenti, cronologia, relazioni`; gerarchia di classi; schema DB/spaziale; formati di scambio.
- **Fase 3 (codice + doc)**: pipeline "IA ricercatore" — ingestione satellite / GPX / dati pubblici / sensori; proposte di modifica con **livello di confidenza**; API pulita.
- **Fase 4 (codice + doc)**: valutazione SVG / Canvas / WebGL / GPU; renderer che consuma i modelli di Fase 1-2; motivazione della scelta.
- **Fase 5 (codice)**: digital twin — oggetti "vivi". Strada conosce `traffico, asfalto, ombra, pendenza, manutenzione`; albero `specie, altezza, ombra, crescita`; montagna `versanti, neve, vegetazione, sentieri`. Integra 1-4.

## Validazione
- **F1**: coerenza matematica; test round-trip coordinate (encode→decode senza perdita inaccettabile).
- **F2**: lo schema copre i casi d'uso strada/albero/montagna senza eccezioni strutturali.
- **F3**: la pipeline gira su un dataset minimo e produce proposte con confidenza misurabile.
- **F4**: il renderer disegna un sottoinsieme del mondo a FPS accettabile.
- **F5**: un oggetto twin risponde a un update (es. variazione traffico) e il cambiamento si riflette nel rendering.

## Rischi
- **Scope esplosivo**: ogni fase ha un deliverable minimo e checkpoint; il Lead respinge l'over-engineering.
- **Lock tecnologico prematuro**: ogni scelta documenta alternative e limiti (regola guida).
- **Refactoring a valle**: Fase 5 rischia di richiedere modifiche se 1-4 cambiano; il Lead mantiene **contratti d'interfaccia** espliciti tra fasi.

## Open questions (non bloccanti, risolte durante l'esecuzione)
- Stack runtime del prototipo (core Python + ? per il rendering): deciso in Fase 4.
- Dataset di test reali (GPX/satellitari) vs sintetici.
- Estensione temporale / profondità del corso.

## Primo passo
Il Lead crea la struttura `aethermap/` e avvia l'**Agente Fase 1** (modello matematico della Terra).
