#!/usr/bin/env bash
set -euo pipefail

# Install coleam00/mcp-crawl4ai-rag as a host-native systemd service.

REPO_URL=${REPO_URL:-https://github.com/coleam00/mcp-crawl4ai-rag.git}
APP_DIR=${APP_DIR:-/opt/mcp-crawl4ai-rag}
PY_ENV=${PY_ENV:-/opt/mcp-crawl4ai-venv}
PYTHON=${PYTHON:-python3}

echo "Cloning $REPO_URL to $APP_DIR"
sudo rm -rf "$APP_DIR"
sudo git clone "$REPO_URL" "$APP_DIR"

echo "Creating venv at $PY_ENV"
sudo $PYTHON -m venv "$PY_ENV"
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

# Run setup helper (creates any local assets / dependencies as per README)
if command -v crawl4ai-setup >/dev/null 2>&1; then
  crawl4ai-setup || true
else
  echo "crawl4ai-setup entrypoint not found, continuing"
fi

# Environment file for the service
sudo mkdir -p $APP_DIR
sudo tee $APP_DIR/.env >/dev/null <<'ENV'
# Core MCP Server
HOST=0.0.0.0
PORT=8051
TRANSPORT=sse

# OpenAI or LocalAI
OPENAI_API_KEY=
MODEL_CHOICE=gpt-4.1-nano

# If using LocalAI instead of OpenAI
OPENAI_BASE_URL=http://127.0.0.1:8080/v1

# RAG strategies
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=false
USE_RERANKING=false
USE_KNOWLEDGE_GRAPH=false

# Supabase (for vector storage in this server)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Neo4j (for optional KG tools)
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
ENV

sudo tee /etc/systemd/system/mcp-crawl4ai-rag.service >/dev/null <<UNIT
[Unit]
Description=MCP Crawl4AI RAG Server
After=network.target

[Service]
EnvironmentFile=$APP_DIR/.env
WorkingDirectory=$APP_DIR
ExecStart=$PY_ENV/bin/python $APP_DIR/src/crawl4ai_mcp.py
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now mcp-crawl4ai-rag

echo "MCP Crawl4AI RAG running on :8051 (/sse). Edit $APP_DIR/.env to configure."

