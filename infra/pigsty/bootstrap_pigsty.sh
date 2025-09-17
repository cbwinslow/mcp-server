#!/usr/bin/env bash
set -euo pipefail

# Install and bootstrap Pigsty on the local host, then provision a single-node Postgres.

if ! command -v pigsty >/dev/null 2>&1; then
  echo "Installing Pigsty CLI..."
  curl -fsSL https://get.pigsty.cc | bash -s -- -y
fi

echo "Bootstrapping Pigsty..."
pigsty init || true

echo "Provisioning PostgreSQL via Pigsty (single node)..."
pigsty apply -i inventory.ini pg || {
  echo "Pigsty apply failed. Ensure SSH access and sudo permissions on 192.168.4.117."; exit 1;
}

echo "Pigsty provisioning complete. Next: run ./apply_sql.sh"

