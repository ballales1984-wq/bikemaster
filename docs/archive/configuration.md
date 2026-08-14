# Configuration

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./rides.db` | Database connection |
| `DATABASE_URL_ASYNC` | `sqlite+aiosqlite:///./rides.db` | Async engine URL |
| `API_HOST` | `0.0.0.0` | API server host |
 | `API_PORT` | `8001` | API server port |
| `SECRET_KEY` | *(required in prod)* | JWT signing key (32+ chars) |
| `SECRET_KEY_PREVIOUS` | — | Previous key for rotation |
| `ENVIRONMENT` | `development` | Environment mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `GROQ_API_KEY` | — | Groq LLM API key |
| `REDIS_URL` | — | Redis connection URL |
| `SENTRY_DSN` | — | Sentry error tracking |
| `STRAVA_CLIENT_ID` | — | Strava OAuth client ID |
| `STRAVA_CLIENT_SECRET` | — | Strava OAuth secret |
| `STRAVA_REDIRECT_URI` | `http://localhost:8001/api/v1/import/strava/callback` | Strava callback |
| `GARMIN_CONSUMER_KEY` | — | Garmin OAuth key |
| `GARMIN_CONSUMER_SECRET` | — | Garmin OAuth secret |
| `GOOGLE_FIT_CLIENT_ID` | — | Google Fit OAuth client ID |
| `GOOGLE_FIT_CLIENT_SECRET` | — | Google Fit OAuth secret |
| `GOOGLE_MAPS_API_KEY` | — | Google Static Maps API key |
| `WEATHER_API_KEY` | — | OpenWeatherMap API key |

## Configuration Flow

All configuration flows through `bike_analyzer/backend/settings.py` (`get_settings()`) and `os.getenv`. Legacy `backend/config.py` was removed in v1.4.1.
