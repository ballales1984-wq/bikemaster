---
description: FIX-05 BikeMaster — BM2 PowerModel. Corregge la simulazione what-if degenerata (resta sempre 260W=FTP perche ricalcola P dalla v risolta per P=FTP).
mode: all
steps: 25
color: "#34495E"
---

Sei l'agente **FIX-05 (BM2 PowerModel)** di BikeMaster.

Problema (vedi `bike_analyzer/bm2/algorithms/power_model.py` e `core.physics`):
`_compute` risolve `v` per `P=FTP` e poi ricalcola `P` da quella `v` (identita),
quindi peso/pendenza/CdA NON influenzano il risultato → la simulazione "what-if"
e priva di effetto (output sempre ~260W). Anche la docstring demo cita "peso -5 kg"
ma il preset `light_bike` applica -2 kg.

## Cosa fare
- Riscrivi `_compute` in modo che, dati i parametri (peso, pendenza, CdA, vento,
  FTP, potenza target o velocita target), il calcolo di potenza/velocita sia
  fisicamente coerente e sensibile ai parametri (equazione del ciclista:
  P = (resistenze: rotolamento + aero + gravita + inerzia) * v).
- Assicurati che variare peso/pendenza/CdA cambi l'output in modo monotono e
  plausibile.
- Allinea i preset demo (`light_bike`, ecc.) alla docstring o aggiorna la docstring.
- Aggiungi test di sensitivita (delta non nullo al variare dei parametri) e
  verifica `python -m bm2.simulation.demo`.

## Vincoli (NON violare)
1. NON introdurre dipendenze non in requirements.txt.
2. Algoritmo puro e deterministico (testabile senza IO).
3. NON rompere gli altri 8 algoritmi ne il registro `ALL_ALGORITHMS`.
4. Mantieni la firma/contratti usati da `orchestrator.py`/`adapters.py`.

## Perimetro
- `bike_analyzer/bm2/algorithms/power_model.py`, `core/physics.py`, `simulation/demo.py`
- `tests/` relativi a bm2/power

## Output atteso
- PowerModel fisicamente coerente + test sensitivita + demo verde.
  Report conciso modifiche/test.
