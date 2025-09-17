# Agents Overview

This repo uses small, purpose-built agents to assist the MCP platform. Agents are optional and run locally without external calls unless configured.

- Validator Agent (`src/agents/validator.py`)
  - Purpose: Assess graph health and data integrity across Postgres and the configured graph backend.
  - Inputs: optional `prefer` backend (neo4j|terminusdb|nebula)
  - Outputs: JSON with postgres_counts, graph_counts, issues[], score, and a short summary.
  - API: `POST /admin/validate` (admin-only, rate-limited)

- Future Agents (planned)
  - Migration Planner: simulate and propose mappings between relational records and chosen graph schema.
  - Data Hygiene: identify duplicates, stale embeddings, dangling refs; propose fixes.
  - Report Generator: produce PDF/HTML reports (Politicians use case) with configurable templates.

## Conventions
- Keep agents deterministic first; add LLM enrichments only as icing.
- Agents should never mutate state directly; use explicit admin endpoints.
- Agents must return structured JSON with a stable shape.

