# Quickstart

This guide covers a complete, host‑native setup on Ubuntu 22.04/24.04 to run:

- MCP API (FastAPI) backed by Postgres + pgvector
- Neo4j + APOC for the knowledge graph
- Supabase Auth (GoTrue) for JWT
- LlamaIndex hybrid search
- Graphiti MCP (temporal memory)
- Crawl4AI MCP for crawling
- CrewAI agents/pipelines and scheduled jobs

## 1) Prerequisites

```bash
sudo bash scripts/install/ubuntu/setup_base.sh
```

## 2) Database (choose one)

Pigsty (recommended):

```bash
cd infra/pigsty
./bootstrap_pigsty.sh
export PSQL_URL=postgres://postgres:postgres@127.0.0.1:5432/postgres
./apply_sql.sh
```

APT alternative:

```bash
sudo bash scripts/install/ubuntu/install_postgres_apt.sh
```

## 3) Auth & Graph

```bash
sudo bash scripts/install/ubuntu/install_gotrue.sh
sudo bash scripts/install/ubuntu/install_neo4j.sh
```

Edit `/opt/gotrue/gotrue.env` → set `GOTRUE_JWT_SECRET`, then restart `gotrue`.

## 4) MCP API (Postgres only)

```bash
DATABASE_URL=postgresql+asyncpg://mcp_app:<pass>@127.0.0.1:5432/mcp \
GOTRUE_JWT_SECRET=<secret> REQUIRE_AUTH=true NEO4J_PASSWORD=<pwd> \
sudo bash scripts/install/ubuntu/install_mcp_api.sh
```

Endpoints:
- `POST /admin/index` — index texts into pgvector
- `POST /search` — vector/hybrid search
- `POST /crawl` — crawl proxy to Crawl4AI
- `POST /graph/query` — Cypher (writes gated)
- `POST /graph/traverse` — safe graph traversals
- `GET /graph/insights` — label/edge/top‑degree/dangling

## 5) MCP Services

```bash
sudo bash scripts/install/ubuntu/install_mcp_crawl4ai_rag.sh   # :8051/sse
sudo bash scripts/install/ubuntu/install_graphiti_mcp.sh       # :8000/sse
# Optional HTTP shim for Graphiti
sudo bash scripts/install/ubuntu/install_graphiti_http_shim.sh # :8052
```

## 6) Search sanity check

```bash
JWT=<token>
curl -H "Authorization: Bearer $JWT" \
  -X POST http://127.0.0.1:8000/admin/index \
  -H 'Content-Type: application/json' \
  -d '{"texts":["Hello graph world"],"collection":"mcp_chunks"}'

curl -H "Authorization: Bearer $JWT" \
  -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"graph","hybrid":true,"top_k":5,"collection":"mcp_chunks"}'
```

## 7) Graphiti pipeline (Crew)

```bash
export GRAPHITI_MCP_SSE_URL=http://127.0.0.1:8000/sse
export NEO4J_URI=bolt://127.0.0.1:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=<pwd>
export MCP_API_BASE=http://127.0.0.1:8000 # and MCP_JWT if protected
export TARGET_URL=https://fastapi.tiangolo.com/
python scripts/agents/run_graphiti_pipeline.py
```

## 8) Fast “crawl → episodes → verify” (no LLM planning)

```bash
export TARGET_URLS=https://fastapi.tiangolo.com/,https://docs.python.org/3/
export GROUP_ID=default
export GRAPHITI_MCP_SSE_URL=http://127.0.0.1:8000/sse
export NEO4J_URI=bolt://127.0.0.1:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=<pwd>
python scripts/agents/fast_graphiti_ingest.py
```

## 9) Scheduling

```bash
sudo bash scripts/install/ubuntu/install_fast_graphiti_ingest_timer.sh
sudo bash scripts/install/ubuntu/install_repo_kg_timer.sh
```

Edit `/etc/fast-graphiti.env` and `/etc/repo-kg.env` to set URLs and credentials.

## More docs
- docs/CONFIG.md — environment variables and configuration
- docs/OPERATIONS.md — daily ops, logs, services, troubleshooting
- docs/SECURITY.md — auth, binding, secrets, practices
- docs/SCHEDULING.md — timers and schedules
- docs/AI-STACK.md — agents, tools, retrieval & KG strategy

