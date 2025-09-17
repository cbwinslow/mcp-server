# Configuration Reference

This file documents important environment variables and configuration knobs.

## MCP API (FastAPI)
- `DATABASE_URL` (required): Postgres URL, asyncpg. Example: `postgresql+asyncpg://mcp_app:pass@127.0.0.1:5432/mcp`
- `REQUIRE_AUTH` (default: false): If true, require JWT on API.
- `GOTRUE_JWT_SECRET` or `JWT_SECRET`: HS256 secret used to verify JWT when `REQUIRE_AUTH=true`.
- `NEO4J_URI` (default: `bolt://127.0.0.1:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASSWORD` (required): Neo4j password.
- `ALLOW_GRAPH_WRITES` (default: false): Allow `mode=write` on `/graph/query`.
- `MCP_CRAWL4AI_URL` (default: `http://127.0.0.1:8051`): Upstream crawl server for `/crawl` proxy.

## GoTrue (Supabase Auth)
- `GOTRUE_JWT_SECRET` (required): Shared secret for HS256 JWTs.
- `GOTRUE_API_HOST` (default: 127.0.0.1), `GOTRUE_API_PORT` (default: 9999)

## Neo4j
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Connection.
- Memory tuning in `/etc/neo4j/neo4j.conf` set by installer.

## Graphiti MCP (JSON‑RPC over HTTP + SSE)
- `GRAPHITI_MCP_SSE_URL` (default: `http://127.0.0.1:8000/sse`)
- `GRAPHITI_MCP_POST_URL` (optional): If not set, derived from SSE URL (replace `/sse` with `/messages`).
- `GRAPHITI_MCP_AUTH` (optional): Authorization header value for Graphiti MCP.

## Crawl4AI MCP
- Typically no env here; configure in MCP API: `MCP_CRAWL4AI_URL`.

## CrewAI tools
- Graphiti wrapped tools use Graphiti MCP env vars listed above.
- `MCP_API_BASE` (default: `http://127.0.0.1:8000`) and optional `MCP_JWT` used by tools that call MCP API.

## Schedulers
### Fast Graphiti Ingest
File: `/etc/fast-graphiti.env`
- `TARGET_URLS` (comma‑separated) or `TARGET_URL`
- `GROUP_ID` (default: `default`)
- `CRAWL_DEPTH` (default: 1), `CRAWL_MAX_PAGES` (default: 3)
- `BATCH_BY_DOMAIN` (default: true), `MAX_ITEMS` (default: 20), `BODY_CHARS` (default: 3000)
- `MCP_API_BASE`, optional `MCP_JWT`
- Graphiti/Neo4j: `GRAPHITI_MCP_SSE_URL`, `NEO4J_URI/USER/PASSWORD`

### Repo → KG Batch
File: `/etc/repo-kg.env`
- `REPO_URLS` (comma‑separated)
- `NEO4J_URI/USER/PASSWORD`
- `GROUP_ID` reserved (future use)

