# Deployment

## Docker

```bash
docker compose up -d
```

- Multi-stage hardened build
- Non-root user, read-only fs, no-new-privileges, healthcheck

## Render

- `render.yaml` present in repo root

## Fly.io

- See `docker/deploy/flyio.md`

## Railway

- See `docker/deploy/railway.md`

## Vercel

- See `docker/deploy/vercel.md`

## Kubernetes

- Helm chart at `docker/helm/bikemaster/`

## Environment Variables

See [configuration.md](./configuration.md).
