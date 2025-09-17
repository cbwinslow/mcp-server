# Ansible

Playbooks:
- `site.yml`: Installs Docker/Compose, syncs repo to `{{ repo_dir }}`, renders `infra/prod/.env`, builds and starts the stack.
- `checks.yml`: Lightweight connectivity checks to external services (Postgres/Neo4j/Nebula/TerminusDB/LocalAI).

Inventory:
- `inventory.ini` contains the production host: `192.168.4.117 ansible_user=cbwinslow`.

Variables:
- Group vars at `group_vars/mcp.yml` control repo paths, env values, and feature flags.
- Cloudflare KV secrets: set `cloudflare_api_token` and `cloudflare_account_id`. Secrets are written/read under namespace `mcp-secrets` with keys prefixed by `prod:`.
- Managed keys: `GOTRUE_JWT_SECRET`, `NEO4J_PASSWORD`, `NEBULA_PASSWORD`, `TERMINUSDB_TOKEN`, plus optional `CLOUDFLARE_TUNNEL_TOKEN`, `DATABASE_URL`, `LOCALAI_BASE_URL`.

Run:
```
ansible-playbook -i inventory.ini site.yml       # deploy
ansible-playbook -i inventory.ini checks.yml     # verify ports
ansible-playbook -i inventory.ini tfvars.yml     # render Terraform tfvars only
```
Notes:
- Domain defaults to `cloudcurio.cc` with `mcp.cloudcurio.cc` (web) and `api.cloudcurio.cc` (api). Adjust in group vars if needed.
- On first deploy, missing secrets are generated and stored in Cloudflare KV; subsequent runs reuse them.
- KV also seeds API_BASE_URL and WEB_BASE_URL so services that directly read from KV have values without relying on .env.

## Staging vs Production

- Default compose file is `docker-compose.prod.yml`. To deploy the staging stack by default, set in `group_vars/mcp.yml`:

```
compose_file: docker-compose.staging.yml
env_dir: "{{ repo_dir }}/infra/staging"
env_file: "{{ env_dir }}/.env"
```

- Staging publishes on ports 8001 (API) and 3001 (Web).

## Nightly Validation

- Enabled by default (`enable_validation_timer: true`). A systemd timer runs validation and appends JSON reports to `/var/log/mcp/validation-YYYY-MM-DD.json`.
- Logrotate keeps 8 weekly rotations; adjust `templates/logrotate-mcp.j2` as needed.
