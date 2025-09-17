#!/usr/bin/env bash
set -euo pipefail

# Install a simple repo → KG ingest worker as a systemd service

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}

if [ ! -d "$PY_ENV" ]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

# Default env file
sudo tee /etc/repo-ingest.env >/dev/null <<'ENV'
REPO_URL=https://github.com/pydantic/pydantic
GROUP_ID=default
REPO_NAME=pydantic
ENV

sudo tee /usr/local/bin/repo-ingest.sh >/dev/null <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
source /opt/mcp-venv/bin/activate
source /etc/repo-ingest.env
python /opt/mcp-server/scripts/ingest/repo_to_kg.py "$REPO_URL" --group "$GROUP_ID" --repo-name "$REPO_NAME"
RUN
sudo chmod +x /usr/local/bin/repo-ingest.sh

sudo tee /etc/systemd/system/repo-ingest.service >/dev/null <<'UNIT'
[Unit]
Description=Repository → KG Ingest Worker
After=network.target

[Service]
Environment=NEO4J_URI=${NEO4J_URI:-bolt://127.0.0.1:7687}
Environment=NEO4J_USER=${NEO4J_USER:-neo4j}
Environment=NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}
Environment=DATABASE_URL=${DATABASE_URL}
Type=oneshot
ExecStart=/usr/local/bin/repo-ingest.sh
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
echo "Edit /etc/repo-ingest.env then run: sudo systemctl start repo-ingest"

