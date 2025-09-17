#!/usr/bin/env python3
"""
CrewAI Knowledge Graph Tools
- Neo4jCypherTool: run Cypher against Neo4j
- LlamaIndexGraphSyncTool: upsert nodes/edges via LlamaIndex Neo4jGraphStore
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional

from crewai_tools import BaseTool

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jCypherTool(BaseTool):
    """Execute Cypher read/write queries against Neo4j."""

    name: str = "Neo4j Cypher"
    description: str = (
        "Run Cypher (read/write). Inputs: 'query' (str), 'params' (JSON str, optional),"
        " 'mode' (read|write, default: read)."
    )

    def _run(self, query: str, params: str = "{}", mode: str = "read") -> str:
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        pwd = os.getenv("NEO4J_PASSWORD")
        if not pwd:
            return json.dumps({"status": "failed", "error": "NEO4J_PASSWORD not set"})
        try:
            p = json.loads(params) if params else {}
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Invalid params JSON: {e}"})

        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        try:
            def work(tx):
                res = tx.run(query, **p)
                return [r.data() for r in res]
            if mode.lower() == "write":
                records = driver.execute_write(work)
            else:
                records = driver.execute_read(work)
            return json.dumps({"status": "success", "records": records}, indent=2)
        except Exception as e:
            logger.error(f"Cypher error: {e}")
            return json.dumps({"status": "failed", "error": str(e)})
        finally:
            driver.close()


class LlamaIndexGraphSyncTool(BaseTool):
    """Upsert simple nodes/edges into Neo4j via LlamaIndex Neo4jGraphStore.
    Inputs:
      - nodes: JSON list of {label: str, properties: dict}
      - edges: JSON list of {src: {label,id or key}, dst: {label,id or key}, type: str, properties: dict}
    """

    name: str = "KG Sync (LlamaIndex)"
    description: str = (
        "Upsert nodes/edges in Neo4j using LlamaIndex GraphStore."
    )

    def _run(self, nodes: str = "[]", edges: str = "[]") -> str:
        try:
            from llama_index.graph_stores.neo4j import Neo4jGraphStore
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Missing llama-index graph store: {e}"})

        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        pwd = os.getenv("NEO4J_PASSWORD")
        if not pwd:
            return json.dumps({"status": "failed", "error": "NEO4J_PASSWORD not set"})

        try:
            nodes_json = json.loads(nodes) if nodes else []
            edges_json = json.loads(edges) if edges else []
        except Exception as e:
            return json.dumps({"status": "failed", "error": f"Invalid JSON: {e}"})

        store = Neo4jGraphStore(url=uri, username=user, password=pwd)
        created = {"nodes": 0, "edges": 0}

        try:
            # Basic upserts using merge semantics
            for n in nodes_json:
                label = n.get("label", "Entity")
                props = n.get("properties", {})
                store.client.run(
                    f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                    id=props.get("id"), props=props,
                )
                created["nodes"] += 1
            for e in edges_json:
                etype = e.get("type", "RELATED")
                s = e.get("src", {})
                d = e.get("dst", {})
                s_label, s_id = s.get("label", "Entity"), s.get("id")
                d_label, d_id = d.get("label", "Entity"), d.get("id")
                props = e.get("properties", {})
                store.client.run(
                    f"MERGE (a:{s_label} {{id: $sid}}) MERGE (b:{d_label} {{id: $did}}) "
                    f"MERGE (a)-[r:{etype}]->(b) SET r += $props",
                    sid=s_id, did=d_id, props=props,
                )
                created["edges"] += 1
            return json.dumps({"status": "success", **created}, indent=2)
        except Exception as e:
            logger.error(f"Graph sync error: {e}")
            return json.dumps({"status": "failed", "error": str(e)})

