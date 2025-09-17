# Infra Overview

- Docker: `infra/compose/docker-compose.prod.yml` (api, web, optional cloudflared)
- Env: `infra/prod/.env` (rendered by Ansible template)
- Terraform (Cloudflare): `infra/terraform/cloudflare`
- Pulumi (Cloudflare): `infra/pulumi/cloudflare`

Workflows
- Local build: `docker compose -f infra/compose/docker-compose.prod.yml up -d --build`
- Ansible deploy: `make ansible-install deploy` (renders `.env`, builds/starts stack)
- Checks: `make check`
- Migrations: `make migrate`
- Terraform: `make tf-init tf-apply`
- Pulumi: `make pulumi-preview pulumi-up`

DNS/Tunnel
- Terraform/Pulumi create DNS and an optional named Argo Tunnel; CNAMEs point to the tunnel endpoint.
- Compose `cloudflared` supports two modes automatically:
  - Token mode: set `CLOUDFLARE_TUNNEL_TOKEN` (stored in CF KV as `prod:CLOUDFLARE_TUNNEL_TOKEN`).
  - Credentials-file mode: Ansible writes `/infra/prod/cloudflared/{tunnel_id}.json` and `config.yml` and the service runs without a token.
