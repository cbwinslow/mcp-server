#!/usr/bin/env bash
set -euo pipefail

# Install a systemd oneshot service + timer for fast_graphiti_ingest.py

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}

if [ ! -d "$PY_ENV" ]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

# Default env
sudo tee /etc/fast-graphiti.env >/dev/null <<'ENV'
# Required
# Use TARGET_URLS (comma-separated) or TARGET_URL (single)
# TARGET_URLS=https://fastapi.tiangolo.com/,https://docs.python.org/3/
TARGET_URL=https://fastapi.tiangolo.com/
GROUP_ID=default

# MCP API
MCP_API_BASE=http://127.0.0.1:8000
# MCP_JWT=

# Graphiti MCP + Neo4j
GRAPHITI_MCP_SSE_URL=http://127.0.0.1:8000/sse
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme

# Crawl tuning
CRAWL_DEPTH=1
CRAWL_MAX_PAGES=3
BATCH_BY_DOMAIN=true
MAX_ITEMS=20
BODY_CHARS=3000
ENV

sudo tee /usr/local/bin/fast-graphiti-ingest.sh >/dev/null <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
source /etc/fast-graphiti.env
source /opt/mcp-venv/bin/activate
python /opt/mcp-server/scripts/agents/fast_graphiti_ingest.py
RUN
sudo chmod +x /usr/local/bin/fast-graphiti-ingest.sh

sudo tee /etc/systemd/system/fast-graphiti-ingest.service >/dev/null <<'UNIT'
[Unit]
Description=Fast Graphiti Ingest (crawl -> episodes -> verify)
After=network.target

[Service]
Type=oneshot
EnvironmentFile=/etc/fast-graphiti.env
ExecStart=/usr/local/bin/fast-graphiti-ingest.sh
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/fast-graphiti-ingest.timer >/dev/null <<'TIMER'
[Unit]
Description=Schedule Fast Graphiti Ingest

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER

sudo systemctl daemon-reload
sudo systemctl enable --now fast-graphiti-ingest.timer

echo "fast-graphiti-ingest.timer enabled. Edit /etc/fast-graphiti.env to set TARGET_URL and GROUP_ID."
