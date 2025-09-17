#!/usr/bin/env python3
"""
Typed Graphiti MCP tools that call JSON-RPC with fixed methods and validated params.

Env:
- GRAPHITI_MCP_POST_URL or GRAPHITI_MCP_SSE_URL (derives /messages)
- GRAPHITI_MCP_AUTH (optional Authorization header)
"""

import os
import json
import requests
from typing import Dict
from crewai_tools import BaseTool


def _derive_post_url() -> str:
    post = os.getenv("GRAPHITI_MCP_POST_URL")
    if post:
        return post
    sse = os.getenv("GRAPHITI_MCP_SSE_URL", "http://127.0.0.1:8000/sse").rstrip("/")
    if sse.endswith("/sse"):
        return sse[:-4] + "/messages"
    return sse + "/messages"


def _rpc(method: str, params: Dict, id: int = 1) -> Dict:
    url = _derive_post_url()
    headers = {"Content-Type": "application/json"}
    auth = os.getenv("GRAPHITI_MCP_AUTH")
    if auth:
        headers["Authorization"] = auth
    payload = {"jsonrpc": "2.0", "id": id, "method": method, "params": params}
    r = requests.post(url, json=payload, headers=headers, timeout=90)
    r.raise_for_status()
    return r.json()


class GraphitiAddMemoryTool(BaseTool):
    name: str = "Graphiti Add Memory"
    description: "Add an episode to Graphiti memory. Inputs: name (str), body (str), group_id (str, optional), source (text|json|message)."

    def _run(self, name: str, body: str, group_id: str = "default", source: str = "text") -> str:
        try:
            res = _rpc("add_memory", {
                "name": name,
                "episode_body": body,
                "group_id": group_id,
                "source": source,
            })
            return json.dumps({"status": "success", "result": res}, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)})


class GraphitiSearchNodesTool(BaseTool):
    name: str = "Graphiti Search Nodes"
    description: "Search Graphiti nodes. Inputs: query (str), group_ids (JSON list, optional), max_nodes (int), center_node_uuid (str, optional), entity (str, optional)."

    def _run(self, query: str, group_ids: str = "[]", max_nodes: int = 10, center_node_uuid: str = "", entity: str = "") -> str:
        try:
            gids = json.loads(group_ids) if group_ids else []
            params = {
                "query": query,
                "group_ids": gids or None,
                "max_nodes": max_nodes,
                "center_node_uuid": center_node_uuid or None,
                "entity": entity or "",
            }
            res = _rpc("search_memory_nodes", params)
            return json.dumps({"status": "success", "result": res}, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)})


class GraphitiSearchFactsTool(BaseTool):
    name: str = "Graphiti Search Facts"
    description: "Search Graphiti facts. Inputs: query (str), group_ids (JSON list, optional), max_facts (int), center_node_uuid (str, optional)."

    def _run(self, query: str, group_ids: str = "[]", max_facts: int = 10, center_node_uuid: str = "") -> str:
        try:
            gids = json.loads(group_ids) if group_ids else []
            params = {
                "query": query,
                "group_ids": gids or None,
                "max_facts": max_facts,
                "center_node_uuid": center_node_uuid or None,
            }
            res = _rpc("search_memory_facts", params)
            return json.dumps({"status": "success", "result": res}, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)})


class GraphitiGetEpisodesTool(BaseTool):
    name: str = "Graphiti Get Episodes"
    description: "Get recent episodes. Inputs: group_id (str), last_n (int)."

    def _run(self, group_id: str = "default", last_n: int = 10) -> str:
        try:
            res = _rpc("get_episodes", {"group_id": group_id, "last_n": last_n})
            return json.dumps({"status": "success", "result": res}, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)})


class GraphitiClearGraphTool(BaseTool):
    name: str = "Graphiti Clear Graph"
    description: "Clear the entire graph and rebuild indexes (DANGEROUS). No inputs."

    def _run(self) -> str:
        try:
            res = _rpc("clear_graph", {})
            return json.dumps({"status": "success", "result": res}, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)})


class CrawlToGraphitiEpisodesTool(BaseTool):
    name: str = "Crawl → Graphiti Episodes"
    description: (
        "Transform crawl JSON into Graphiti episodes and write via add_memory. "
        "Inputs: crawl_json (str), group_id (str, default 'default'), max_items (int, default 10), "
        "batch_by_domain (bool, default false), body_chars (int, default 2000)."
    )

    def _run(
        self,
        crawl_json: str,
        group_id: str = "default",
        max_items: int = 10,
        batch_by_domain: bool = False,
        body_chars: int = 2000,
    ) -> str:
        try:
            payload = json.loads(crawl_json)
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Invalid crawl_json: {e}"})

        # Flatten items
        items = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            if isinstance(payload.get("results"), list):
                items = payload["results"]
            elif isinstance(payload.get("items"), list):
                items = payload["items"]
            else:
                items = [payload]

        # Transform
        def title_of(it):
            return it.get("title") or it.get("url") or "Crawled Page"

        def text_of(it):
            return it.get("text") or it.get("content") or ""

        def domain_of(it):
            url = it.get("url", "")
            try:
                from urllib.parse import urlparse
                net = urlparse(url).netloc
                return net or "unknown"
            except Exception:
                return "unknown"

        written = 0
        errors = []
        if batch_by_domain:
            from collections import defaultdict
            buckets = defaultdict(list)
            for it in items[:max_items]:
                buckets[domain_of(it)].append(it)
            for dom, bucket in buckets.items():
                parts = []
                for it in bucket:
                    t = title_of(it)
                    txt = text_of(it)
                    if not txt:
                        continue
                    parts.append(f"# {t}\n\n{txt[:body_chars]}")
                if not parts:
                    continue
                body = f"Domain: {dom}\n\n" + "\n\n---\n\n".join(parts)
                try:
                    _rpc("add_memory", {"name": f"Crawl batch: {dom}", "episode_body": body, "group_id": group_id, "source": "text"})
                    written += 1
                except Exception as e:
                    errors.append(str(e))
        else:
            for it in items[:max_items]:
                name = title_of(it)
                txt = text_of(it)
                if not txt:
                    continue
                body = txt[:body_chars]
                try:
                    _rpc("add_memory", {"name": name, "episode_body": body, "group_id": group_id, "source": "text"})
                    written += 1
                except Exception as e:
                    errors.append(str(e))
        return json.dumps({"status": "success", "episodes_written": written, "errors": errors}, indent=2)
