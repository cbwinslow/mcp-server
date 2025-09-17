#!/usr/bin/env bash
set -euo pipefail

# Install a crawl → index worker and timer using MCP API proxy endpoints

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}

if [ ! -d "$PY_ENV" ]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

sudo tee /etc/crawl-ingest.env >/dev/null <<'ENV'
URLS=https://docs.python.org/3/ https://fastapi.tiangolo.com/
COLLECTION=mcp_chunks
MCP_API_BASE=http://127.0.0.1:8000
# MCP_JWT=
ENV

sudo tee /usr/local/bin/crawl-ingest.sh >/dev/null <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
source /opt/mcp-venv/bin/activate
source /etc/crawl-ingest.env
python /opt/mcp-server/scripts/ingest/crawl_and_index.py ${URLS} --collection "$COLLECTION" --mcp "$MCP_API_BASE" ${MCP_JWT:+--jwt $MCP_JWT}
RUN
sudo chmod +x /usr/local/bin/crawl-ingest.sh

sudo tee /etc/systemd/system/crawl-ingest.service >/dev/null <<'UNIT'
[Unit]
Description=Crawl → Index worker (via MCP API)
After=network.target

[Service]
Environment=NEO4J_URI=${NEO4J_URI:-bolt://127.0.0.1:7687}
Environment=NEO4J_USER=${NEO4J_USER:-neo4j}
Environment=NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}
Environment=DATABASE_URL=${DATABASE_URL}
Type=oneshot
ExecStart=/usr/local/bin/crawl-ingest.sh
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/crawl-ingest.timer >/dev/null <<'TIMER'
[Unit]
Description=Schedule crawl → index job

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER

sudo systemctl daemon-reload
sudo systemctl enable --now crawl-ingest.timer

echo "crawl-ingest.timer enabled. Edit /etc/crawl-ingest.env to change targets."

