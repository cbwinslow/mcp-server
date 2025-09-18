# Validation

The validation suite compares Postgres records vs. the configured graph backend and checks basic data hygiene.

What it checks
- Count mismatches: Repo/File/Chunk/Embedding counts across Postgres vs. graph.
- Null refs: `files.repository_id IS NULL`, `chunks.file_id IS NULL`.
- Dangling refs: Files without an existing repo; Chunks without an existing file.
- Duplicates: repositories by `url` (top 50 shown).
- Missing fields: Embeddings without `embedding_vector` or `model_name`.

Outputs
- JSON with:
  - `postgres_counts`, `graph_counts`
  - `issues[]` with `type`, `entity`, `field`, and counts or details
  - `score` (0–100)
  - `summary` (terse)

Running it
- API: `POST /admin/validate` (admin-only)
- Nightly: systemd timer (Ansible) runs it and logs to `/var/log/mcp/validation-YYYY-MM-DD.json`.
- UI: Admin → Validation Results & Validation Reports.

CI
- `validation-dry` job runs in CI and uploads `validation-report.json` as an artifact.
- Set GitHub Actions variable `VALIDATION_MIN_SCORE` (default 70) to show a warning if the score is below threshold.

Extending
- Add more checks in `src/agents/validator.py` as the schema evolves.
- Optionally baseline a target score in `validation-baseline.json` and compare in CI (future).

