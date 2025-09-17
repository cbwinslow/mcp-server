#!/usr/bin/env python3
"""
Graphiti MCP JSON-RPC tool for CrewAI.
This tool posts JSON-RPC payloads to Graphiti MCP over HTTP.

Env:
- GRAPHITI_MCP_POST_URL: full POST endpoint; if unset, derive from GRAPHITI_MCP_SSE_URL by replacing /sse with /messages
- GRAPHITI_MCP_AUTH: Authorization header value if needed
"""

import os
import json
import requests
from crewai_tools import BaseTool


def _derive_post_url() -> str:
    post = os.getenv("GRAPHITI_MCP_POST_URL")
    if post:
        return post
    sse = os.getenv("GRAPHITI_MCP_SSE_URL", "http://127.0.0.1:8000/sse").rstrip("/")
    if sse.endswith("/sse"):
        return sse[:-4] + "/messages"
    return sse + "/messages"


class GraphitiMcpJsonRpcTool(BaseTool):
    name: str = "Graphiti MCP JSON-RPC"
    description: (
        "Send JSON-RPC requests to Graphiti MCP. Inputs: 'method' (str), 'params' (JSON str)."
    )

    def _run(self, method: str, params: str = "{}", id: int = 1) -> str:
        url = _derive_post_url()
        headers = {"Content-Type": "application/json"}
        auth = os.getenv("GRAPHITI_MCP_AUTH")
        if auth:
            headers["Authorization"] = auth
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": id,
                "method": method,
                "params": json.loads(params) if params else {},
            }
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Invalid params JSON: {e}"})

        try:
            r = requests.post(url, json=payload, headers=headers, timeout=60)
            r.raise_for_status()
            return json.dumps({"status": "success", "result": r.json()}, indent=2)
        except requests.RequestException as e:
            return json.dumps({"status": "failed", "error": str(e)})

