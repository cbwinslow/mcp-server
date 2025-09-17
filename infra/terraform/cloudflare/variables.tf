variable "api_token" {
  type        = string
  description = "Cloudflare API token with permissions for Zone DNS and Tunnels"
}

variable "account_id" {
  type        = string
  description = "Cloudflare account ID"
}

variable "zone_id" {
  type        = string
  description = "Zone ID for the root domain"
}

variable "root_domain" {
  type        = string
  description = "Root domain"
  default     = "cloudcurio.cc"
}

variable "web_subdomain" {
  type        = string
  default     = "mcp"
  description = "Subdomain for the web console"
}

variable "api_subdomain" {
  type        = string
  default     = "api"
  description = "Subdomain for the API"
}

variable "tunnel_name" {
  type        = string
  default     = "mcp-tunnel"
}

variable "ingress" {
  type = list(object({
    hostname = string
    service  = string
  }))
  default = []
  description = "Optional custom ingress rules; if empty, defaults to web/api"
}
