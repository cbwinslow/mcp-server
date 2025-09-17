#!/usr/bin/env bash
set -euo pipefail

# Install a systemd oneshot service + timer to ingest multiple repos into the KG

APP_DIR=${APP_DIR:-/opt/mcp-server}
PY_ENV=${PY_ENV:-/opt/mcp-venv}

if [ ! -d "$PY_ENV" ]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -e "$APP_DIR"

sudo tee /etc/repo-kg.env >/dev/null <<'ENV'
# Comma-separated list of repo URLs
REPO_URLS=https://github.com/pydantic/pydantic,https://github.com/tiangolo/fastapi

# Optional group id (not used by raw Neo4j ingest, reserved for Graphiti-based flows)
GROUP_ID=default

# Neo4j
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
ENV

sudo tee /usr/local/bin/repo-kg.sh >/dev/null <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
source /etc/repo-kg.env
source /opt/mcp-venv/bin/activate

IFS="," read -ra REPOS <<< "$REPO_URLS"
for url in "${REPOS[@]}"; do
  url_trim=$(echo "$url" | xargs)
  [ -z "$url_trim" ] && continue
  name=$(basename "$url_trim" .git)
  python /opt/mcp-server/scripts/ingest/repo_to_kg.py "$url_trim" --repo-name "$name" --group "$GROUP_ID" || true
done
RUN
sudo chmod +x /usr/local/bin/repo-kg.sh

sudo tee /etc/systemd/system/repo-kg.service >/dev/null <<'UNIT'
[Unit]
Description=Repo → KG batch ingest
After=network.target

[Service]
Type=oneshot
EnvironmentFile=/etc/repo-kg.env
ExecStart=/usr/local/bin/repo-kg.sh
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/repo-kg.timer >/dev/null <<'TIMER'
[Unit]
Description=Schedule Repo → KG batch ingest

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER

sudo systemctl daemon-reload
sudo systemctl enable --now repo-kg.timer

echo "repo-kg.timer enabled. Edit /etc/repo-kg.env to set REPO_URLS."

