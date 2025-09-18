# Master Task List (Rolling)

Status codes: [P0]=now, [P1]=next, [P2]=later; (Done) when complete.

## Platform & Security
- [P0] Admin route hardening with role claims (Done)
- [P0] Rate-limits on admin endpoints (Done)
- [P1] Sentry/OTel sampling env + docs
- [P1] Prometheus `/metrics` counters (Done)
- [P2] Audit log export (JSONL) and download from Admin

## Data & Graph
- [P0] Files/Chunks SQLAlchemy models + Alembic (Done)
- [P0] Migration v2: repos/files/chunks/embeddings, dry-run/stream (Done)
- [P1] Migration v2: better progress (per-entity totals, progress bar) (Done)
- [P1] TerminusDB schema init endpoint (Done)
- [P2] Embedding→Chunk linkage strategy (await DB column or mapping)

## Validation
- [P0] Validator v2: count mismatches, null refs, summary (Done)
- [P1] Admin viewer for validation results with filters and CSV/JSON export
- [P2] Cross-backend diff (e.g., Neo4j vs TerminusDB) where applicable

## Console (Next.js)
- [P0] Settings: KV load/save for URLs (Done)
- [P0] Settings: connectivity badges + last tested stamps (Done)
- [P1] Settings: per-backend inline badges + timestamps (Done)
- [P1] Graph: templates, color legend, label filter, search/focus, PNG/JSON (Done)
- [P1] Admin: migration v2 Run & Run Live, progress, Download Summary (Done)
- [P1] Admin: compact/detailed stream toggle (Done)
- [P1] Admin: audit log viewer with filters, auto-refresh, table/JSON view, downloads (Done)
- [P1] Dashboard: show overall health and last validation score (Done)

## Infra/IaC
- [P0] Ansible: CF KV secrets, env render, systemd, checks (Done)
- [P1] Terraform/Pulumi: CF DNS + Tunnel + KV namespace, example tfvars (Done)
- [P1] Staging stack (compose profile) (Done)
- [P2] Nightly validation job (Ansible timer) (Done)

## CI/CD
- [P0] Ruff + mypy + pytest (enforced) (Done)
- [P1] Playwright smoke (non-blocking) (Done)
- [P2] Lint/type/test as required gates; artifact uploads for summaries (validation report artifact added)

## Docs
- [P0] CODE.md (map) (Done)
- [P0] AGENTS.md (Done)
- [P1] DEPLOYMENT.md expanded with Sentry/OTel, metrics scrape

## Milestones
- M1 (Complete): Security hardening, Secrets, Infra scaffolding
- M2 (Complete): Settings/Graph/Admin UX core, migration v2 basics
- M3 (In progress): Streaming progress, validation v2, metrics
- M4 (Upcoming): Validation viewer, audit exports, staging rollout
