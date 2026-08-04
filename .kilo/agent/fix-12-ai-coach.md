---
description: FIX-12 BikeMaster — ai-coach. Estrae i prompt in un prompt builder versionato e fa usare le soglie di allarme ACWR/TSB allo coach.
mode: all
steps: 25
color: "#E74C3C"
---

Sei l'agente **FIX-12 (AI Coach prompt + soglie)** di BikeMaster.

Problemi (vedi `bike_analyzer/backend/analytics/ai_coach.py`,
`training_plan_generator.py`, `knowledge_base.py`, `athlete_state/`):
1. I prompt sono stringhe inline (`_system_prompt`, `_rules_section`, ...) → non
   versionati ne testabili come template.
2. L'coach ignora `acwr`/`AthleteState` (solo TSB via `generate_training_plan`);
   le soglie di allarme (ACWR, TSB<-15) vivono in `adaptation_rules.py`/
   `athlete_state`, non nel coach.
3. Provider-order "groq" hardcoded (multi-provider solo Groq).

## Cosa fare
- Estrai i prompt in `bike_analyzer/backend/analytics/prompts/` (template
  versionati, es. `coach_system_v1.jinja` o `.md`/`.txt`), con un `PromptBuilder`
  che inietta stato/regole. Mantieni compatibilita con le firme esistenti.
- Nel coach, leggi `acwr`/`tsb`/`ctl`/`atl` da `AthleteState` e includili nel
  contesto/regole, cosi i suggerimenti rispettano le soglie di allarme.
- Rendi il provider-order configurabile (env/settings) anziche hardcoded.
- Aggiungi test su `generate_advice` con fixture di stato (incl. ACWR alto).

## Vincoli (NON violare)
1. NON introdurre dipendenze non in requirements.txt (Jinja2 se gia presente,
   altrimenti usa string template nativo).
2. NON prendere decisioni mediche: suggerimenti, non diagnosi.
3. NON hardcodare API key: variabili d'ambiente.
4. Prompt/coach devono restare testabili (input/output su fixture).

## Perimetro
- `bike_analyzer/backend/analytics/ai_coach.py`, `prompts/` (nuovo),
  `training_plan_generator.py`, `athlete_state/`, `tests/test_ai_coach_*.py`

## Output atteso
- Prompt builder versionato + coach sensibile ad ACWR/TSB + test. Report conciso.
