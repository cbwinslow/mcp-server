# AI Stack & Agents

## LlamaIndex
- Vector store: Postgres pgvector via `llama-index-vector-stores-postgres`
- Graph store: Neo4j via `llama-index-graph-stores-neo4j`
- Pipeline helper: `src/mcp_ingest/llama_pipeline.py`
- MCP API `/search` uses a LlamaIndex VectorStoreIndex; hybrid merges with pg_trgm.

## Graphiti MCP (Temporal Memory)
- Run Graphiti MCP (`install_graphiti_mcp.sh`) at `:8000/sse`.
- Tools:
  - `graphiti_add_memory`, `graphiti_search_nodes`, `graphiti_search_facts`, `graphiti_get_episodes`, `graphiti_clear_graph`
  - Generic: `graphiti_mcp_jsonrpc` (JSON‑RPC) and experimental SSE client.

## Crawl4AI MCP
- `install_mcp_crawl4ai_rag.sh` (SSE `:8051/sse`). MCP API `/crawl` proxies to it.
- Crew tools: `mcp_api_crawl` (proxy) and `crawl_to_graphiti` (transform to episodes).

## CrewAI configs
- `config/crewai_graphiti.yaml`: Crawl → Episodes → Verify pipeline.
- `config/crewai_kg.yaml`: KG architect/extractor/sync/auditor for Neo4j.

## Quick Routines
- Fast ingest (no LLM planning): `scripts/agents/fast_graphiti_ingest.py`
- Repo → KG (code): `scripts/ingest/repo_to_kg.py`

