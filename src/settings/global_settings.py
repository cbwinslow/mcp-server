#!/usr/bin/env python3
"""
Global settings store for MCP platform.
Stores and retrieves configuration from a JSON file on disk, with optional env fallbacks.

Note: Changing certain settings may require a service restart to fully apply.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


DEFAULTS: Dict[str, Any] = {
    "mcp_api": {
        "require_auth": False,
        "allow_graph_writes": False,
        "database_url": os.getenv("DATABASE_URL", ""),
        "neo4j": {
            "uri": os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
            "user": os.getenv("NEO4J_USER", "neo4j"),
            "password": os.getenv("NEO4J_PASSWORD", ""),
        },
        "crawl4ai_url": os.getenv("MCP_CRAWL4AI_URL", "http://127.0.0.1:8051"),
    },
    "graphiti": {
        "sse_url": os.getenv("GRAPHITI_MCP_SSE_URL", "http://127.0.0.1:8000/sse"),
        "post_url": os.getenv("GRAPHITI_MCP_POST_URL", ""),
        "auth": os.getenv("GRAPHITI_MCP_AUTH", ""),
        "group_id": os.getenv("GROUP_ID", "default"),
    },
    "crawl_pipeline": {
        "targets": [],
        "depth": 1,
        "max_pages": 3,
        "batch_by_domain": True,
        "max_items": 20,
        "body_chars": 3000,
    },
    "graph_backends": {
        "neo4j": False,
        "terminusdb": True,
        "nebulagraph": False,
        "default": "terminusdb",
    },
    "terminusdb": {
        "server_url": os.getenv("TERMINUSDB_URL", "http://127.0.0.1:6363"),
        "db": os.getenv("TERMINUSDB_DB", "admin"),
        "user": os.getenv("TERMINUSDB_USER", "admin"),
        "password": os.getenv("TERMINUSDB_PASSWORD", ""),
        "token": os.getenv("TERMINUSDB_TOKEN", ""),
    },
    "nebulagraph": {
        "host": os.getenv("NEBULA_HOST", "127.0.0.1"),
        "port": int(os.getenv("NEBULA_PORT", "9669")),
        "user": os.getenv("NEBULA_USER", "root"),
        "password": os.getenv("NEBULA_PASSWORD", ""),
        "space": os.getenv("NEBULA_SPACE", ""),
    },
    "admin": {
        "allowed_units": [
            "mcp-api",
            "mcp-crawl4ai-rag",
            "graphiti-mcp",
            "fast-graphiti-ingest",
            "repo-kg",
        ]
    },
    "chat": {
        "model": os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        "top_k": 5,
    },
}


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path("config/global_settings.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return DEFAULTS.copy()
        try:
            return DEFAULTS | json.loads(self.path.read_text())  # shallow merge
        except Exception:
            return DEFAULTS.copy()

    def write(self, data: Dict[str, Any]) -> Dict[str, Any]:
        merged = DEFAULTS.copy()
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        self.path.write_text(json.dumps(merged, indent=2))
        return merged
