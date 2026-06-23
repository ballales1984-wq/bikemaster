# Changelog

## v1.2.0 (2026-06-23)

### Added
- Test coverage improvements for analytics modules (performance, power_model, training_load, training_stress, advanced)
- Edge case tests for GPS processing functions (analyze_historical_trend, detect_speed_surges, calculate_heart_rate_zones, calculate_ride_recommendation_score)
- Tests for knowledge_base embeddings (`init_kb_embeddings` with local fallback)
- Tests for `compute_ctl_atl_tsb_external` function

### Fixed
- Added missing `Ride` import to test_processing.py
- Test suite stability improvements

### Technical Details
- Coverage: ~90% on core analytics modules
- All 880+ tests passing with mock mode for AI Coach

---

## v1.1.0

### Added
- Clean Architecture with Core domain layer (models, pipeline, engine, fitness_state.py)
- Calculators/Services/Repositories separation in analytics
- Domain Events (RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated)
- Traffic Safety Module with risk score computation
- Strava Integration with OAuth2 + PKCE + batch import
- Garmin Connect Integration
- Vector Database (PGVector wrapper with TF-IDF fallback)
- Google OAuth2 authentication
- Security hardening (CSP, HSTS, X-Frame-Options, rate limiting)

---

## v1.0.0

### Initial Release
- GPX/FIT parsing and GPS processing
- Performance scoring engine (Performance, Endurance, Fatigue, Recovery, Efficiency)
- Benchmark percentile comparisons
- Calorie estimation (physics + MET)
- Charts and maps (Folium, Google Static Maps, OSM)
- Training Stress Score (TSS) and Training Load calculations
- Badge system and GPS heatmap
- Granfondo planner with tapering
- Weather service integration
- Calendar events for scheduled workouts
- Knowledge Base with BM25 ranking
- AI Coach with Groq/OpenAI/Ollama support
- Frontend Vue 3 + Vite + TypeScript SPA
- PWA support with service worker
- Android app with Capacitor