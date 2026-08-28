# ECLAIR — nginx Reverse Proxy

> Derived only from the Spec (§M18, §1 folder structure, §4.10) and the repository. Owned by **M18**
> (Evaluation, Benchmarking & Deployment). No invented configuration. Read
> `rules/M18_evaluation_deployment.md` and `docs/deployment/docker.md` first.

## Purpose
nginx acts as the reverse proxy in front of the ECLAIR services in the Dockerized deployment
(Spec §M18 deployment scope, §1 folder structure).

## Files (Spec §1)
```
deployment/nginx/
  nginx.conf   # reverse-proxy configuration
  README.md    # this file
```

## Role in the deployment
- Sits in front of the API image (`Dockerfile.api`, M15) and the dashboard image
  (`Dockerfile.dashboard`, M17) composed by the root `docker-compose.yml`.
- Provides a single entry point / routing layer for the REST API and dashboard.

## Constraints (Spec §4.10)
- Part of the approved Docker / Docker Compose deployment. Do **not** introduce Kubernetes, a service
  mesh, or paid observability platforms in Prototype v1.
- nginx configuration must only route to the services that actually exist in the compose file
  (API, dashboard, worker) — do not invent upstreams.

## Status
`nginx.conf` is a placeholder on the `Rules` branch (no configuration yet). Its concrete contents are
delivered by M18 as part of the deployment module. This README defines the file's purpose; it does
not invent the proxy configuration.
