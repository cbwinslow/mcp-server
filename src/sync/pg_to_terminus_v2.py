#!/usr/bin/env python3
"""
PG -> TerminusDB migration v2 (idempotent, multi-entity, dry-run support).
Implements repositories, files, chunks, and embeddings mappings (safe defaults).
"""
from __future__ import annotations
import os, json, sys, asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text as sql_text
from terminusdb_client import WOQLClient


async def fetch_all(engine, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    async with engine.connect() as conn:
        res = await conn.execute(sql_text(query), params or {})
        rows = res.mappings().all()
        return [dict(r) for r in rows]

async def count_table(engine, table: str) -> int:
    rows = await fetch_all(engine, f"SELECT count(1) as c FROM {table}")
    try:
        return int(rows[0].get('c') or 0)
    except Exception:
        return 0


def td_client() -> WOQLClient:
    url = os.getenv('TERMINUSDB_URL', 'http://127.0.0.1:6363')
    db = os.getenv('TERMINUSDB_DB', 'admin')
    user = os.getenv('TERMINUSDB_USER', 'admin')
    key = os.getenv('TERMINUSDB_PASSWORD', '')
    token = os.getenv('TERMINUSDB_TOKEN', '')
    client = WOQLClient(url)
    if token:
        client.connect(db=db, team=user, jwt_token=token)
    else:
        client.connect(db=db, team=user, key=key)
    return client


def upsert_docs(client: WOQLClient, docs: List[Dict[str, Any]]) -> int:
    n = 0
    for d in docs:
        try:
            client.update_document(d)
        except Exception:
            client.insert_document(d)
        n += 1
    return n


async def migrate_repos(engine, limit: int, dry_run: bool) -> Dict[str, Any]:
    total = await count_table(engine, 'repositories')
    rows = await fetch_all(engine, "SELECT id, name, owner, url, language, stars, forks FROM repositories LIMIT :k", {"k": limit})
    docs = [
        {
            "@type": "Repo",
            "@id": f"Repo/{r['id']}",
            "name": r.get("name"),
            "owner": r.get("owner"),
            "url": r.get("url"),
            "language": r.get("language"),
            "stars": int(r.get("stars") or 0),
            "forks": int(r.get("forks") or 0),
        }
        for r in rows
    ]
    if dry_run:
        return {"entity": "repos", "dry_run": True, "migrated": 0, "would_write": len(docs), "total": total}
    client = td_client()
    n = upsert_docs(client, docs)
    return {"entity": "repos", "dry_run": False, "migrated": n, "total": total}


async def migrate_files(engine, limit: int, dry_run: bool) -> Dict[str, Any]:
    total = await count_table(engine, 'files')
    rows = await fetch_all(engine, "SELECT id, repository_id, path, size, sha256 FROM files LIMIT :k", {"k": limit})
    docs = [
        {
            "@type": "File",
            "@id": f"File/{r['id']}",
            "path": r.get("path"),
            "repo": f"Repo/{r['repository_id']}" if r.get("repository_id") else None,
        }
        for r in rows
    ]
    if dry_run:
        return {"entity": "files", "dry_run": True, "migrated": 0, "would_write": len(docs), "total": total}
    client = td_client()
    n = upsert_docs(client, docs)
    return {"entity": "files", "dry_run": False, "migrated": n, "total": total}


async def migrate_chunks(engine, limit: int, dry_run: bool) -> Dict[str, Any]:
    total = await count_table(engine, 'chunks')
    rows = await fetch_all(engine, "SELECT id, file_id, index, text FROM chunks LIMIT :k", {"k": limit})
    docs = [
        {
            "@type": "Chunk",
            "@id": f"Chunk/{r['id']}",
            "index": int(r.get("index") or 0),
            "text": r.get("text") or "",
            "file": f"File/{r['file_id']}" if r.get("file_id") else None,
        }
        for r in rows
    ]
    if dry_run:
        return {"entity": "chunks", "dry_run": True, "migrated": 0, "would_write": len(docs), "total": total}
    client = td_client()
    n = upsert_docs(client, docs)
    return {"entity": "chunks", "dry_run": False, "migrated": n, "total": total}


async def migrate_embeddings(engine, limit: int, dry_run: bool) -> Dict[str, Any]:
    total = await count_table(engine, 'embeddings')
    rows = await fetch_all(engine, "SELECT id, repository_id, content_type, content_path, embedding_vector, model_name FROM embeddings LIMIT :k", {"k": limit})
    docs = [
        {
            "@type": "Embedding",
            "@id": f"Embedding/{r['id']}",
            "model": r.get("model_name") or "",
            "vector": r.get("embedding_vector") or "",
            "repo": f"Repo/{r['repository_id']}" if r.get("repository_id") else None,
            # Note: chunk link requires chunk IDs; omitted unless present in DB
        }
        for r in rows
    ]
    if dry_run:
        return {"entity": "embeddings", "dry_run": True, "migrated": 0, "would_write": len(docs), "total": total}
    client = td_client()
    n = upsert_docs(client, docs)
    return {"entity": "embeddings", "dry_run": False, "migrated": n, "total": total}


async def run_async(entities: List[str], limit: int = 1000, dry_run: bool = True) -> Dict[str, Any]:
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    results = []
    for e in entities:
        if e in {"repos", "repositories"}:
            results.append(await migrate_repos(engine, limit, dry_run))
        elif e == "files":
            results.append(await migrate_files(engine, limit, dry_run))
        elif e == "chunks":
            results.append(await migrate_chunks(engine, limit, dry_run))
        elif e == "embeddings":
            results.append(await migrate_embeddings(engine, limit, dry_run))
        else:
            results.append({"entity": e, "error": "unknown entity"})
    return {"entities": entities, "limit": limit, "dry_run": dry_run, "results": results}


if __name__ == "__main__":
    payload = json.loads(os.environ.get("MIGRATION_PAYLOAD", "{}"))
    entities = payload.get("entities", ["repos"])
    limit = int(payload.get("limit", 1000))
    dry_run = bool(payload.get("dry_run", True))
    out = asyncio.run(run_async(entities, limit, dry_run))
    print(json.dumps(out))
