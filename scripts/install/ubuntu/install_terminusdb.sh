#!/usr/bin/env bash
set -euo pipefail

# Experimental host-native TerminusDB setup.
# Note: Official guidance often uses Docker; host-native install may vary.

sudo apt-get update
sudo apt-get install -y git curl build-essential swi-prolog jq

# Clone TerminusDB server (if not present)
sudo mkdir -p /opt/terminusdb
if [ ! -d /opt/terminusdb/terminusdb ]; then
  sudo git clone https://github.com/terminusdb/terminusdb /opt/terminusdb/terminusdb
fi

cat <<'UNIT' | sudo tee /etc/systemd/system/terminusdb.service >/dev/null
[Unit]
Description=TerminusDB Server (experimental)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/terminusdb/terminusdb
ExecStart=/usr/bin/swipl -q -f ./bootstrap.pl
Restart=on-failure
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now terminusdb

echo "TerminusDB attempted install. If it fails, consider Docker-based deployment."

