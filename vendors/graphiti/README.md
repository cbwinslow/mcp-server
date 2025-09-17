# Graphiti (getzep/graphiti)

This project integrates Graphiti to provide temporal, agent-first knowledge graph capabilities.

We do not vendor the full repository here. Use the installer script to clone and run the Graphiti MCP server as a host-native service.

- Upstream: https://github.com/getzep/graphiti
- Local installer: `scripts/install/ubuntu/install_graphiti_mcp.sh`
- Default service port: 8000 (SSE endpoint at `/sse`)

After install, point MCP clients (or your agents) to `http://127.0.0.1:8000/sse`.

