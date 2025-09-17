#!/usr/bin/env bash
set -euo pipefail

# Install Graphiti HTTP shim (FastAPI) as a systemd service

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}
PORT=${PORT:-8052}

if [ ! -d "$PY_ENV" ]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

sudo tee /etc/systemd/system/graphiti-http.service >/dev/null <<UNIT
[Unit]
Description=Graphiti HTTP Shim
After=network.target

[Service]
Environment=NEO4J_URI=${NEO4J_URI:-bolt://127.0.0.1:7687}
Environment=NEO4J_USER=${NEO4J_USER:-neo4j}
Environment=NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}
Environment=GRAPHITI_HTTP_PORT=${PORT}
WorkingDirectory=$APP_DIR
ExecStart=$PY_ENV/bin/uvicorn src.graphiti_shim.main:app --host 0.0.0.0 --port ${PORT}
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now graphiti-http

echo "Graphiti HTTP shim running on :${PORT} (POST /episodes, POST /search)."

