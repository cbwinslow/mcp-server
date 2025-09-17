# Host-Native (No Docker) Deployment Plan

This guide aligns with a lean, host-native setup on Ubuntu without containers.

## Components
- PostgreSQL 16 + pgvector (via Pigsty or apt) — primary datastore
- Neo4j 5 Community + APOC — knowledge graph
- n8n (Node workflow engine) — glue automation
- LocalAI — OpenAI-compatible local inference endpoint
- PostgREST — REST interface to Postgres (Supabase-like capability)
- Monitoring Stack — Grafana, Prometheus, Loki, Promtail, Node Exporter

Optional later: Supabase extras (Auth/Storage/Studio) via native installs; Kong gateway.

## Install order
1) Base: `scripts/install/ubuntu/setup_base.sh`
2) PostgreSQL + pgvector: `infra/pigsty` (Pigsty) or apt + `CREATE EXTENSION vector;`
3) Neo4j: `scripts/install/ubuntu/install_neo4j.sh`
4) LocalAI: `scripts/install/ubuntu/install_localai.sh`
5) n8n: `scripts/install/ubuntu/install_n8n.sh`
6) PostgREST: `scripts/install/ubuntu/install_postgrest.sh`
7) Monitoring: `scripts/install/ubuntu/install_monitoring.sh`

## Configuration notes
- DATABASE_URL for your app: `postgresql+asyncpg://mcp_app:<pass>@127.0.0.1:5432/mcp`
- LocalAI endpoint: `http://127.0.0.1:8080/v1` (set as OpenAI base URL)
- n8n UI: `http://127.0.0.1:5678` (secured behind SSH tunnel or reverse proxy)
- Neo4j: Bolt `bolt://127.0.0.1:7687`, Browser `http://127.0.0.1:7474`
- Grafana: `http://127.0.0.1:3000` (admin:admin by default; change password)

## Security quick wins
- Bind admin UIs to localhost only; access via SSH tunnel or a small reverse proxy on LAN.
- Rotate DB roles and JWT secrets; restrict n8n credentials.
- Use UFW rules; fail2ban optional.

