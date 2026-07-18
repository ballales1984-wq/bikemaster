# BikeMaster — Central Logic & Product Vision

> **Version:** 2.0.0
> **Date:** 2026-07-18
> **Status:** Definitive — central point of the project

For technical architecture, see [MASTER.md](./MASTER.md). For roadmap phases, see [ROADMAP.md](../ROADMAP.md).

---

## 1. Strategic Positioning

BikeMaster is a **lifestyle health intelligence** system. It defines health state as the dynamic balance of variables acquired from real life, and uses structured physical activity — starting with cycling — as the primary domain for analysis, recommendations, and optimization.

> **Official Mission:** The program defines health state as the balancing of variables acquired from your lifestyle. You choose what to eat, it analyzes, advises compatible quantities, proposes micro-corrections, and gives you the right amount of movement to maintain balance. We are similar in biology, but different in life — and the system respects both.

This choice:
- eliminates the onboarding barrier (the user does not have to start from zero);
- allows focus on unique value instead of rebuilding existing functionality;
- treats the person as a whole, not just as an athlete.

### 1.1 The Health Balance Framework

The system considers general health state as the **dynamic equilibrium** of all variables it collects:

| VAR | Description |
|---|---|
| **Energia** | Available energy level |
| **Macronutrienti** | Protein/carb/fat balance |
| **Acqua_totale** | Daily hydration |
| **Glicemia** | Glycemic control |
| **VO2** | Cardiorespiratory capacity |
| **Respirazione** | Breathing efficiency |
| **Battito** | Resting and exertion heart rate |
| **Orario** | Circadian rhythms and timing |
| **Storico** | Temporal trends |
| **Stato_generale** | Subjective wellbeing perception |

These VARs are every person's **metabolic signature**.

### 1.2 Where the VARs Come From — Real Life

The system invents nothing: it takes variables directly from lifestyle:

- **Stile_di_vita** — sedentariness, spontaneous activity, routines
- **Orari_di_lavoro** — shifts, flexibility, workload
- **Famiglia** — responsibilities, social support, conflicts
- **Stress** — psychological pressure, stressful events
- **Vizi** — smoking, alcohol, substances
- **Abitudini** — consolidated routines, automatic choices
- **Sonno** — duration, quality, continuity
- **Attività_fisica** — structured exercise (cycling included) and spontaneous movement

Because we are similar in biology, but different in life.

---

## 2. Differentiation vs Existing Products

### 2.1 Cycling-specific tools

| Product | Strength | Limitation vs BikeMaster |
|---|---|---|
| **Strava** | Community, segments, user habit, massive database | Still shows *what you did*, not *what you should do* |
| **Garmin** | Hardware, sensors, smartwatches, physiological data | Technical experience, not conversational |
| **TrainingPeaks** | Structured workouts, coaches | Rigid, oriented toward athletes who want to follow a fixed program |

### 2.2 Lifestyle health tools

| Product | Strength | Limitation vs BikeMaster |
|---|---|---|
| **MyFitnessPal** | Food tracking, calorie counting | Passive logging, no contextual intelligence |
| **Oura / Whoop** | Sleep, recovery, readiness scores | Single-domain (sleep/recovery), no lifestyle integration |
| **Apple Health** | Data aggregation | Dashboard of numbers, no actionable intelligence |

BikeMaster's distinctive value is the **continuous cycle** across all domains:

```
data → understanding → decision → improvement
```

Cycling is the flagship structured activity, but the system integrates nutrition, sleep, stress, and all lifestyle variables into one coherent health model.

---

## 3. The Four Pillars (Roadmap)

### Pillar 1 — Core BikeMaster (Foundations)
> Goal: be useful with a single ride.

- GPX/FIT import
- Athlete historical database
- Performance analysis
- Metrics (load, fatigue, recovery)
- VAR tracking (energy, macros, hydration, glucose, VO2, breathing, HR, sleep, stress)
- Clear dashboard
- Automatic post-ride report
- Lifestyle data integration (work schedule, family, habits, vices)

Output: *"I did this ride. Here's what it means for my overall health balance."*

### Pillar 2 — Intelligent Coach
- Dynamic athlete profile (cycling + lifestyle)
- Personalized goals
- Adaptive advice across all VARs
- Training plan (cycling as structured activity)
- Micro-corrections (nutrition timing, hydration, sleep optimization)
- AI that explains data in context of full lifestyle

Output: *"Knowing your history, here's what I recommend for your balance."*

### Pillar 3 — Live Assistant
- Voice notifications
- Audio integration
- Ride-time alerts
- Real-time training status
- Real-time lifestyle nudges (hydration, posture, breathing)

Output: *"While you pedal, I guide you. While you live, I keep you balanced."*

### Pillar 4 — Ecosystem
Only after Pillars 1–3 are solid:

- Smartwatch
- Community
- Events
- Advanced safety
- Social
- External integrations (kitchen scale, glucose monitor, sleep tracker)

---

## 4. Central Logic of the System

### 4.1 Main Cycle

```
Data Collection → Athlete State → Decision → Communication → New Feedback → ...
```

### 4.2 Data Collection

The system gathers information from:

**Activity data:**
- distance;
- time;
- speed;
- elevation;
- heart rate;
- power (if available);
- route;
- intensity.

**Athlete state:**
- training history;
- recovery;
- recent load;
- goals;
- available time;
- personal sensations.

**Human feedback:**
After each ride the athlete reports:
- easy;
- normal;
- hard;
- very hard.

And optionally:
- fatigue;
- motivation;
- pains;
- general sensations.

### 4.3 Athlete State Creation

The system does not look at the single workout. It calculates the current state by combining:

- past workouts + time distribution + recovery + personal response

The result is an estimate of present condition:
- current form;
- fatigue level;
- capacity to sustain new load.

### 4.4 Workout Generation

When the user says *"I want to train"*, the system analyzes:
- current state;
- goal;
- available time;
- external conditions;
- history.

Then it generates a concrete workout.

Example:
```
Recommended workout:
40 km
2 hours 40 minutes
average pace 14 km/h
controlled intensity
goal: improve endurance.
```

### 4.5 Dynamic Adaptation

The plan is not fixed. Every event modifies the system:

- skipped ride → load redistribution;
- longer ride than planned → subsequent reduction;
- insufficient recovery → deload;
- improvement → gradual increase.

The system always seeks the best balance.

### 4.6 Load Management

Weekly load can be seen as a distributed objective.

Example:
```
Goal: 150 km in 3 rides.
```

If one ride is reduced:
```
remaining km ÷ available rides = new recommended load.
```

This is the base mathematical level. On top are applied:
- fatigue;
- recovery;
- athlete response.

### 4.7 Proactive Assistant

BikeMaster must not disturb continuously. It must intervene only when message value exceeds the disturbance threshold.

**Not necessary:**
- minor statistics;
- already known information.

**Important:**
- risk;
- insufficient recovery;
- important plan change;
- problems during the ride.

### 4.8 Usage Modes

**Normal mode** — the assistant works in the background:
- analyzes state;
- suggests next rides;
- recommends recovery;
- updates goals.

**Tracking mode** — during the ride:
- GPS;
- navigation;
- voice coach;
- safety;
- live data.

### 4.9 Personal Athlete Model

Over time BikeMaster builds a memory of the user:
- how they recover;
- what loads they can handle;
- how they react to climbs;
- which days are best;
- how performance changes.

Two athletes with identical external data can have different responses because the system accounts for the individual.

---

## 5. Problem Decomposition Approach

Many apparently complex decisions can be broken into smaller problems and solved by combining multiple rules.

Example — *"I skipped a workout, what do I do now?"*

Break it down:

1. **What was planned?**
   - planned km;
   - planned hours;
   - planned intensity.

2. **What did I actually do?**
   - completed km;
   - fatigue;
   - recovery.

3. **How much time remains?**
   - available days;
   - possible rides.

4. **What constraints do I have?**
   - work;
   - weather;
   - tiredness;
   - goal.

Then generate multiple solutions:

**Solution A** — Recover the volume:
> "Let's slightly increase the next rides."

**Solution B** — Don't recover everything:
> "Keep the plan because recovery is more important."

**Solution C** — Change workout type:
> "Instead of more km, let's do a short quality ride."

AI does not need to *invent* the solution: it chooses between predefined strategies using the data.

This concept is powerful for BikeMaster:

- mathematical rules for the certain part;
- algorithms to optimize;
- AI to explain, choose, and communicate.

A good digital coach can be built exactly this way: many small connected reasonings that together solve bigger problems.

The system can create multiple combinations and adapt to what the user can actually do.

---

## 6. The Core Problem

The question is not only *"How much did you do?"* but *"How much did it cost you?"*

Two athletes with identical external data can have completely different responses. The system must learn the personal relationship between stimulus and response.

Over time BikeMaster learns:

- "When this athlete does 60 km with 800 m of climbing, they recover in 48 hours."
- "When they exceed 3 consecutive intense days, performance drops."
- "After a light week they respond better to long workouts."
- "When they sleep less than 6 hours, their food tolerance changes."
- "On high-stress work days, the same ride costs more recovery."

This is the difference between an activity database and a **true person model**: it doesn't just store events, it learns the relationship between load, lifestyle, and individual response.

---

## 7. Business Model

| Free | Premium |
|---|---|
| Import activities | AI Coach |
| Basic statistics | Adaptive plan |
| Some advice | Full history |
| | Advanced analysis |
| | Voice |
| | Safety |

The value is not in GPS tracking (that already exists). The value is: *"It helps me improve."*

---

## 8. Final Evaluation

| Criterion | Score |
|---|---|
| As an idea | 9/10 |
| Differentiation potential | 9.5/10 |
| Technical difficulty | 8/10 |
| First solo-product potential | 8/10 (cycling is the structured entry point; lifestyle expands the moat) |

The sentence that summarizes the project:

> "Strava records what you did. BikeMaster tries to understand what you should do next — not just on the bike, but in your whole life."

The challenge is not having 100 features, but demonstrating that the cycle:

```
data → understanding → advice → improvement
```

actually works for the first users, starting with cycling as the structured activity domain.

---

## 9. Conceptual Architecture

```
Dati → Analisi → Stato persona → Decisione → Comunicazione → Nuovo feedback
```

The system becomes a continuous cycle:

```
Training (structured activity)
    ↓
Measurement (VARs from sensors + lifestyle)
    ↓
Understanding (metabolic signature interpretation)
    ↓
Adaptation (micro-corrections + dynamic training)
    ↓
Balance (equilibrio metabolico)
    ↓
New training
```

### 9.1 Health Balance Operational Cycle

Every day the system:

1. **Analizza** ciò che scegli di mangiare → *Analisi_cibo*
2. **Consiglia** la quantità compatibile → *Quantita_compatibile*
3. **Propone** micro-correzioni intelligenti → *Correzione_micro*
4. **Calcola** la quantità giusta di movimento → *Allenamento_dinamico*
5. **Bilancia** le VAR per riportarti in equilibrio → *Equilibrio_metabolico*

### 9.2 Feedback and Direct Measurements

The system becomes personal through:

- **Feedback_personale** — perceptions, sensations, preferences
- **Misurazioni_dirette** — sensors, devices, labs

So it understands: how you react, how you feel, how your energy varies, how your general state changes. And it adapts everything.

### Final Objective

Transform BikeMaster from a simple ride recorder into:

> **A personal lifestyle health intelligence system that knows the person, understands their metabolic signature, and guides them toward dynamic equilibrium — with cycling as the structured activity anchor.**
