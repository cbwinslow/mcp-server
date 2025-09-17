#!/usr/bin/env bash
set -euo pipefail

# Apply bootstrap SQL to the target Postgres (Pigsty or Supabase DB)

PSQL_URL="${PSQL_URL:-postgres://postgres:postgres@127.0.0.1:5432/postgres}"

echo "Using PSQL_URL=$PSQL_URL"

psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f bootstrap/00_roles.sql
psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f bootstrap/10_db_mcp.sql
psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f bootstrap/20_extensions.sql
psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f bootstrap/30_db_langfuse.sql

echo "SQL bootstrap complete."

