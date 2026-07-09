# Railway

## Backend (FastAPI + Docker)

1. Push this repo to GitHub/GitLab.
2. In Railway, create a new project and select your repo.
3. Add a service, choose **Docker** as the source.
4. Set root directory to `/`.
5. Add a **PostgreSQL** plugin — Railway will inject `DATABASE_URL`.
6. Add **Redis** plugin (optional but recommended). Railway will inject `REDIS_URL`.
7. Add environment variables:
   - `SECRET_KEY` (generate a strong random string)
   - `DATABASE_URL` (from PostgreSQL plugin)
   - `REDIS_URL` (from Redis plugin)
   - `AI_COACH_MODE=external`
   - `GROQ_API_KEY` (unica chiave AI attiva)
8. Deploy. Railway exposes the service via a public URL automatically.

No extra files needed if your root `Dockerfile` is up to date.

## Frontend (Vercel)

1. Create a new Vercel project importing the same repo.
2. Set **Root Directory** to `frontend`.
3. Add an environment variable pointing to the backend:
   - `VITE_API_BASE_URL=https://<railway-backend-url>/api/v1`
4. Build command: `npm run build`
5. Output directory: `dist`

Vercel serves the static bundle. The browser calls the backend directly via the API base URL.
