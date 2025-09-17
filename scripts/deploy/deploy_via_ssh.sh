#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-192.168.4.117}"
USER="${2:-cbwinslow}"
REPO_DIR="${3:-/opt/mcp-server}"

echo "==> Rsyncing repo to ${USER}@${HOST}:${REPO_DIR}"
rsync -az --delete --exclude '.git' ./ "${USER}@${HOST}:${REPO_DIR}/"

echo "==> Building and starting compose stack"
ssh -t "${USER}@${HOST}" "cd ${REPO_DIR}/infra/compose && docker compose -f docker-compose.prod.yml up -d --build && docker compose ps"

echo "==> Done. Web: http://${HOST}:3000  API: http://${HOST}:8000"
