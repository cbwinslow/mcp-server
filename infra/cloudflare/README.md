# Cloudflare Tunnel

- Set `CLOUDFLARE_TUNNEL_TOKEN` in `infra/prod/.env`.
- Compose service `cloudflared` will start the tunnel and route your public hostname to `web` and `api`.
- To customize ingress rules, create `infra/cloudflare/config.yml` and mount it into the container.

