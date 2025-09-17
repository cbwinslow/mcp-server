# Terraform: Cloudflare DNS + Tunnel

Inputs (set via TF vars or `*.tfvars`):
- `api_token`: Cloudflare API token (Zone:DNS:Edit, Account:Cloudflare Tunnel:Edit)
- `account_id`, `zone_id`, `root_domain`
- `web_subdomain` (default: `mcp`), `api_subdomain` (default: `api-mcp`)
- `tunnel_name` (default: `mcp-tunnel`)

What it creates:
- A named Argo Tunnel with an ingress config routing hostnames to `web:3000` and `api:8000` (container names inside Compose).
- CNAME records for both hostnames pointing to the Tunnel’s `.cfargotunnel.com` endpoint.

Usage:
```
cd infra/terraform/cloudflare
terraform init
terraform apply -var "api_token=..." -var "account_id=..." -var "zone_id=..." -var "root_domain=cloudcurio.cc"
```

Output:
- `tunnel_id` for use in `cloudflared` credentials (if using file-based mode).
