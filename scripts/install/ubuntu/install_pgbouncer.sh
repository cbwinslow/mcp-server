#!/usr/bin/env bash
set -euo pipefail

# Install and configure PgBouncer for local PostgreSQL pooling

sudo apt-get update
sudo apt-get install -y pgbouncer

sudo tee /etc/pgbouncer/pgbouncer.ini >/dev/null <<'CFG'
[databases]
mcp = host=127.0.0.1 port=5432 dbname=mcp auth_user=mcp_app

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
reserve_pool_size = 20
server_reset_query = DISCARD ALL
ignore_startup_parameters = extra_float_digits
CFG

sudo tee /etc/pgbouncer/userlist.txt >/dev/null <<'USERS'
"mcp_app" "md5$(echo -n change-me | md5sum | awk '{print $1}')"
USERS

sudo systemctl enable --now pgbouncer

echo "PgBouncer listening on 127.0.0.1:6432"

