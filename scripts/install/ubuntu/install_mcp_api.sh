#!/usr/bin/env bash
set -euo pipefail

# Install MCP FastAPI server as a systemd service running uvicorn

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}
PYTHON=${PYTHON:-python3}

sudo mkdir -p $APP_DIR
sudo rsync -a --exclude '.git' --exclude 'venv' --exclude '.venv' ./ $APP_DIR/

sudo $PYTHON -m venv $PY_ENV
source $PY_ENV/bin/activate
pip install --upgrade pip
pip install -e $APP_DIR

sudo tee /etc/systemd/system/mcp-api.service >/dev/null <<UNIT
[Unit]
Description=MCP FastAPI Server
After=network.target

[Service]
Environment=DATABASE_URL=${DATABASE_URL}
Environment=NEO4J_URI=${NEO4J_URI:-bolt://127.0.0.1:7687}
Environment=NEO4J_USER=${NEO4J_USER:-neo4j}
Environment=NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}
Environment=JWT_SECRET=${JWT_SECRET:-}
Environment=REQUIRE_AUTH=${REQUIRE_AUTH:-false}
WorkingDirectory=$APP_DIR
ExecStart=$PY_ENV/bin/uvicorn src.mcp_ingest.main:app --host 0.0.0.0 --port 8000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now mcp-api

echo "MCP API service installed on :8000"

