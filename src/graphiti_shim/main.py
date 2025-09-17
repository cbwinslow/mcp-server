#!/usr/bin/env python3
"""
Graphiti HTTP shim: simple FastAPI service to add episodes and run search using graphiti-core.
Intended for convenience; preferred integration remains Graphiti MCP (SSE) for rich tools.
"""

import os
import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graphiti_core.graphiti import Graphiti
from graphiti_core.search.search import search as graphiti_search
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
)
from graphiti_core.search.search_filters import SearchFilters

logger = logging.getLogger("graphiti_shim")
logging.basicConfig(level=logging.INFO)


class EpisodeIn(BaseModel):
    name: str
    body: str
    source_description: str = "api"
    reference_time: Optional[str] = None  # ISO string; default now
    group_id: Optional[str] = None
    update_communities: bool = False


class SearchIn(BaseModel):
    query: str
    group_ids: Optional[List[str]] = None
    limit: int = 10


app = FastAPI(title="Graphiti HTTP Shim", version="0.1.0")


def get_graphiti() -> Graphiti:
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD not set")
    return Graphiti(uri=uri, user=user, password=password)


@app.post("/episodes")
async def add_episode(ep: EpisodeIn):
    try:
        g = get_graphiti()
        ref = datetime.fromisoformat(ep.reference_time) if ep.reference_time else datetime.utcnow()
        res = await g.add_episode(
            name=ep.name,
            episode_body=ep.body,
            source_description=ep.source_description,
            reference_time=ref,
            group_id=ep.group_id,
            update_communities=ep.update_communities,
        )
        return {"status": "success", "episode": res.episode.model_dump()}
    except Exception as e:
        logger.exception("Episode error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def run_search(s: SearchIn):
    try:
        g = get_graphiti()
        cfg = COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        cfg.limit = s.limit
        res = await graphiti_search(
            g.clients,
            query=s.query,
            group_ids=s.group_ids or None,
            config=cfg,
            search_filter=SearchFilters(),
        )
        return {"status": "success", "results": res.model_dump()}
    except Exception as e:
        logger.exception("Search error")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GRAPHITI_HTTP_PORT", "8052")))

