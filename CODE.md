# Codebase Map

This document summarizes key components and conventions.

## Backend (FastAPI)
- `src/mcp_ingest/main.py`: API entry with admin routes, graph endpoints, search, chat, KV, connectivity tests, and streaming migration v2.
- `src/mcp_ingest/db_async.py`: Async SQLAlchemy models (repositories, embeddings, files, chunks) and DB helper.
- `src/graph_clients/base.py`: Graph backends (Neo4j, TerminusDB, Nebula) + `select_backend` helper.
- `src/sync/pg_to_terminus.py`: v1 repo migration (legacy).
- `src/sync/pg_to_terminus_v2.py`: v2 migration (repos/files/chunks/embeddings) with dry-run and idempotent upserts.
- `src/sync/terminus_schema.py`: Minimal TerminusDB schema initializer.
- `src/agents/validator.py`: Graph/DB integrity validator.

## Web Console (Next.js)
- `webapp/pages/*`: Dashboard, Settings, Graph, Agents (stub), Reports (stub), Chat, Admin.
- `webapp/components/*`: Layout, GraphView (Cytoscape-based).
- `webapp/lib/api.js`: API helpers + streaming `apiStream`.
- `webapp/lib/templates.js`: Per-backend query templates.
- Styling via Tailwind/DaisyUI (see `webapp/styles.css`).

## Infra
- Ansible: render env from Cloudflare KV; build/start stack; optional systemd; checks.
- Terraform/Pulumi: Cloudflare DNS + Tunnel + KV namespace + generated secrets.
- Compose: `infra/compose/docker-compose.prod.yml` (api, web, cloudflared).

## Observability
- Request IDs (X-Request-ID), structured logs (structlog), optional Sentry/OTel.
- Rate limits (slowapi) on admin-sensitive routes.
- `/metrics` (Prometheus): counters for graph tests, migration runs, admin actions.

## Conventions
- Admin-only mutations; JWT-based auth, role gating, rate-limits.
- Prefer dry-run + streaming progress for long-running tasks.
- Secrets centrally managed via Cloudflare KV; API reads server-side.

