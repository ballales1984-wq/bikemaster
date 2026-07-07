# Vercel (Frontend Only)

Use Vercel to serve the static Vue build. The backend remains hosted elsewhere (Railway or Fly).

## Setup

1. Push the repo to GitHub/GitLab.
2. In Vercel, create a new project from the repo.
3. Set **Root Directory** to `frontend`.
4. Build command: `npm run build`.
5. Output directory: `dist`.
6. Environment variable:
   - `VITE_API_BASE_URL=https://<backend-url>/api/v1`

## Notes

- The Dockerfile multi-stage build still produces a self-contained image for Render/Railway/Fly. Vercel builds only the frontend.
- If you want a single-url experience, put Vercel in front and use rewrites/proxies to forward `/api/v1/**` to the backend host.

## Static export

Vue Vite build already produces a static `dist/`. No extra runtime is required on Vercel.
