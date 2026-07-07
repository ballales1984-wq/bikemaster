# BikeMaster Helm Chart

Deploy BikeMaster on Kubernetes using this Helm chart.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.x
- A container registry with the BikeMaster image built from the multi-stage `Dockerfile`

## Install

```bash
helm repo add bikemaster ./docker/helm/bikemaster
helm install bikemaster bikemaster/bikemaster \
  --set image.repository=<your-registry>/bikemaster \
  --set image.tag=<tag> \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=bikemaster.example.com
```

## PostgreSQL and Redis

This chart does **not** install PostgreSQL or Redis for you. Provide them via:

- Bitnami charts (recommended for quick setup):
  ```bash
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm install postgres bitnami/postgresql \
    --set auth.username=bikemaster \
    --set auth.database=bikemaster \
    --set auth.password=CHANGE_ME \
    --set primary.persistence.size=10Gi

  helm install redis bitnami/redis \
    --set architecture=standalone \
    --set auth.enabled=false \
    --set master.persistence.size=2Gi
  ```
- Managed services (AWS RDS, Google Cloud SQL, Azure Database)

After provisioning, set `DATABASE_URL` and `REDIS_URL` via `helm install --set env`.

## Values

See `values.yaml` for all configurable options:

- `image.repository`, `image.tag`, `image.pullPolicy`
- `replicaCount`
- `service.type`, `service.port`
- `ingress.enabled`, `ingress.className`, `ingress.hosts`
- `resources.limits` / `resources.requests`
- `autoscaling.enabled`
- `env` list of environment variables

## Resource limits

Recommended defaults:

- CPU request: `200m`
- CPU limit: `1000m`
- Memory request: `256Mi`
- Memory limit: `512Mi`

## Health

Liveness and readiness probes target `/api/v1/health`.
