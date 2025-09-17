#!/usr/bin/env python3
"""
Experimental Graphiti MCP SSE client.

Status: Receiver-only scaffold. It connects to an SSE endpoint (GRAPHITI_MCP_SSE_URL),
prints incoming events, and provides placeholders for sending JSON-RPC requests.

Notes:
- MCP over SSE requires a client→server channel (typically POSTing JSON-RPC messages)
  and a server→client channel (SSE stream). This module implements the SSE read loop
  and provides a send() stub you can wire to Graphiti's expected POST endpoint.
- For immediate functionality in CrewAI, prefer graphiti_mcp (HTTP shim) or run
  Graphiti MCP with an MCP-aware client (Claude/Cursor).
"""

import asyncio
import json
import os
from typing import AsyncIterator, Optional

import aiohttp


class GraphitiMcpSseClient:
    def __init__(self, sse_url: Optional[str] = None, auth: Optional[str] = None):
        self.sse_url = sse_url or os.getenv("GRAPHITI_MCP_SSE_URL", "http://127.0.0.1:8000/sse")
        self.auth = auth or os.getenv("GRAPHITI_MCP_AUTH")

    async def events(self) -> AsyncIterator[dict]:
        headers = {}
        if self.auth:
            headers["Authorization"] = self.auth
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(self.sse_url) as resp:
                resp.raise_for_status()
                async for line in resp.content:
                    try:
                        s = line.decode("utf-8").strip()
                        if not s or not s.startswith("data:"):
                            continue
                        data = s[5:].strip()
                        if data == "[DONE]":
                            break
                        yield json.loads(data)
                    except Exception:
                        continue

    async def send(self, payload: dict) -> dict:
        """Send a JSON-RPC message to Graphiti MCP.
        Uses GRAPHITI_MCP_POST_URL if set; otherwise derives from SSE URL by replacing '/sse' with '/messages'.
        """
        post_url = os.getenv("GRAPHITI_MCP_POST_URL")
        if not post_url:
            base = self.sse_url.rstrip('/')
            if base.endswith('/sse'):
                post_url = base[:-4] + '/messages'
            else:
                post_url = base + '/messages'

        headers = {"Content-Type": "application/json"}
        if self.auth:
            headers["Authorization"] = self.auth
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(post_url, json=payload) as resp:
                resp.raise_for_status()
                return await resp.json()


async def _demo():
    client = GraphitiMcpSseClient()
    async for ev in client.events():
        print(ev)


if __name__ == "__main__":
    asyncio.run(_demo())
