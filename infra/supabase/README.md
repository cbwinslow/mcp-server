# Supabase Self-Hosted Integration

This project expects the official Supabase self-hosted stack to provide Postgres (with pgBouncer), Auth, PostgREST, Storage, and Studio.

Two options:

1) Minimal DB-only: use `supabase/postgres` image (quick start, not full feature set).
2) Full Supabase: clone the official repo and run their compose with our network overrides.

## Full Supabase (recommended)

- Clone the official repository beside this project (or into `infra/supabase/upstream`).
- Copy `.env.example` from Supabase and set secrets.
- Apply our overrides to attach to `net_back` and `net_db`, and to avoid exposing Supabase's Kong.

```
# Example layout
infra/supabase/upstream/docker/docker-compose.yml
infra/supabase/overrides.yml
```

Run:

```
docker compose -f infra/compose/compose.core.yml \
               -f infra/supabase/upstream/docker/docker-compose.yml \
               -f infra/supabase/overrides.yml \
               --env-file infra/.env \
               up -d
```

## Minimal DB-only (fast track)

If you just need Postgres + pgvector quickly, create a simple compose file with `supabase/postgres` and connect it to `net_db`. Then update `DATABASE_URL` accordingly.

> Note: The full Supabase stack ships with its own Kong. We recommend keeping Supabase's Kong internal-only and using the external Kong defined in `compose.core.yml` for north-south traffic.

