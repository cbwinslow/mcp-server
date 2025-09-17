# Deployment (Ubuntu 22.04+)

## Quick SSH Deploy

```
scripts/deploy/deploy_via_ssh.sh 192.168.4.117 cbwinslow /opt/mcp-server
```

- Edit `infra/prod/.env` on the server (copy from `.env.example`).
- Optional: set `CLOUDFLARE_TUNNEL_TOKEN` to expose public URLs.

## Ansible

```
ansible-playbook -i ansible/inventory.ini ansible/site.yml
```

## Docker Compose (server)

```
cd /opt/mcp-server/infra/compose
cp ../prod/.env.example ../prod/.env  # then edit
docker compose -f docker-compose.prod.yml up -d --build
```

Services:
- API: `:8000`
- Web: `:3000`
- Cloudflared: runs if token provided

## Notes
- Existing databases (Postgres, Neo4j, TerminusDB, Nebula) are treated as external; configure connection strings in `infra/prod/.env`.
- Run DB migrations as needed via API admin endpoints or Alembic.

## IaC

Terraform (Cloudflare):
```
cd infra/terraform/cloudflare
terraform init
terraform apply -var "api_token=..." -var "account_id=..." -var "zone_id=..." -var "root_domain=cloudcurio.cc"
```

Pulumi (Cloudflare):
```
cd infra/pulumi/cloudflare
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pulumi stack init dev
pulumi config set cloudflare:apiToken --secret <token>
pulumi config set accountId <account-id>
pulumi config set zoneId <zone-id>
pulumi config set rootDomain cloudcurio.cc
pulumi up

### Tunnel modes
- Token mode: store the Tunnel token in CF KV as `prod:CLOUDFLARE_TUNNEL_TOKEN` and redeploy; the `cloudflared` service will pick it up.
- Credentials-file mode: Ansible will create a named tunnel and write credentials/config under `infra/prod/cloudflared/`. Compose mounts this path and runs the tunnel without a token.

## Observability

- Structured logs (JSON) with `X-Request-ID` for correlation are enabled by default.
- Optional Sentry: set `SENTRY_DSN` in `infra/prod/.env` (Ansible template supports it).
- Optional OpenTelemetry: set `OTEL_EXPORTER_OTLP_ENDPOINT` (HTTP OTLP); service name is `mcp-api`.
- Prometheus metrics: scrape `http://<host>:8000/metrics` for counters:
  - `graph_tests_total{backend,ok}`
  - `migration_runs_total{dry_run,ok}`
  - `admin_actions_total{unit,action}`

Example Prometheus scrape config:

```
scrape_configs:
  - job_name: 'mcp-api'
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets: ['192.168.4.117:8000']
```

Sentry (optional): set `SENTRY_DSN` in `infra/prod/.env`. Sampling is set to 0.05 in code; adjust as desired.

OpenTelemetry (optional): set `OTEL_EXPORTER_OTLP_ENDPOINT` to your collector (HTTP). Service name is `mcp-api`.

## Staging Environment

To run a staging stack side-by-side:

```
# On the server
cd /opt/mcp-server/infra/compose
cp ../staging/.env.example ../staging/.env  # edit with staging URLs + CF KV prefix
docker compose -f docker-compose.staging.yml up -d --build
```

- Staging publishes on 8001 (API) and 3001 (Web).
- Adjust Ansible `compose_file` to `docker-compose.staging.yml` to make staging the default for deploys:
  - In `ansible/group_vars/mcp.yml`: `compose_file: docker-compose.staging.yml`


## Cloudflare KV CLI

Quickly list/get/set secrets in KV from your terminal (uses env `CF_API_TOKEN`, `CF_ACCOUNT_ID`):

```
export CF_API_TOKEN=...; export CF_ACCOUNT_ID=968ff4ee9f5e59bc6c72758269d6b9d6
scripts/tools/cf_kv.sh list
scripts/tools/cf_kv.sh get API_BASE_URL
scripts/tools/cf_kv.sh set API_BASE_URL https://api.cloudcurio.cc
```
```
