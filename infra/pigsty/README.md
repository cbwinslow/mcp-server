# Pigsty Integration for PostgreSQL / pgvector

Pigsty (https://pigsty.cc) can provision and configure PostgreSQL clusters on bare-metal/VMs.

This repo provides a minimal inventory and SQL bootstrap to:
- Install Postgres on 192.168.4.117 using Pigsty
- Enable required extensions (pgvector, pg_trgm)
- Create databases and roles used by this project (mcp, langfuse)

> Note: If you run the full Supabase stack, it ships its own Postgres inside Docker.
> Pigsty cannot manage inside that container. You can either:
> 1) Use Pigsty to provision a host Postgres (external) and point services to it; or
> 2) Keep Supabase's Postgres and use the `bootstrap/*.sql` files here with `psql` to create roles/extensions.

## Quick Start (host Postgres via Pigsty)

1) Install prerequisites on the control machine (this VM):
```
curl -fsSL https://get.pigsty.cc | bash -s -- -y
```

2) Adjust `inventory.ini` to point to your host (default 192.168.4.117).

3) Run Pigsty playbooks to provision Postgres single node:
```
cd infra/pigsty
./bootstrap_pigsty.sh
```

4) Apply bootstrap SQL (roles, dbs, extensions):
```
./apply_sql.sh
```

## Use with Supabase Postgres (container)

If you keep Supabase's Postgres, run:
```
export PSQL_URL="postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:5432/postgres"
psql "$PSQL_URL" -f bootstrap/00_roles.sql
psql "$PSQL_URL" -f bootstrap/10_db_mcp.sql
psql "$PSQL_URL" -f bootstrap/20_extensions.sql
psql "$PSQL_URL" -f bootstrap/30_db_langfuse.sql
```

