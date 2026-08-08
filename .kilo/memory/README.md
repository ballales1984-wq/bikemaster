# Project Memory — Structure

Questo spazio costituisce la **memoria tecnica persistente** del team AI per
BikeMaster (§21 PROJECT MEMORY). È il custode della conoscenza condivisa tra
una sessione e l'altra.

L'agente **LIBRARIAN** mantiene e aggiorna questa struttura. Ogni agente le
pubblica eventi e registra risultati qui.

## Struttura

```
.kilo/memory/
├── README.md              ← questo file (panoramica)
├── shared-log.md          ← log eventi condiviso (§30)
├── bug-database.md        ← bug registry (§37)
├── decision-records.md    ← Architecture Decision Records (§43)
├── data-graph.md          ← grafo relazioni variabili (§14, §25)
└── code-graph.md          ← grafo dipendenze codice (§24)
```

## Categorie di memoria (§45)

| Categoria | Descrizione |
|---|---|
| FACT | Fatto oggettivo, verificabile |
| VERIFIED | Verificato con evidenza |
| HYPOTHESIS | Ipotesi da validare |
| OBSOLETE | Superato / non più valido |
| DECISION | Decisione architetturale |
| BUG | Bug registrato |
| FIX | Correzione applicata |

## Affidabilità di una informazione (§45)

Ogni entry deve indicare:

```
SOURCE | AUTHOR | TIMESTAMP | VERSION | VERIFICATION | CONFIDENCE | STATUS
```

## RAG Ibrido (§22, §26, §36)

La retrieval combina:

```
VECTOR SEARCH + KEYWORD SEARCH + METADATA FILTERING
  + CODE SEARCH + GRAPH SEARCH + TEMPORAL SEARCH
```

I risultati sono ordinati per:
```
SEMANTIC SIMILARITY + KEYWORD RELEVANCE + CODE RELATION
  + RECENCY + VERIFICATION STATUS + TASK RELEVANCE
```

## Usare la memoria

- Prima di ogni task, il LIBRARIAN costruisce un **Context Package** (§27)
  estraendo da questa memoria solo le informazioni rilevanti.
- Dopo ogni task, il LIBRARIAN registra: bug, decisioni, lezioni apprese,
  aggiornamenti ai grafi.
- Il VERIFIER verifica che le informazioni siano marcate con lo stato corretto.
