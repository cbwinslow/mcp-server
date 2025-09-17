#!/usr/bin/env python3
"""
Minimal Graphiti MCP client wrapper (placeholder).

Note: Implementing a full MCP SSE client involves JSON-RPC over SSE/stdio negotiation.
This module provides a pragmatic fallback: if GRAPHITI_HTTP_URL is set, it proxies to the HTTP shim; otherwise, it raises.

Future work: replace with a true MCP SSE client for add_episode and search.
"""

import os
import json
import requests
from crewai_tools import BaseTool


class GraphitiMCPClientTool(BaseTool):
    name: str = "Graphiti MCP (proxy)"
    description: "Add episode or search via Graphiti; uses HTTP shim when available."

    def _run(self, action: str, payload: str) -> str:
        base = os.getenv("GRAPHITI_HTTP_URL")
        if not base:
            return json.dumps({
                "status": "failed",
                "error": "GRAPHITI_HTTP_URL not set; real MCP SSE client not yet implemented",
            })
        ep = "/episodes" if action == "episodes" else "/search"
        data = json.loads(payload) if payload else {}
        r = requests.post(base.rstrip("/") + ep, json=data, timeout=60)
        r.raise_for_status()
        return json.dumps({"status": "success", "result": r.json()}, indent=2)

