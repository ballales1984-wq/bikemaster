# BikeMaster — Central Logic & Product Vision

> **Version:** 1.0.0
> **Date:** 2026-07-16
> **Status:** Definitive — central point of the project

For technical architecture, see [MASTER.md](./MASTER.md). For roadmap phases, see [ROADMAP.md](../ROADMAP.md).

---

## 1. Strategic Positioning

BikeMaster does not compete with Strava, Garmin, or TrainingPeaks. It positions itself as an **intelligence layer above the tools the cyclist already uses**.

> "You already have all your data. Now let's turn it into useful advice."

This choice:
- eliminates the onboarding barrier (the user does not have to start from zero);
- allows focus on unique value instead of rebuilding existing functionality.

---

## 2. Differentiation vs Existing Products

| Product | Strength | Limitation vs BikeMaster |
|---|---|---|
| **Strava** | Community, segments, user habit, massive database | Still shows *what you did*, not *what you should do* |
| **Garmin** | Hardware, sensors, smartwatches, physiological data | Technical experience, not conversational |
| **TrainingPeaks** | Structured workouts, coaches | Rigid, oriented toward athletes who want to follow a fixed program |

BikeMaster's distinctive value is the **continuous cycle**:

```
data → understanding → decision → improvement
```

---

## 3. The Four Pillars (Roadmap)

### Pillar 1 — Core BikeMaster (Foundations)
> Goal: be useful with a single ride.

- GPX/FIT import
- Athlete historical database
- Performance analysis
- Metrics (load, fatigue, recovery)
- Clear dashboard
- Automatic post-ride report

Output: *"I did this ride. Here's what it means."*

### Pillar 2 — Intelligent Coach
- Dynamic athlete profile
- Personalized goals
- Adaptive advice
- Training plan
- AI that explains data

Output: *"Knowing your history, here's what I recommend."*

### Pillar 3 — Live Assistant
- Voice notifications
- Audio integration
- Ride-time alerts
- Real-time training status

Output: *"While you pedal, I guide you."*

### Pillar 4 — Ecosystem
Only after Pillars 1–3 are solid:

- Smartwatch
- Community
- Events
- Advanced safety
- Social

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

This is the difference between an activity database and a **true athlete model**: it doesn't just store events, it learns the relationship between load and individual response.

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
| As an idea | 8.5/10 |
| Differentiation potential | 9/10 |
| Technical difficulty | 8/10 |
| First solo-product potential | 7/10 (requires careful choice of the first piece) |

The sentence that summarizes the project:

> "Strava records what you did. BikeMaster tries to understand what you should do next."

The challenge is not having 100 features, but demonstrating that the cycle:

```
data → understanding → advice → improvement
```

actually works for the first users.

---

## 9. Conceptual Architecture

```
Dati → Analisi → Stato atleta → Decisione → Comunicazione → Nuovo feedback
```

The system becomes a continuous cycle:

```
Training
   ↓
Measurement
   ↓
Understanding
   ↓
Adaptation
   ↓
New training
```

### Final Objective

Transform BikeMaster from a simple ride recorder into:

> **A personal digital coach that knows the athlete, understands the present situation, and guides them on the improvement path.**
