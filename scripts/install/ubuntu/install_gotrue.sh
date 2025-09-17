#!/usr/bin/env bash
set -euo pipefail

# Install Supabase GoTrue (Auth) as a native systemd service

INSTALL_DIR=/opt/gotrue
BIN=/usr/local/bin/gotrue
VERSION=${VERSION:-latest}

sudo mkdir -p $INSTALL_DIR

if [ "$VERSION" = "latest" ]; then
  URL=$(curl -s https://api.github.com/repos/supabase/gotrue/releases/latest | jq -r '.assets[] | select(.name | test("linux_amd64")) | .browser_download_url' | head -n1)
else
  URL=$(curl -s https://api.github.com/repos/supabase/gotrue/releases | jq -r --arg v "$VERSION" '.[] | select(.tag_name==$v) | .assets[] | select(.name | test("linux_amd64")) | .browser_download_url' | head -n1)
fi

tmp=$(mktemp -d)
cd "$tmp"
curl -L "$URL" -o gotrue.tar.gz
tar -xzf gotrue.tar.gz
sudo mv gotrue $BIN
sudo chmod +x $BIN

# Default env file
sudo tee $INSTALL_DIR/gotrue.env >/dev/null <<'ENV'
GOTRUE_SITE_URL=http://localhost
GOTRUE_API_HOST=127.0.0.1
GOTRUE_API_PORT=9999
GOTRUE_DB_DRIVER=postgres
GOTRUE_DB_DATABASE_URL=postgres://mcp_app:change-me@127.0.0.1:5432/mcp?sslmode=disable
GOTRUE_JWT_SECRET=replace-with-long-secret
GOTRUE_JWT_EXP=3600
GOTRUE_DISABLE_SIGNUP=false
ENV

sudo tee /etc/systemd/system/gotrue.service >/dev/null <<'UNIT'
[Unit]
Description=Supabase GoTrue Auth Service
After=network.target postgresql.service

[Service]
EnvironmentFile=/opt/gotrue/gotrue.env
ExecStart=/usr/local/bin/gotrue
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now gotrue

echo "GoTrue installed on 127.0.0.1:9999"

