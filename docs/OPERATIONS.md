# Operations Guide

## Services
- MCP API: `systemctl status mcp-api`
- GoTrue: `systemctl status gotrue`
- Neo4j: `systemctl status neo4j`
- Crawl4AI MCP: `systemctl status mcp-crawl4ai-rag`
- Graphiti MCP: `systemctl status graphiti-mcp`
- Graphiti HTTP shim (optional): `systemctl status graphiti-http`

## Logs
`journalctl -u <service> -n 200 -f`

## Health Checks
- MCP API: `GET /status`, `GET /graph/insights`
- Neo4j: `cypher-shell -u neo4j -p <pwd> 'CALL apoc.version()'`

## Backups (starter recommendations)
- Postgres: nightly `pg_dump -Fc mcp` → rotate 7–14 days; consider WAL‑G for PITR.
- Neo4j: nightly `neo4j-admin database dump neo4j --to-path=/var/backups/neo4j`

## Scheduling
- Fast Graphiti ingest: `systemctl status fast-graphiti-ingest.timer`
- Repo KG ingest: `systemctl status repo-kg.timer`
- Run now: `systemctl start fast-graphiti-ingest` or `systemctl start repo-kg`

## Troubleshooting
- Auth failures: confirm `REQUIRE_AUTH=true` and JWT secret matches GoTrue.
- DB errors: verify `DATABASE_URL` and that `vector`/`pg_trgm` extensions are installed.
- Graph errors: verify Neo4j password, APOC enabled, ports bound to localhost.
- Crawl: ensure Crawl4AI MCP is running; MCP API `/crawl` proxies to `MCP_CRAWL4AI_URL`.

