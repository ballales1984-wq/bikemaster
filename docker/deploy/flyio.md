# Fly.io

## Backend

1. Install `flyctl` and log in.
2. From the repo root, run `fly launch`.
3. Choose a name and region. Accept the default Dockerfile detection.
4. Add a Postgres cluster: `fly postgres create --name bikemaster-db`.
5. Attach it: `fly postgres attach -a bikemaster bikemaster-db`. `DATABASE_URL` is injected.
6. Add Redis: `fly redis create` and attach, or set `REDIS_URL` manually.
7. Set secrets:
   ```
   fly secrets set SECRET_KEY="$(openssl rand -hex 32)" AI_COACH_MODE=external
   ```
8. Deploy:
   ```
   fly deploy
   ```

Frontend files are baked into the image by the Dockerfile, so Vercel is not needed if you serve from the same container.

## Vercel (Frontend alternative)

If you prefer Vercel for the frontend:

1. Import the repo in Vercel.
2. Root Directory: `frontend`.
3. Build command: `npm run build`.
4. Output directory: `dist`.
5. Environment: `VITE_API_BASE_URL=https://<your-fly-app>.fly.dev/api/v1`.

Notes:
- Make sure CORS/backend origins allow the Vercel domain if you enforce host checks.
- This keeps the lightweight static assets on Vercel CDN and the Python backend on Fly.
