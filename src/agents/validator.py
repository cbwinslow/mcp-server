from __future__ import annotations
"""
Validation agent using pydantic-ai to compare backends and run integrity checks.
"""

from typing import Dict, Any, Optional
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text as sql_text
from pydantic_ai import Agent, RunContext
from graph_clients.base import select_backend
from settings.global_settings import SettingsStore


async def run_validation(prefer: Optional[str] = None) -> Dict[str, Any]:
    settings = SettingsStore().read()
    be = select_backend(settings, prefer=prefer)

    # Basic graph metrics
    insights = be.insights()

    # Postgres snapshot
    pg_url = os.getenv('DATABASE_URL')
    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        def one(q):
            return (await conn.execute(sql_text(q))).mappings().first()
        repos_c = (await conn.execute(sql_text('SELECT count(1) AS c FROM repositories'))).scalar()
        files_c = (await conn.execute(sql_text('SELECT count(1) AS c FROM files'))).scalar() if (await conn.exec_driver_sql("SELECT to_regclass('public.files')")).scalar() else 0
        chunks_c = (await conn.execute(sql_text('SELECT count(1) AS c FROM chunks'))).scalar() if (await conn.exec_driver_sql("SELECT to_regclass('public.chunks')")).scalar() else 0
        embeds_c = (await conn.execute(sql_text('SELECT count(1) AS c FROM embeddings'))).scalar()
        null_files = (await conn.execute(sql_text('SELECT count(1) FROM files WHERE repository_id IS NULL'))).scalar() if files_c else 0
        null_chunks = (await conn.execute(sql_text('SELECT count(1) FROM chunks WHERE file_id IS NULL'))).scalar() if chunks_c else 0

    # Graph snapshot for Repo/File/Chunk/Embedding
    graph_counts: Dict[str, int] = {}
    try:
        # Try to infer from insights across backends
        if 'classes' in insights:  # TerminusDB
            m = { (c.get('class') or '').split('/')[-1]: int(c.get('count') or 0) for c in insights['classes'] }
            graph_counts = { 'Repo': m.get('Repo', 0), 'File': m.get('File', 0), 'Chunk': m.get('Chunk', 0), 'Embedding': m.get('Embedding', 0) }
        elif 'labels' in insights:  # Neo4j
            m = { (r.get('label') or (r.get('l') if isinstance(r,dict) else None)): int(r.get('cnt') or 0) for r in insights['labels'] }
            graph_counts = { 'Repo': m.get('Repo', 0), 'File': m.get('File', 0), 'Chunk': m.get('Chunk', 0), 'Embedding': m.get('Embedding', 0) }
        elif 'tags' in insights:  # Nebula
            m = { t.get('tag'): int(t.get('count') or 0) for t in insights['tags'] }
            graph_counts = { 'Repo': m.get('Repo', 0), 'File': m.get('File', 0), 'Chunk': m.get('Chunk', 0), 'Embedding': m.get('Embedding', 0) }
    except Exception:
        graph_counts = {}

    # Findings
    issues = []
    def diff(name: str, pg: int, g: int):
        if pg != g:
            issues.append({ 'type': 'count_mismatch', 'entity': name, 'postgres': pg, 'graph': g })

    diff('Repo', int(repos_c or 0), graph_counts.get('Repo', 0))
    diff('File', int(files_c or 0), graph_counts.get('File', 0))
    diff('Chunk', int(chunks_c or 0), graph_counts.get('Chunk', 0))
    diff('Embedding', int(embeds_c or 0), graph_counts.get('Embedding', 0))
    if null_files:
        issues.append({ 'type': 'null_ref', 'entity': 'File', 'field': 'repository_id', 'count': int(null_files) })
    if null_chunks:
        issues.append({ 'type': 'null_ref', 'entity': 'Chunk', 'field': 'file_id', 'count': int(null_chunks) })

    # Summarize
    score = max(0, 100 - 10*len([i for i in issues if i.get('type')!='count_mismatch']) - 2*len([i for i in issues if i.get('type')=='count_mismatch']))

    # Optional LLM summary
    system = "Summarize issues tersely; suggest next actions."  # keep it minimal if LLM unavailable
    agent = Agent(system=system)
    prompt = f"Graph counts: {graph_counts}; PG repos={repos_c}, files={files_c}, chunks={chunks_c}, embeddings={embeds_c}. Issues: {issues}"
    summary = await agent.run(prompt)

    return {
        'graph_counts': graph_counts,
        'postgres_counts': { 'repositories': int(repos_c or 0), 'files': int(files_c or 0), 'chunks': int(chunks_c or 0), 'embeddings': int(embeds_c or 0) },
        'issues': issues,
        'score': score,
        'summary': summary.output_text,
    }
