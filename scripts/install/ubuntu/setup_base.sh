#!/usr/bin/env bash
set -euo pipefail

# Base system setup for Ubuntu 22.04+/24.04 on 192.168.4.117

sudo apt-get update
sudo apt-get install -y curl wget jq git ca-certificates gnupg lsb-release unzip build-essential ufw

# Firewall: allow SSH/HTTP/HTTPS; default deny incoming
sudo ufw default deny incoming || true
sudo ufw default allow outgoing || true
sudo ufw allow 22/tcp || true
sudo ufw allow 80/tcp || true
sudo ufw allow 443/tcp || true
echo "y" | sudo ufw enable || true

echo "Base system setup completed."

