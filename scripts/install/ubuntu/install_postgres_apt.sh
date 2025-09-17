#!/usr/bin/env bash
set -euo pipefail

# Install PostgreSQL 16 + pgvector via apt (alternative to Pigsty)

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-client-16 postgresql-16-pgvector postgresql-16-pgadmin4 || true

sudo systemctl enable --now postgresql@16-main || sudo systemctl enable --now postgresql

sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
   CREATE ROLE mcp_app LOGIN PASSWORD 'change-me';
EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'role exists'; END $$;
CREATE DATABASE mcp OWNER mcp_app;
\c mcp
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL

echo "PostgreSQL 16 with pgvector installed."

