#!/usr/bin/env bash
set -euo pipefail

DIR="infra/terraform/cloudflare"
pushd "$DIR" >/dev/null
terraform init
terraform apply "$@"
popd >/dev/null

