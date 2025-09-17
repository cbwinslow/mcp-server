# Security Guide

## Authentication
- MCP API can require JWT (`REQUIRE_AUTH=true`).
- Tokens validated with HS256 using `GOTRUE_JWT_SECRET` (from GoTrue) or `JWT_SECRET`.

## Network Binding
- Bind admin UIs to `127.0.0.1` (Neo4j Browser, Grafana) or protect with reverse proxy + auth.
- UFW: allow 22/80/443; keep DB/graph/admin on localhost.

## Secrets
- Store secrets in root‑owned env files (`/etc/*`) with `0600` permissions.
- Avoid committing secrets. Use Bitwarden/1Password or SOPS for versioned secrets.

## Authorization & Writes
- Graph writes via `/graph/query` require `ALLOW_GRAPH_WRITES=true`.
- Limit who can set/modify service env files.

## TLS
- If exposing beyond LAN, terminate TLS at a reverse proxy (Caddy, nginx) or Kong.

