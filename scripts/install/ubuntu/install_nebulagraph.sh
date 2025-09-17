#!/usr/bin/env bash
set -euo pipefail

# Install NebulaGraph (community) on Ubuntu via official apt repo

if ! command -v wget >/dev/null 2>&1; then
  sudo apt-get update && sudo apt-get install -y wget gnupg lsb-release
fi

wget -qO - https://repo.nebula-graph.io/nebula-graph.key | sudo apt-key add -
echo "deb https://repo.nebula-graph.io/apt/ $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/nebula-graph.list
sudo apt-get update
sudo apt-get install -y nebula-graphd nebula-metad nebula-storaged nebula-console

sudo systemctl enable --now nebula-graphd.service nebula-metad.service nebula-storaged.service || true

echo "NebulaGraph installed. Default console: nebula-console -addr 127.0.0.1 -port 9669"

