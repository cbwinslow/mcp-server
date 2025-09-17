#!/usr/bin/env bash
set -euo pipefail

DIR="infra/pulumi/cloudflare"
pushd "$DIR" >/dev/null
python -m venv .venv || true
source .venv/bin/activate
pip install -r requirements.txt
pulumi up "$@"
popd >/dev/null

