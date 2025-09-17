#!/usr/bin/env bash
set -euo pipefail

# Cloudflare KV helper
# Env: CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_TITLE (default mcp-secrets), CF_KV_ENV_PREFIX (default prod)

API_TOKEN="${CF_API_TOKEN:-}"
ACCOUNT_ID="${CF_ACCOUNT_ID:-}"
TITLE="${CF_KV_NAMESPACE_TITLE:-mcp-secrets}"
PREFIX="${CF_KV_ENV_PREFIX:-prod}"

if [[ -z "$API_TOKEN" || -z "$ACCOUNT_ID" ]]; then
  echo "Set CF_API_TOKEN and CF_ACCOUNT_ID in env" >&2
  exit 1
fi

hdr=( -H "Authorization: Bearer ${API_TOKEN}" )

ns_id() {
  local id
  id=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces" "${hdr[@]}" | jq -r --arg t "$TITLE" '.result[] | select(.title==$t) | .id' | head -n1)
  if [[ -z "$id" || "$id" == "null" ]]; then
    id=$(curl -sS -X POST "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces" \
      -H 'Content-Type: application/json' "${hdr[@]}" \
      --data @<(jq -n --arg t "$TITLE" '{title:$t}') | jq -r '.result.id')
  fi
  echo "$id"
}

cmd="${1:-}"
case "$cmd" in
  list)
    NS=$(ns_id)
    curl -sS "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces/${NS}/keys?limit=1000&prefix=${PREFIX}:" "${hdr[@]}" | jq .
    ;;
  get)
    key="${2:-}"
    if [[ -z "$key" ]]; then echo "Usage: $0 get KEY" >&2; exit 1; fi
    NS=$(ns_id)
    curl -sS "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces/${NS}/values/${PREFIX}:${key}" "${hdr[@]}"
    ;;
  set)
    key="${2:-}"; val="${3:-}"
    if [[ -z "$key" ]]; then echo "Usage: $0 set KEY VALUE" >&2; exit 1; fi
    NS=$(ns_id)
    curl -sS -X PUT "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces/${NS}/values/${PREFIX}:${key}" \
      -H 'Content-Type: text/plain' "${hdr[@]}" --data-raw "$val" | jq .
    ;;
  *)
    echo "Usage: $0 {list|get KEY|set KEY VALUE}" >&2
    exit 1
    ;;
esac

