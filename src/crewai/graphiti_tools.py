#!/usr/bin/env python3
"""
Graphiti MCP integration tool (lightweight).

Prefer using the Graphiti MCP server via SSE with a real MCP client.
This tool provides an optional HTTP shim if GRAPHITI_HTTP_URL is set.
Expected endpoints (if you run a shim):
  POST {GRAPHITI_HTTP_URL}/episodes -> upsert episodes
  POST {GRAPHITI_HTTP_URL}/search   -> search facts/entities
"""

import os
import json
import requests
from typing import Any
from crewai_tools import BaseTool


class GraphitiEpisodesTool(BaseTool):
    name: str = "Graphiti Episodes"
    description: (
        "Upsert episodes or search via Graphiti. Requires GRAPHITI_HTTP_URL (shim)."
    )

    def _run(self, action: str, payload: str) -> str:
        base = os.getenv("GRAPHITI_HTTP_URL")
        if not base:
            return json.dumps({
                "status": "failed",
                "error": "GRAPHITI_HTTP_URL not set. Use Graphiti MCP SSE directly or install an HTTP shim.",
            })
        try:
            data = json.loads(payload) if payload else {}
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Invalid JSON: {e}"})
        endpoint = "/episodes" if action == "episodes" else "/search"
        try:
            r = requests.post(base.rstrip("/") + endpoint, json=data, timeout=60)
            r.raise_for_status()
            return json.dumps({"status": "success", "result": r.json()}, indent=2)
        except requests.RequestException as e:
            return json.dumps({"status": "failed", "error": str(e)})

