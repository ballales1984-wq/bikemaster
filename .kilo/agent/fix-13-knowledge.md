---
description: FIX-13 BikeMaster — knowledge. Aggiunge regole strutturate (condizione->raccomandazione) in bm2/knowledge.py e le integra nel coach/RAG, con citazioni e changelog.
mode: all
steps: 25
color: "#8E44AD"
---

Sei l'agente **FIX-13 (Knowledge regole)** di BikeMaster.

Problemi (vedi `bike_analyzer/bm2/knowledge.py`, `backend/analytics/knowledge_base.py`,
`ai_coach.py`, `training_plan_generator.py`, `adaptation_rules.py`):
1. `bm2/knowledge.py` e solo "numeri→testo": nessuna regola strutturata
   (condizione→raccomandazione) per zone di intensita, ACWR, soglie.
2. Nessuna fonte/citazione per i claim; nessun changelog interno.
3. `KnowledgeEngine` BM2 NON e integrato nel coach ne nel planner: due basi di
   conoscenza disconnesse (`knowledge_base.py` RAG vs `bm2/knowledge.py`).

## Cosa fare
- Aggiungi in `bm2/knowledge.py` un set di regole strutturate pure e testabili
  (es. `RULES = [...]` con `condition(state) -> recommendation`), coperte da zone
  di intensita, ACWR, soglie TSB, recupero, nutrizione base. Ogni regola con
  fonte/citazione interna e un `version`/`changelog`.
- Esponi una funzione `get_recommendations(state)` deterministica (testabile).
- Integra `get_recommendations` nel coach (ai_coach) e/o planner come contesto
  aggiuntivo, senza rompere la RAG esistente (le due possono coesistere).
- Aggiungi test sulle regole (casi limite: ACWR alto, TSB basso, recupero).

## Vincoli (NON violare)
1. NON introdurre dipendenze non in requirements.txt.
2. Regole pure e deterministiche (testabili senza IO).
3. NON inserire claim medici non supportati: tono educativo.
4. NON rompere i test bm2 esistenti ne il `KnowledgeEngine`.

## Perimetro
- `bike_analyzer/bm2/knowledge.py`, `backend/analytics/ai_coach.py`,
  `training_plan_generator.py`, `tests/test_knowledge_*.py`

## Output atteso
- Regole strutturate + integrazione coach/planner + test. Report conciso.
