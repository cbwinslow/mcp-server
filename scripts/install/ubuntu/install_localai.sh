#!/usr/bin/env bash
set -euo pipefail

# Install LocalAI (OpenAI-compatible local inference) as a systemd service

VERSION=${VERSION:-"latest"}
INSTALL_DIR=/opt/localai
BIN_DIR=/usr/local/bin
USER=${SUDO_USER:-$(whoami)}

sudo mkdir -p $INSTALL_DIR/models $INSTALL_DIR/logs
sudo chown -R $USER:$USER $INSTALL_DIR

if [ "$VERSION" = "latest" ]; then
  URL=$(curl -s https://api.github.com/repos/go-skynet/LocalAI/releases/latest | jq -r '.assets[] | select(.name | test("linux-amd64")) | .browser_download_url' | head -n1)
else
  URL=$(curl -s https://api.github.com/repos/go-skynet/LocalAI/releases | jq -r --arg v "$VERSION" '.[] | select(.tag_name==$v) | .assets[] | select(.name | test("linux-amd64")) | .browser_download_url' | head -n1)
fi

tmp=$(mktemp -d)
cd "$tmp"
curl -L "$URL" -o localai.tgz
tar -xzf localai.tgz
sudo mv local-ai $BIN_DIR/local-ai
sudo chmod +x $BIN_DIR/local-ai

sudo tee /etc/systemd/system/localai.service >/dev/null <<'UNIT'
[Unit]
Description=LocalAI Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
Environment=MODELS_PATH=/opt/localai/models
ExecStart=/usr/local/bin/local-ai --address 0.0.0.0 --port 8080 --models-path /opt/localai/models
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now localai

echo "LocalAI installed. API at http://127.0.0.1:8080/v1"

