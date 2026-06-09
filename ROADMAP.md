# BikeMaster - Roadmap Completa

## Stato Attuale

**Completati: 145/145 step base + 20/80 estensioni**

### ✅ Completati di recente
- [x] 146. Pydantic Settings v2 (`pydantic-settings`) — type-safe config layer
- [x] 148. Environment validation all'avvio — SECRET_KEY obbligatoria in prod
- [x] 191. SECRET_KEY hardening con rotazione (SECRET_KEY + SECRET_KEY_PREVIOUS)
- [x] 192. Security headers middleware (CSP, X-Frame-Options, HSTS, XSS)
- [x] 196. Environment validation con ENVIRONMENT detection (dev vs prod)
- [x] 149. Alembic configurato per migrazioni SQLite/PostgreSQL
- [x] 150-151. Modelli SQLAlchemy ORM + async_db.py (asyncpg/aiosqlite)
- [x] 157-158. Compressione GPS + Indicizzazione ottimizzata (già presente)
- [x] 242. Migrazione iniziale Alembic: `08ee39bfe529_initial_models.py`
- [x] 14 nuovi modelli matematici in `advanced.py` (power, VO2max, climb, pace, ecc.)
- [x] `endurance-metrics` integrato come adapter opzionale

### In corso
- [ ] 15 nuovi test nel modulo `advanced.py` — 25/25 passano
- [ ] 203. Multi-utente completo (in design)

---

## **FASE 14 - Architettura & Configurazione Robusta** *(Alta Priorità)*

### Configurazione
- [ ] 146. Migrare a Pydantic Settings v2 (`pydantic-settings`) invece di dotenv manuale
- [ ] 147. Centralizzare tutte le costanti e settings in un singolo modulo
- [ ] 148. Aggiungere validazione environment variables all'avvio

### Database
- [ ] 149. Introdurre Alembic per migrazioni database versionate
- [ ] 150. Aggiungere supporto PostgreSQL con fallback SQLite
- [ ] 151. Implementare async SQLAlchemy (asyncpg)

### Codice
- [ ] 152. Ristrutturazione secondo Clean Architecture (services, repositories, use_cases)
- [ ] 153. Dependency injection più strutturata con `Depends`
- [ ] 154. Type hints completi ovunque + mypy configuration
- [ ] 155. Linting automatico: Ruff + Black + pre-commit hooks
- [ ] 156. Logging centralizzato e strutturato (JSON per produzione)

---

## **FASE 15 - Database & Scalabilità** *(Alta Priorità)*

- [ ] 157. Compressione GPS points (Douglas-Peucker) per ridurre dimensione DB
- [ ] 158. Indicizzazione ottimizzata su `date`, `athlete_id`, `distance_km`, `elevation_gain_m`
- [ ] 159. Aggiungere Redis per cache e rate limiting avanzato
- [ ] 160. Background tasks per operazioni pesanti (import batch, generazione mappe)
- [ ] 161. Connection pooling per database

---

## **FASE 16 - Frontend Moderno** *(Alta Priorità)*

- [ ] 162. Setup Vue 3 + Vite + TypeScript come SPA
- [ ] 163. Dark/Light theme toggle
- [ ] 164. Grafici interattivi con Chart.js o Plotly (sostituire Matplotlib statici)
- [ ] 165. Componenti riutilizzabili e state management (Pinia)
- [ ] 166. Progressive Web App (PWA) per installazione smartphone
- [ ] 167. Mobile-first responsive design
- [ ] 168. Completare app Android nella cartella `android/`

---

## **FASE 17 - Funzionalità Analytics Avanzate** *(Media Priorità)*

### Integrazioni
- [ ] 169. Integrazione Strava API (import/export attività)
- [ ] 170. Integrazione Garmin Connect
- [ ] 171. Integrazione Wahoo

### Power & Training Metrics
- [ ] 172. Modello di potenza avanzato con dati power meter FIT
- [ ] 173. Normalized Power (NP) — algoritmo Coggan
- [ ] 174. Intensity Factor (IF) e Variability Index (VI)
- [ ] 175. Efficiency Factor (EF) per cardio drift detection
- [ ] 176. TRIMP — Training Impulse da HR data
- [ ] 177. ACWR — Acute:Chronic Workload Ratio
- [ ] 178. Ramp Rate — velocità di caricamento fitness
- [ ] 179. Decoupling analysis — scompenso aerobico

### Segment Detection
- [ ] 180. Segment detection più intelligente (confronto con segmenti Strava)
- [ ] 181. Climb categorization migliorata (superficie, pendenza media vs max)

### Esportazione
- [ ] 182. Esportazione TCX
- [ ] 183. Esportazione FIT
- [ ] 184. PDF report professionali con grafice e tabelle

---

## **FASE 18 - AI Coach Avanzato** *(Media Priorità)*

- [ ] 185. Vector Database (Chroma, PGVector o Qdrant) per RAG più potente
- [ ] 186. Tool calling / function calling con Groq o OpenAI
- [ ] 187. Memory persistente delle conversazioni per utente
- [ ] 188. Personalizzazione basata su storico completo dell'atleta
- [ ] 189. Voice input/output (opzionale)
- [ ] 190. Prompt engineering avanzato con few-shot examples

---

## **FASE 19 - Sicurezza & Produzione** *(Alta Priorità)*

- [ ] 191. Gestione sicura di SECRET_KEY (rotazione, non-generazione in produzione)
- [ ] 192. HTTPS obbligatorio, CSP headers, security middleware
- [ ] 193. Rate limiting per utente (non solo globale)
- [ ] 194. Backup automatici crittografati e scheduled
- [ ] 195. Docker multi-stage ottimizzato + security scan
- [ ] 196. Environment variables validation all'avvio migliorata

---

## **FASE 20 - Testing & DevOps** *(Media Priorità)*

- [ ] 197. Aumentare coverage test a >90%
- [ ] 198. Integration tests con pytest + TestClient
- [ ] 199. E2E tests con Playwright
- [ ] 200. GitHub Actions: lint, test, build Docker, deploy preview
- [ ] 201. Monitoring: Prometheus + Grafana o Sentry per errori
- [ ] 202. Documentazione API completa con Swagger + Redoc personalizzato

---

## **FASE 21 - Deployment & Distribuzione** *(Bassa Priorità)*

- [ ] 203. Supporto multi-utente completo (attualmente single-user oriented)
- [ ] 204. Versione cloud hosted (opzionale, per monetizzazione)
- [ ] 205. Helm chart per Kubernetes
- [ ] 206. One-click deploy su Railway, Fly.io, Vercel (frontend)

---

## **FASE 22 - Community & Monetization** *(Bassa Priorità)*

### Documentazione
- [ ] 207. Aggiornare README con screenshot, demo video, badge di stato
- [ ] 208. API documentation esterna (ReadTheDocs o MkDocs)
- [ ] 209. Esempi di contribuzione + template per nuove feature
- [ ] 210. Roadmap pubblica più dettagliata con issues collegate

### Features Extra
- [ ] 211. Plugin system per nuovi analizzatori o fonti dati
- [ ] 212. Confronto tra atleti (condivisione anonima benchmark)
- [ ] 213. Gamification: badge, challenges, streak
- [ ] 214. Social features: condivisione uscite (con privacy)
- [ ] 215. Mobile-first redesign completo

---

## **Priorità Consigliate (Prime 5 da implementare)**

| Priorità | Feature | Impatto | Difficoltà |
|:---:|---|---|:---:|
| **1** | Pydantic Settings + Config robusta | Alto | Bassa |
| **2** | Miglioramento Frontend (Vue 3 + Vite) | Alto | Media |
| **3** | Sicurezza SECRET_KEY + production hardening | Alto | Bassa |
| **4** | PostgreSQL + Alembic | Alto | Media |
| **5** | Redis + Background Tasks | Medio-Alto | Media |

---

*Ultimo aggiornamento: 2026-06-09*
