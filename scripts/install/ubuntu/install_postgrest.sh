#!/usr/bin/env bash
set -euo pipefail

# Install PostgREST (Supabase-like REST over Postgres) as a systemd service

sudo apt-get update
sudo apt-get install -y postgrest

sudo mkdir -p /etc/postgrest

sudo tee /etc/postgrest/mcp.conf >/dev/null <<'CONF'
db-uri = "postgres://mcp_app:change-me@127.0.0.1:5432/mcp"
db-schemas = "public"
db-anon-role = "mcp_app"
server-host = "127.0.0.1"
server-port = 3000
jwt-secret = "replace-with-long-secret"
CONF

sudo tee /etc/systemd/system/postgrest.service >/dev/null <<'UNIT'
[Unit]
Description=PostgREST Service (MCP)
After=network.target postgresql.service

[Service]
ExecStart=/usr/bin/postgrest /etc/postgrest/mcp.conf
Restart=always
RestartSec=5
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now postgrest

echo "PostgREST installed on 127.0.0.1:3000"

