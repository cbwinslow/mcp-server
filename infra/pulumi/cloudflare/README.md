# Pulumi (Python): Cloudflare DNS + Tunnel

Configure stack settings (production example):

```
cd infra/pulumi/cloudflare
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pulumi stack init dev
pulumi config set cloudflare:apiToken --secret <token>
pulumi config set accountId <account-id>
pulumi config set zoneId <zone-id>
pulumi config set rootDomain cloudcurio.cc
pulumi config set webSubdomain mcp
pulumi config set apiSubdomain api-mcp
pulumi config set tunnelName mcp-tunnel
```

For staging, use a separate stack and subdomains:

```
pulumi stack init staging
pulumi config set cloudflare:apiToken --secret <token>
pulumi config set accountId <account-id>
pulumi config set zoneId <zone-id>
pulumi config set rootDomain cloudcurio.cc
pulumi config set webSubdomain mcp-staging
pulumi config set apiSubdomain api-staging
pulumi config set tunnelName mcp-staging-tunnel
```

Preview/apply:
```
pulumi preview
pulumi up
```

Exports: `tunnelId`, `webHostname`, `apiHostname`.
