# Deployment

Vedi [deployment-plan.md](./deployment-plan.md) per il piano di deployment completo.

## Docker

```bash
docker compose up -d
```

- Multi-stage hardened build
- Non-root user, read-only fs, no-new-privileges, healthcheck

## Render

- `render.yaml` presente nella repo root
- Configurazione in [deployment-plan.md](./deployment-plan.md)

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
