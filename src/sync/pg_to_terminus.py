#!/usr/bin/env python3
"""
Sync Postgres entities into TerminusDB as simple documents/triples.
This preserves configuration separately; mapping is configurable later.
"""

import os
import asyncio
from typing import Any, Dict, List
from terminusdb_client import WOQLClient
from sqlalchemy.ext.asyncio import create_async_engine


async def fetch_repos(engine, limit=1000) -> List[Dict[str, Any]]:
    async with engine.connect() as conn:
        res = await conn.execute(f"SELECT id, name, owner, url, description, language, stars, forks FROM repositories LIMIT {limit}")
        cols = res.keys()
        rows = [dict(zip(cols, r)) for r in res]
        return rows


def upsert_repos(client: WOQLClient, docs: List[Dict[str, Any]]):
    # Simple doc model: type Repo with properties
    for d in docs:
        doc = {
            "@type": "Repo",
            "@id": f"Repo/{d['id']}" if d.get('id') else f"Repo/{d['owner']}-{d['name']}",
            "name": d.get('name'),
            "owner": d.get('owner'),
            "url": d.get('url'),
            "language": d.get('language'),
            "stars": int(d.get('stars') or 0),
            "forks": int(d.get('forks') or 0),
        }
        try:
            client.update_document(doc)
        except Exception:
            client.insert_document(doc)


async def main():
    db_url = os.getenv('DATABASE_URL')
    term_url = os.getenv('TERMINUSDB_URL', 'http://127.0.0.1:6363')
    term_db = os.getenv('TERMINUSDB_DB', 'admin')
    term_user = os.getenv('TERMINUSDB_USER', 'admin')
    term_key = os.getenv('TERMINUSDB_PASSWORD', '')

    engine = create_async_engine(db_url)
    repos = await fetch_repos(engine)

    client = WOQLClient(term_url)
    client.connect(db=term_db, team=term_user, key=term_key)
    upsert_repos(client, repos)
    print({"synced_repos": len(repos)})


if __name__ == '__main__':
    asyncio.run(main())
