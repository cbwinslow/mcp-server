# Scheduling

This project ships systemd oneshot services + timers for recurring jobs.

## Fast Graphiti Ingest (crawl → episodes → verify)
- Installer: `scripts/install/ubuntu/install_fast_graphiti_ingest_timer.sh`
- Service: `fast-graphiti-ingest.service`
- Timer: `fast-graphiti-ingest.timer` (OnCalendar=daily by default)
- Config: `/etc/fast-graphiti.env`

Edit env:
- `TARGET_URLS` or `TARGET_URL`
- `GROUP_ID`
- Crawl tunables: `CRAWL_DEPTH`, `CRAWL_MAX_PAGES`, `BATCH_BY_DOMAIN`, `MAX_ITEMS`, `BODY_CHARS`
- MCP/Graphiti/Neo4j envs as needed

## Repo → KG Batch
- Installer: `scripts/install/ubuntu/install_repo_kg_timer.sh`
- Service: `repo-kg.service`
- Timer: `repo-kg.timer` (OnCalendar=daily)
- Config: `/etc/repo-kg.env`

Edit env:
- `REPO_URLS` (comma‑separated)
- `NEO4J_URI/USER/PASSWORD`

## Timer Ops
- Enable + start: `systemctl enable --now <timer>`
- Run now: `systemctl start <service>`
- Inspect: `systemctl list-timers | grep <name>`

