import pulumi
import pulumi_cloudflare as cf

config = pulumi.Config()

api_token = config.require_secret("apiToken")
account_id = config.require("accountId")
zone_id = config.require("zoneId")
root_domain = config.require("rootDomain")
web_sub = config.get("webSubdomain") or "mcp"
api_sub = config.get("apiSubdomain") or "api-mcp"
tunnel_name = config.get("tunnelName") or "mcp-tunnel"

provider = cf.Provider("cloudflare", api_token=api_token)

tunnel = cf.Tunnel("mcp", name=tunnel_name, account_id=account_id, opts=pulumi.ResourceOptions(provider=provider))

web_host = f"{web_sub}.{root_domain}"
api_host = f"{api_sub}.{root_domain}"

cfg = cf.TunnelConfig(
    "mcp-cfg",
    account_id=account_id,
    tunnel_id=tunnel.id,
    ingress_rules=[
        cf.TunnelConfigIngressRuleArgs(hostname=web_host, service="http://web:3000"),
        cf.TunnelConfigIngressRuleArgs(hostname=api_host, service="http://api:8000"),
        cf.TunnelConfigIngressRuleArgs(service="http_status:404"),
    ],
    origin_request=cf.TunnelConfigOriginRequestArgs(http2_origin=True),
    opts=pulumi.ResourceOptions(provider=provider),
)

dns_web = cf.Record(
    "web",
    zone_id=zone_id,
    name=web_sub,
    type="CNAME",
    value=tunnel.cname,
    proxied=True,
    opts=pulumi.ResourceOptions(provider=provider),
)

dns_api = cf.Record(
    "api",
    zone_id=zone_id,
    name=api_sub,
    type="CNAME",
    value=tunnel.cname,
    proxied=True,
    opts=pulumi.ResourceOptions(provider=provider),
)

pulumi.export("tunnelId", tunnel.id)
pulumi.export("webHostname", dns_web.hostname)
pulumi.export("apiHostname", dns_api.hostname)

