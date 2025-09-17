locals {
  web_host = "${var.web_subdomain}.${var.root_domain}"
  api_host = "${var.api_subdomain}.${var.root_domain}"
}

# Optional: Create a named tunnel and config (requires cloudflared with credentials file mode)
resource "cloudflare_tunnel" "mcp" {
  account_id = var.account_id
  name       = var.tunnel_name
}

resource "cloudflare_tunnel_config" "mcp_cfg" {
  account_id = var.account_id
  tunnel_id  = cloudflare_tunnel.mcp.id

  dynamic "ingress_rule" {
    for_each = length(var.ingress) > 0 ? var.ingress : [
      {
        hostname = local.web_host
        service  = "http://web:3000"
      },
      {
        hostname = local.api_host
        service  = "http://api:8000"
      }
    ]
    content {
      hostname = ingress_rule.value.hostname
      service  = ingress_rule.value.service
    }
  }

  origin_request {
    http2_origin = true
  }
}

resource "cloudflare_record" "web" {
  zone_id = var.zone_id
  name    = var.web_subdomain
  type    = "CNAME"
  value   = cloudflare_tunnel.mcp.cname
  proxied = true
}

resource "cloudflare_record" "api" {
  zone_id = var.zone_id
  name    = var.api_subdomain
  type    = "CNAME"
  value   = cloudflare_tunnel.mcp.cname
  proxied = true
}

output "tunnel_id" {
  value = cloudflare_tunnel.mcp.id
}

# KV namespace for secrets
resource "cloudflare_workers_kv_namespace" "mcp_secrets" {
  account_id = var.account_id
  title      = "mcp-secrets"
}

resource "random_password" "jwt" { length = 48 special = false }
resource "random_password" "neo4j" { length = 32 special = false }
resource "random_password" "nebula" { length = 32 special = false }
resource "random_password" "terminus" { length = 48 special = false }

locals {
  env_prefix = "prod"
}

resource "cloudflare_workers_kv" "secrets" {
  for_each = {
    ("${local.env_prefix}:GOTRUE_JWT_SECRET") = random_password.jwt.result
    ("${local.env_prefix}:NEO4J_PASSWORD")    = random_password.neo4j.result
    ("${local.env_prefix}:NEBULA_PASSWORD")   = random_password.nebula.result
    ("${local.env_prefix}:TERMINUSDB_TOKEN")  = random_password.terminus.result
  }
  account_id   = var.account_id
  namespace_id = cloudflare_workers_kv_namespace.mcp_secrets.id
  key          = each.key
  value        = each.value
}
