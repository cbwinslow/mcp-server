#!/usr/bin/env python3
"""
LlamaIndex-powered indexing and hybrid retrieval pipeline.
Stores embeddings in Postgres (pgvector) and entities/relations in Neo4j.
"""

import os
from typing import List, Optional

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.graph_stores.neo4j import Neo4jGraphStore


def get_pg_params():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for PGVector store")
    return url


def get_neo4j_params():
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD")
    if not pwd:
        raise RuntimeError("NEO4J_PASSWORD is required")
    return uri, user, pwd


def index_texts(texts: List[str], collection: str = "mcp_chunks") -> int:
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=128)
    nodes = []
    for t in texts:
        chunks = splitter.split_text(t)
        for i, ch in enumerate(chunks):
            nodes.append(Document(text=ch))

    # PGVector store
    pg_conn_str = get_pg_params()
    vector_store = PGVectorStore.from_params(
        database_url=pg_conn_str, schema_name="public", table_name=collection
    )

    VectorStoreIndex.from_documents(nodes, vector_store=vector_store)
    return len(nodes)


def init_graph():
    uri, user, pwd = get_neo4j_params()
    graph_store = Neo4jGraphStore(url=uri, username=user, password=pwd)
    return graph_store

