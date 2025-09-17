#!/usr/bin/env bash
set -euo pipefail

# Install Graphiti MCP Server (getzep/graphiti) as a host-native service.

REPO_URL=${REPO_URL:-https://github.com/getzep/graphiti.git}
APP_DIR=${APP_DIR:-/opt/graphiti}
PY_ENV=${PY_ENV:-/opt/graphiti-venv}

sudo rm -rf "$APP_DIR"
sudo git clone "$REPO_URL" "$APP_DIR"

# Install uv (Graphiti uses uv)
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

cd "$APP_DIR/mcp_server"
uv sync

# Env file
sudo tee $APP_DIR/mcp_server/.env >/dev/null <<'ENV'
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=demodemo
OPENAI_API_KEY=
MODEL_NAME=gpt-4.1-mini
SMALL_MODEL_NAME=gpt-4.1-nano
LLM_TEMPERATURE=0.2
SEMAPHORE_LIMIT=10
ENV

sudo tee /etc/systemd/system/graphiti-mcp.service >/dev/null <<'UNIT'
[Unit]
Description=Graphiti MCP Server
After=network.target

[Service]
WorkingDirectory=/opt/graphiti/mcp_server
EnvironmentFile=/opt/graphiti/mcp_server/.env
ExecStart=/root/.local/bin/uv run graphiti_mcp_server.py --transport sse
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now graphiti-mcp

echo "Graphiti MCP running. SSE at http://127.0.0.1:8000/sse"

