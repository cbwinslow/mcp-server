#!/usr/bin/env python3
"""
MCP Server - Model Context Protocol Server for GitHub Repository Ingestion
Provides REST API endpoints for CrewAI agents to interact with MCP components.
NOTE: Uses Postgres via async SQLAlchemy (no SQLite).
"""

import os
import json
import logging
import uuid
from urllib.parse import urlparse
from contextvars import ContextVar
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .db_async import AsyncDatabase
import jwt
from .llama_pipeline import index_texts  # for future use

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import text as sql_text
from neo4j import GraphDatabase
import anyio
from pathlib import Path
from settings.global_settings import SettingsStore
import subprocess
from openai import OpenAI
from graph_clients.base import select_backend
from agents.validator import run_validation
import httpx
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from prometheus_client import Counter, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from collections import deque
from pathlib import Path

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
role_ctx: ContextVar[Optional[str]] = ContextVar("role", default=None)

def configure_logging():
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    base_logger = structlog.get_logger("mcp")
    return base_logger

logger = configure_logging()

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server for GitHub Repository Ingestion",
    version="1.0.0"
)

# Optional Sentry
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.05)
    app.add_middleware(SentryAsgiMiddleware)

# Optional OpenTelemetry (OTLP HTTP)
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "mcp-api")})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

# CORS allowlist from env (with sensible defaults)
WEB_BASE_URL = os.getenv("WEB_BASE_URL") or os.getenv("NEXT_PUBLIC_WEB_BASE")
origins = [
    o for o in [
        WEB_BASE_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://mcp.cloudcurio.cc",
    ] if o
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(rid)
    import structlog
    structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
    # Access log timing
    import time
    start = time.perf_counter()
    response = await call_next(request)
    dur_ms = int((time.perf_counter() - start) * 1000)
    try:
        logger.info("access", method=request.method, path=request.url.path, status=response.status_code, ms=dur_ms)
    except Exception:
        pass
    response.headers["X-Request-ID"] = rid
    return response

@app.get("/metrics")
async def metrics(authorization: Optional[str] = None):
    # Optional protection for metrics endpoint
    if os.getenv("REQUIRE_AUTH_METRICS", "false").lower() in {"1","true","yes"}:
        # Reuse JWT verification; do not require admin
        await verify_jwt(authorization)
    data = generate_latest(registry)
    from fastapi.responses import Response
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/admin/logs")
@limiter.limit("60/minute")
async def get_logs(limit: int = 200, event: Optional[str] = None, after_seq: Optional[int] = None, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        lim = max(1, min(int(limit), 1000))
    except Exception:
        lim = 200
    entries = list(_audit_buffer)
    if after_seq is not None:
        try:
            a = int(after_seq)
            entries = [e for e in entries if (e.get('seq') or 0) > a]
        except Exception:
            pass
    if not after_seq:
        entries = entries[-lim:]
    if event:
        entries = [e for e in entries if event.lower() in str(e.get('event','')).lower()]
    max_seq = entries[-1]['seq'] if entries else (_audit_buffer[-1]['seq'] if _audit_buffer else 0)
    return {"status": "success", "count": len(entries), "max_seq": max_seq, "logs": entries}


@app.get("/admin/validation/reports")
@limiter.limit("30/minute")
async def list_validation_reports(limit: int = 10, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        lim = max(1, min(int(limit), 50))
    except Exception:
        lim = 10
    base = Path("/var/log/mcp")
    files = []
    if base.exists():
        for p in sorted(base.glob("validation-*.json"), key=lambda x: x.name, reverse=True)[:lim]:
            try:
                files.append({
                    'name': p.name,
                    'size': p.stat().st_size,
                    'modified': datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()+'Z',
                })
            except Exception:
                pass
    return { 'status': 'success', 'files': files }


@app.get("/admin/validation/reports/{name}")
@limiter.limit("30/minute")
async def get_validation_report(name: str, auth=Depends(verify_jwt)):
    require_admin(auth)
    # Basic sanitization
    if '/' in name or '\\' in name:
        raise HTTPException(status_code=400, detail="invalid name")
    p = Path("/var/log/mcp") / name
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="not found")
    if not name.startswith("validation-") or not name.endswith(".json"):
        raise HTTPException(status_code=400, detail="unsupported file")
    try:
        data = p.read_text()[:2_000_000]
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=data, media_type='application/json')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/validation/last")
@limiter.limit("30/minute")
async def get_last_validation(auth=Depends(verify_jwt)):
    require_admin(auth)
    base = Path("/var/log/mcp")
    if not base.exists():
        return {"status":"success","latest":None,"previous":None}
    files = sorted(base.glob("validation-*.json"), key=lambda x: x.name, reverse=True)
    out = {"status":"success","latest":None,"previous":None}
    def read(p: Path):
        try:
            import json as _json
            data = _json.loads(p.read_text()[:2_000_000])
            score = data.get('score')
            return {
                'name': p.name,
                'modified': datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()+'Z',
                'size': p.stat().st_size,
                'score': score,
                'summary': data.get('summary',''),
            }
        except Exception:
            return None
    if files:
        out['latest'] = read(files[0])
    if len(files) > 1:
        out['previous'] = read(files[1])
    return out


class SeedSampleRequest(BaseModel):
    repos: int = 5
    files_per_repo: int = 2
    chunks_per_file: int = 2
    dry_run: bool = True


@app.post("/admin/seed/sample")
@limiter.limit("10/minute")
async def seed_sample(req: SeedSampleRequest, auth=Depends(verify_jwt)):
    require_admin(auth)
    import uuid as _uuid
    import random as _rand
    repos = max(0, min(req.repos, 100))
    fpr = max(0, min(req.files_per_repo, 20))
    cpf = max(0, min(req.chunks_per_file, 50))
    inserted = {"repositories": 0, "files": 0, "chunks": 0}
    if req.dry_run:
        return {"status": "success", "dry_run": True, "would_insert": {"repositories": repos, "files": repos*fpr, "chunks": repos*fpr*cpf}}
    async with db.engine.begin() as conn:
        for ri in range(repos):
            rid = str(_uuid.uuid4())
            name = f"sample-repo-{ri+1}"
            await conn.execute(sql_text(
                """
                INSERT INTO repositories (id, name, owner, url, description, language, stars, forks, added_at, processed)
                VALUES (:id, :name, 'sample', :url, :desc, :lang, :stars, :forks, now(), false)
                """),
                {"id": rid, "name": name, "url": f"https://example.com/{name}", "desc": "Sample repository", "lang": "Python", "stars": _rand.randint(0, 200), "forks": _rand.randint(0, 50)}
            )
            inserted["repositories"] += 1
            for fi in range(fpr):
                fid = str(_uuid.uuid4())
                path = f"/src/module_{fi+1}.py"
                await conn.execute(sql_text(
                    """
                    INSERT INTO files (id, repository_id, path, size, sha256, created_at, updated_at)
                    VALUES (:id, :rid, :path, :size, :sha, now(), now())
                    """),
                    {"id": fid, "rid": rid, "path": path, "size": _rand.randint(100, 5000), "sha": None}
                )
                inserted["files"] += 1
                for ci in range(cpf):
                    cid = str(_uuid.uuid4())
                    await conn.execute(sql_text(
                        """
                        INSERT INTO chunks (id, file_id, index, text, created_at)
                        VALUES (:id, :fid, :idx, :text, now())
                        """),
                        {"id": cid, "fid": fid, "idx": ci, "text": f"Sample chunk {ci+1} for {path}"}
                    )
                    inserted["chunks"] += 1
    audit("seed_sample", **inserted)
    return {"status": "success", "inserted": inserted}


@app.post("/admin/seed/clear")
@limiter.limit("10/minute")
async def seed_clear(auth=Depends(verify_jwt)):
    require_admin(auth)
    deleted = {"chunks": 0, "files": 0, "repositories": 0}
    async with db.engine.begin() as conn:
        r = await conn.execute(sql_text("""
            DELETE FROM chunks WHERE file_id IN (
              SELECT id FROM files WHERE repository_id IN (SELECT id FROM repositories WHERE owner = 'sample')
            )
        """))
        deleted["chunks"] = r.rowcount or 0
        r = await conn.execute(sql_text("DELETE FROM files WHERE repository_id IN (SELECT id FROM repositories WHERE owner = 'sample')"))
        deleted["files"] = r.rowcount or 0
        r = await conn.execute(sql_text("DELETE FROM repositories WHERE owner = 'sample'"))
        deleted["repositories"] = r.rowcount or 0
    audit("seed_clear", **deleted)
    return {"status": "success", "deleted": deleted}

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("DATABASE_URL must be a Postgres URL; SQLite is not supported.")

# Initialize database (async)
db = AsyncDatabase(DATABASE_URL)

# Global status tracking (could be moved to database)
crawler_status = {"status": "idle", "last_run": None, "progress": 0}
extractor_status = {"status": "idle", "last_run": None, "processed": 0}
embeddings_status = {"status": "idle", "last_run": None, "generated": 0}

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query_type: str = "select"
    table: str = "repositories"
    filters: Dict[str, Any] = {}
    limit: int = 100

class CrawlerRequest(BaseModel):
    action: str = "status"
    target: str = "all"
    config: Dict[str, Any] = {}

class EmbeddingsRequest(BaseModel):
    content_type: str = "code"
    batch_size: int = 100
    source: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "mcp_chunks"
    hybrid: bool = False
    expand_graph: bool = False

class IndexRequest(BaseModel):
    texts: List[str]
    collection: str = "mcp_chunks"

class GraphQueryRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None
    mode: str = "read"  # read|write
    backend: Optional[str] = None

class GraphTraverseRequest(BaseModel):
    # Simple, safe traversals
    op: str  # neighbors|khop|shortest_path
    node_label: Optional[str] = None
    node_id: Optional[str] = None
    rel_types: Optional[List[str]] = None
    direction: str = "OUT"  # OUT|IN|BOTH
    k: int = 1
    dst_label: Optional[str] = None
    dst_id: Optional[str] = None

class SettingsUpdate(BaseModel):
    data: Dict[str, Any]

class ServiceActionRequest(BaseModel):
    unit: str
    action: str  # status|start|stop|restart

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    top_k: int = 5
    collection: str = "mcp_chunks"

class KVSetRequest(BaseModel):
    items: Dict[str, str]

class ConnectivityResult(BaseModel):
    ok: bool
    detail: Optional[str] = None

class MigrationV2Request(BaseModel):
    entities: List[str] = ["repos"]
    limit: int = 1000
    dry_run: bool = True


@app.post("/admin/migrate/pg-to-terminus")
@limiter.limit("20/minute")
async def migrate_pg_to_terminus(limit: int = 1000, auth=Depends(verify_jwt)):
    require_admin(auth)
    """One-off migration: copy repositories table to TerminusDB as Repo documents.
    This is a starter path — mapping is configurable later and config remains separate.
    """
    try:
        import subprocess, os
        env = os.environ.copy()
        env['PYTHONPATH'] = env.get('PYTHONPATH','')
        env['TERMINUSDB_URL'] = env.get('TERMINUSDB_URL', 'http://127.0.0.1:6363')
        r = subprocess.run(["python", "-m", "src.sync.pg_to_terminus"], capture_output=True, text=True, env=env, timeout=300)
        ok = r.returncode == 0
        return {"status": "success" if ok else "failed", "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/terminus/init-schema")
@limiter.limit("10/minute")
async def terminus_init_schema(auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        import subprocess, os
        env = os.environ.copy()
        r = subprocess.run(["python", "-m", "src.sync.terminus_schema"], capture_output=True, text=True, env=env, timeout=120)
        ok = r.returncode == 0
        return {"status": "success" if ok else "failed", "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        logger.error(f"Terminus schema error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/validate")
@limiter.limit("10/minute")
async def admin_validate(backend: Optional[str] = None, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        report = await run_validation(backend)
        return {"status": "success", "report": report}
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/insights")
async def graph_insights(backend: Optional[str] = None, auth=Depends(verify_jwt)):
    """Curated graph insights: label counts, edge counts, top-degree nodes, dangling nodes."""
    def _run():
        settings = SettingsStore().read()
        be = select_backend(settings, prefer=backend)
        return be.insights()

    try:
        data = await anyio.to_thread.run_sync(_run)
        return {"status": "success", "insights": data}
    except Exception as e:
        logger.error(f"Insights error: {e}")
        raise HTTPException(status_code=500, detail=f"Insights failed: {str(e)}")

def get_jwt_secret() -> Optional[str]:
    # Use GoTrue/Supabase JWT secret if available
    return os.getenv("JWT_SECRET") or os.getenv("GOTRUE_JWT_SECRET")

def require_auth_enabled() -> bool:
    return os.getenv("REQUIRE_AUTH", "false").lower() in {"1", "true", "yes"}

async def verify_jwt(authorization: Optional[str] = None):
    """Optional JWT verification using shared secret (HS256)."""
    if not require_auth_enabled():
        return None
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    secret = get_jwt_secret()
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

@app.on_event("startup")
async def on_startup():
    # Create tables if not present (use Alembic for schema migrations in prod)
    await db.init_models()
    # Ensure settings file exists
    SettingsStore().read()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MCP Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status/{component}")
async def get_component_status(component: str, auth=Depends(verify_jwt)):
    """
    Get status of MCP server components

    Args:
        component: Component name (crawler, extractor, embeddings, database)
    """
    component_statuses = {
        "crawler": crawler_status,
        "extractor": extractor_status,
        "embeddings": embeddings_status,
        "database": {
            "status": "connected",
            "size": db.get_stats().get("total_repositories", 0),
            "last_updated": db.get_stats().get("last_updated")
        }
    }

    if component not in component_statuses:
        raise HTTPException(status_code=404, detail=f"Component '{component}' not found")

    return component_statuses[component]

@app.get("/status")
async def get_all_status(auth=Depends(verify_jwt)):
    """Get status of all MCP server components"""
    try:
        # Get actual database status
        db_stats = await db.get_stats()

        return {
            "crawler": crawler_status,
            "extractor": extractor_status,
            "embeddings": embeddings_status,
            "database": {
                "status": "connected",
                "size": db_stats.get("total_repositories", 0),
                "last_updated": db_stats.get("last_updated"),
                "tables": db_stats.get("tables", [])
            },
            "overall": "healthy"  # Simplified for demo
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {
            "crawler": crawler_status,
            "extractor": extractor_status,
            "embeddings": embeddings_status,
            "database": {
                "status": "error",
                "error": str(e)
            },
            "overall": "degraded"
        }

@app.post("/db/query")
async def execute_query(request: QueryRequest, auth=Depends(verify_jwt)):
    """
    Execute database queries

    Args:
        request: Query parameters
    """
    try:
        if request.table == "repositories":
            # Get repositories from database
            results = await db.get_repositories(
                filters=request.filters,
                limit=request.limit,
                offset=0,
            )

            return {
                "status": "success",
                "query_type": request.query_type,
                "table": request.table,
                "count": len(results),
                "results": results
            }
        elif request.table == "stats":
            # Get database statistics
            stats = await db.get_stats()
            return {
                "status": "success",
                "query_type": request.query_type,
                "table": request.table,
                "results": stats
            }
        else:
            return {
                "status": "error",
                "message": f"Table '{request.table}' not found",
                "results": []
            }

    except Exception as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@app.post("/crawler/control")
async def control_crawler(request: CrawlerRequest, background_tasks: BackgroundTasks, auth=Depends(verify_jwt)):
    """
    Control GitHub crawler operations

    Args:
        request: Crawler control parameters
    """
    global crawler_status

    try:
        if request.action == "status":
            return crawler_status

        elif request.action == "start":
            if crawler_status["status"] == "running":
                return {"status": "error", "message": "Crawler already running"}

            crawler_status.update({
                "status": "running",
                "last_run": datetime.now().isoformat(),
                "progress": 0,
                "target": request.target,
                "config": request.config
            })

            # Simulate crawler work in background
            background_tasks.add_task(simulate_crawler_work)

            return {
                "status": "success",
                "message": f"Crawler started for target: {request.target}",
                "job_id": "crawler_001"
            }

        elif request.action == "stop":
            if crawler_status["status"] != "running":
                return {"status": "error", "message": "Crawler not running"}

            crawler_status["status"] = "stopped"
            return {"status": "success", "message": "Crawler stopped"}

        elif request.action == "config":
            crawler_status["config"] = request.config
            return {"status": "success", "message": "Crawler configuration updated"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except Exception as e:
        logger.error(f"Crawler control error: {e}")
        raise HTTPException(status_code=500, detail=f"Crawler control failed: {str(e)}")

@app.post("/embeddings/generate")
async def generate_embeddings(request: EmbeddingsRequest, background_tasks: BackgroundTasks, auth=Depends(verify_jwt)):
    """
    Generate embeddings for harvested content

    Args:
        request: Embeddings generation parameters
    """
    global embeddings_status

    try:
        embeddings_status.update({
            "status": "running",
            "last_run": datetime.now().isoformat(),
            "content_type": request.content_type,
            "batch_size": request.batch_size,
            "source": request.source
        })

        # Simulate embeddings generation in background
        background_tasks.add_task(simulate_embeddings_generation, request)

        return {
            "status": "success",
            "message": f"Embeddings generation started for {request.content_type}",
            "job_id": "embeddings_001"
        }

    except Exception as e:
        logger.error(f"Embeddings generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Embeddings generation failed: {str(e)}")

@app.post("/repositories")
async def add_repository(repo_data: Dict[str, Any], auth=Depends(verify_jwt)):
    """
    Add a repository to the database

    Args:
        repo_data: Repository information
    """
    try:
        # Add repository using database module
        repo_id = await db.add_repository(repo_data)

        return {
            "status": "success",
            "message": "Repository added successfully",
            "repo_id": repo_id
        }

    except Exception as e:
        logger.error(f"Add repository error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add repository: {str(e)}")

@app.get("/repositories")
async def list_repositories(limit: int = 50, offset: int = 0, auth=Depends(verify_jwt)):
    """
    List repositories in the database

    Args:
        limit: Maximum number of results
        offset: Offset for pagination
    """
    try:
        # Get repositories from database
        results = await db.get_repositories(limit=limit, offset=offset)
        total_count = await db.get_repository_count()

        return {
            "status": "success",
            "count": len(results),
            "total": total_count,
            "repositories": results
        }

    except Exception as e:
        logger.error(f"List repositories error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")


@app.post("/search")
async def search(request: SearchRequest, auth=Depends(verify_jwt)):
    """Hybrid search endpoint powered by LlamaIndex PGVector (basic version)."""
    try:
        # Build PGVector store from DATABASE_URL
        vector_store = PGVectorStore.from_params(
            database_url=DATABASE_URL,
            schema_name="public",
            table_name=request.collection,
        )
        index = VectorStoreIndex.from_vector_store(vector_store)
        qe = index.as_query_engine(similarity_top_k=request.top_k)
        res = qe.query(request.query)

        vec_hits = []
        try:
            for ns in getattr(res, "source_nodes", [])[: request.top_k]:
                vec_hits.append({
                    "text": ns.node.get_content(),
                    "score": getattr(ns, "score", None),
                    "node_id": getattr(ns.node, "node_id", None),
                    "source": "vector",
                })
        except Exception:
            pass

        # Optional text/trigram search over the same collection table
        txt_hits = []
        if request.hybrid:
            try:
                async with db.engine.connect() as conn:
                    # Prefer pg_trgm similarity; fallback to ILIKE position
                    query = sql_text(
                        f"""
                        SELECT id, content, similarity(content, :q) AS sim
                        FROM {request.collection}
                        WHERE content %% :q OR content ILIKE '%' || :q || '%'
                        ORDER BY sim DESC NULLS LAST
                        LIMIT :k
                        """
                    )
                    rows = (await conn.execute(query, {"q": request.query, "k": request.top_k})).mappings().all()
                    for r in rows:
                        txt_hits.append({
                            "text": r.get("content"),
                            "score": float(r.get("sim") or 0.0),
                            "node_id": r.get("id"),
                            "source": "text",
                        })
            except Exception as e:
                logger.warning(f"Hybrid text search failed: {e}")

        # Merge results: prefer vector hits, then add unique text hits
        merged = vec_hits.copy()
        seen_ids = {h.get("node_id") for h in merged if h.get("node_id")}
        for h in txt_hits:
            if h.get("node_id") not in seen_ids:
                merged.append(h)
                seen_ids.add(h.get("node_id"))
            if len(merged) >= request.top_k:
                break

        return {
            "status": "success",
            "query": request.query,
            "top_k": request.top_k,
            "collection": request.collection,
            "results": merged,
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/admin/index")
@limiter.limit("20/minute")
async def admin_index(request: IndexRequest, auth=Depends(verify_jwt)):
    require_admin(auth)
    """Admin endpoint to index raw texts into the PGVector collection via LlamaIndex."""
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="No texts provided")
        count = index_texts(request.texts, collection=request.collection)
        return {"status": "success", "indexed": count, "collection": request.collection}
    except Exception as e:
        logger.error(f"Index error: {e}")
        raise HTTPException(status_code=500, detail=f"Index failed: {str(e)}")


@app.post("/crawl")
async def proxy_crawl(payload: Dict[str, Any], auth=Depends(verify_jwt)):
    """Proxy crawl request to the external MCP-crawl4ai-rag server if an HTTP /crawl endpoint exists.
    This keeps agents talking to one API. Configure MCP_CRAWL4AI_URL.
    """
    base = os.getenv("MCP_CRAWL4AI_URL", "http://127.0.0.1:8051")
    url = f"{base.rstrip('/')}/crawl"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error(f"Proxy crawl error: {e}")
        raise HTTPException(status_code=502, detail=f"Crawl proxy failed: {str(e)}")


def _cf_env():
    token = os.getenv("CF_API_TOKEN")
    acct = os.getenv("CF_ACCOUNT_ID")
    ns_title = os.getenv("CF_KV_NAMESPACE_TITLE", "mcp-secrets")
    prefix = os.getenv("CF_KV_ENV_PREFIX", "prod")
    if not (token and acct):
        raise HTTPException(status_code=500, detail="Cloudflare API not configured")
    return token, acct, ns_title, prefix

async def _cf_ns_id(client: httpx.AsyncClient, token: str, acct: str, ns_title: str) -> str:
    r = await client.get(f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces",
                         headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    for ns in r.json().get("result", []):
        if ns.get("title") == ns_title:
            return ns.get("id")
    # Create if missing
    rc = await client.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces",
                           headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                           json={"title": ns_title})
    rc.raise_for_status()
    return rc.json()["result"]["id"]

def _is_admin(payload: Optional[dict]) -> bool:
    if payload is None:
        return not require_auth_enabled()
    if payload.get("role") in {"admin", "owner"}:
        return True
    if payload.get("is_admin") is True:
        return True
    # Supabase/GoTrue app_metadata roles
    appm = payload.get("app_metadata") or {}
    if isinstance(appm, dict) and appm.get("role") in {"admin", "owner"}:
        return True
    return False

def require_admin(auth_payload: Optional[dict]):
    if not _is_admin(auth_payload):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    try:
        import structlog
        uid = None
        if isinstance(auth_payload, dict):
            uid = auth_payload.get("sub") or auth_payload.get("user_id") or auth_payload.get("email")
        structlog.contextvars.bind_contextvars(user_id=uid, role=(auth_payload or {}).get("role"))
        user_ctx.set(uid)
        role_ctx.set((auth_payload or {}).get("role"))
    except Exception:
        pass


@app.get("/admin/kv")
@limiter.limit("120/minute")
async def kv_get(keys: str, auth=Depends(verify_jwt)):
    require_admin(auth)
    token, acct, ns_title, prefix = _cf_env()
    key_list = [k.strip() for k in keys.split(',') if k.strip()]
    async with httpx.AsyncClient(timeout=15) as client:
        ns_id = await _cf_ns_id(client, token, acct, ns_title)
        values: Dict[str, Optional[str]] = {}
        for k in key_list:
            kr = await client.get(f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces/{ns_id}/values/{prefix}:{k}",
                                  headers={"Authorization": f"Bearer {token}"})
            values[k] = kr.text if kr.status_code == 200 else None
        return {"status": "success", "values": values}

@app.put("/admin/kv")
@limiter.limit("60/minute")
async def kv_put(req: KVSetRequest, auth=Depends(verify_jwt)):
    require_admin(auth)
    token, acct, ns_title, prefix = _cf_env()
    async with httpx.AsyncClient(timeout=15) as client:
        ns_id = await _cf_ns_id(client, token, acct, ns_title)
        for k, v in (req.items or {}).items():
            await client.put(f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces/{ns_id}/values/{prefix}:{k}",
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
                             content=v or "")
    return {"status": "success"}

@app.get("/admin/kv/list")
@limiter.limit("120/minute")
async def kv_list(prefix: Optional[str] = None, auth=Depends(verify_jwt)):
    require_admin(auth)
    token, acct, ns_title, env_prefix = _cf_env()
    async with httpx.AsyncClient(timeout=15) as client:
        ns_id = await _cf_ns_id(client, token, acct, ns_title)
        pr = f"{env_prefix}:{prefix or ''}"
        r = await client.get(
            f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces/{ns_id}/keys",
            params={"limit": 1000, "prefix": pr},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        # Strip env prefix when returning keys
        keys = [k.get("name", "").split(":",1)[-1] for k in r.json().get("result", [])]
        return {"status": "success", "keys": keys}


@app.get("/admin/test/connectivity")
@limiter.limit("30/minute")
async def test_connectivity(auth=Depends(verify_jwt)):
    require_admin(auth)
    results: Dict[str, Dict[str, Any]] = {}

    # Postgres
    try:
        async with db.engine.connect() as conn:
            await conn.execute(sql_text("SELECT 1"))
        results["postgres"] = {"ok": True}
    except Exception as e:
        results["postgres"] = {"ok": False, "detail": str(e)}

    # Neo4j
    try:
        driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD") or ""))
        with driver.session() as sess:
            sess.run("RETURN 1 AS ok").consume()
        driver.close()
        results["neo4j"] = {"ok": True}
    except Exception as e:
        results["neo4j"] = {"ok": False, "detail": str(e)}

    # TerminusDB
    try:
        from terminusdb_client import WOQLClient
        settings = SettingsStore().read(); tb = settings.get("terminusdb", {})
        client = WOQLClient(tb.get("server_url","http://127.0.0.1:6363"))
        tok = tb.get("token");
        if tok:
            client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), jwt_token=tok)
        else:
            client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), key=tb.get("password",""))
        results["terminusdb"] = {"ok": True}
    except Exception as e:
        results["terminusdb"] = {"ok": False, "detail": str(e)}

    # NebulaGraph
    try:
        from nebula3.gclient.net import ConnectionPool
        from nebula3.Config import Config
        settings = SettingsStore().read(); nb = settings.get("nebulagraph", {})
        pool = ConnectionPool(); pool.init([(nb.get("host","127.0.0.1"), int(nb.get("port",9669)))], Config())
        sess = pool.get_session(nb.get("user","root"), nb.get("password",""))
        sess.release(); pool.close()
        results["nebulagraph"] = {"ok": True}
    except Exception as e:
        results["nebulagraph"] = {"ok": False, "detail": str(e)}

    # LocalAI
    try:
        la = os.getenv("LOCALAI_BASE_URL", "http://127.0.0.1:8080")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(la.rstrip('/') + "/health")
            ok = r.status_code < 500
        results["localai"] = {"ok": ok}
    except Exception as e:
        results["localai"] = {"ok": False, "detail": str(e)}

    # API self
    results["api"] = {"ok": True}
    # Persist last tested timestamps in settings for quick UI display
    try:
        store = SettingsStore()
        cfg = store.read()
        admin = cfg.get("admin", {})
        last_test = admin.get("last_test", {})
        now = datetime.utcnow().isoformat() + "Z"
        for k, v in results.items():
            last_test[k] = {"ok": bool(v.get("ok")), "ts": now}
        admin["last_test"] = last_test
        cfg["admin"] = admin
        store.write(cfg)
    except Exception:
        pass
    audit("connectivity_test", results={k: v.get('ok') for k, v in results.items()})
    return {"status": "success", "results": results}


@app.post("/admin/migrate/pg-to-terminus-v2")
async def migrate_pg_to_terminus_v2(req: MigrationV2Request, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        env = os.environ.copy()
        env["MIGRATION_PAYLOAD"] = json.dumps(req.model_dump())
        r = subprocess.run(["python", "-m", "src.sync.pg_to_terminus_v2"], capture_output=True, text=True, env=env, timeout=600)
        ok = r.returncode == 0
        summary = {}
        try:
            summary = json.loads(r.stdout or "{}")
        except Exception:
            pass
        audit("migration_v2_run", entities=req.entities, limit=req.limit, dry_run=req.dry_run, ok=ok)
        try:
            metric_migration_runs.labels(dry_run=str(bool(req.dry_run)).lower(), ok=str(bool(ok)).lower()).inc()
        except Exception:
            pass
        return {"status": "success" if ok else "failed", "summary": summary, "stderr_tail": r.stderr[-500:]}
    except Exception as e:
        logger.error("migration_v2_error", err=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/migrate/pg-to-terminus-v2/stream")
@limiter.limit("10/minute")
async def migrate_pg_to_terminus_v2_stream(entities: str = "repos", limit: int = 1000, dry_run: bool = True, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        from src.sync.pg_to_terminus_v2 import run_async as mig_run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {e}")

    ent_list = [e.strip() for e in (entities or '').split(',') if e.strip()] or ["repos"]

    async def gen():
        import json as _json
        # Precompute totals via a dry-run to expose counts without side effects
        totals_summary = None
        try:
            totals_summary = await mig_run(ent_list, limit, True)
        except Exception:
            totals_summary = None
        yield _json.dumps({"phase": "start", "entities": ent_list, "limit": limit, "dry_run": dry_run, "totals": (totals_summary or {}).get('results', [])}) + "\n"
        for i, e in enumerate(ent_list, start=1):
            try:
                res = await mig_run([e], limit, dry_run)
                yield _json.dumps({"phase": "entity_done", "entity": e, "result": res.get("results", [{}])[0], "idx": i, "total": len(ent_list)}) + "\n"
            except Exception as ex:
                yield _json.dumps({"phase": "error", "entity": e, "error": str(ex)}) + "\n"
        try:
            final = await mig_run(ent_list, limit, dry_run)
        except Exception:
            final = {"entities": ent_list, "limit": limit, "dry_run": dry_run}
        yield _json.dumps({"phase": "done", "summary": final}) + "\n"

    audit("migration_v2_stream_start", entities=ent_list, limit=limit, dry_run=dry_run)
    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/graph/query")
async def graph_query(request: GraphQueryRequest, auth=Depends(verify_jwt)):
    """Run a graph query on the selected backend. Cypher for Neo4j, NGQL for Nebula, WOQL JSON for TerminusDB.
    Writes require ALLOW_GRAPH_WRITES=true.
    """
    allow_writes = os.getenv("ALLOW_GRAPH_WRITES", "false").lower() in {"1", "true", "yes"}
    if request.mode.lower() == "write" and not allow_writes:
        raise HTTPException(status_code=403, detail="Graph writes are disabled")

    def _run():
        settings = SettingsStore().read()
        be = select_backend(settings, prefer=request.backend)
        return be.run_query(request.query, request.params or {}, request.mode.lower())

    try:
        records = await anyio.to_thread.run_sync(_run)
        return {"status": "success", "records": records}
    except Exception as e:
        logger.error(f"Graph query error: {e}")
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")


@app.post("/graph/traverse")
async def graph_traverse(req: GraphTraverseRequest, auth=Depends(verify_jwt)):
    """Predefined, safe traversals: neighbors, khop, shortest_path.
    Limits fanout and hop counts to prevent heavy queries.
    """
    op = req.op.lower()
    if op not in {"neighbors", "khop", "shortest_path"}:
        raise HTTPException(status_code=400, detail="Unsupported op")
    if not req.node_label or not req.node_id:
        raise HTTPException(status_code=400, detail="node_label and node_id required")
    rels = req.rel_types or []
    dirmap = {"out": ">", "in": "<", "both": ""}
    d = dirmap.get(req.direction.lower(), ">")
    k = max(1, min(req.k, 4))  # cap k to 4

    def _run():
        driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD") or ""))
        try:
            with driver.session() as sess:
                if op == "neighbors":
                    rel_filter = "|".join(rels) if rels else ""
                    cypher = (
                        f"MATCH (n:{req.node_label} {{id:$id}}) "
                        f"OPTIONAL MATCH (n){d}-[r{(':' + rel_filter) if rel_filter else ''}]-{d}(m) "
                        f"RETURN DISTINCT labels(m) AS labels, m.id AS id, properties(m) AS props LIMIT 200"
                    )
                    res = sess.run(cypher, id=req.node_id)
                    return [r.data() for r in res]
                elif op == "khop":
                    rel_filter = "|".join(rels) if rels else ""
                    cypher = (
                        f"MATCH (n:{req.node_label} {{id:$id}}) "
                        f"CALL apoc.path.expand(n, '{rel_filter}', null, 1, {k}) YIELD path "
                        f"WITH nodes(path) AS ns UNWIND ns AS m RETURN DISTINCT labels(m) AS labels, m.id AS id, properties(m) AS props LIMIT 500"
                    )
                    res = sess.run(cypher, id=req.node_id)
                    return [r.data() for r in res]
                else:  # shortest_path
                    if not req.dst_label or not req.dst_id:
                        raise ValueError("dst_label and dst_id required for shortest_path")
                    cypher = (
                        f"MATCH (a:{req.node_label} {{id:$aid}}), (b:{req.dst_label} {{id:$bid}}) "
                        f"CALL apoc.algo.dijkstra(a, b, null, 'weight') YIELD path, weight "
                        f"RETURN [n IN nodes(path) | {id: n.id, labels: labels(n)}] AS nodes, weight LIMIT 1"
                    )
                    res = sess.run(cypher, aid=req.node_id, bid=req.dst_id)
                    return [r.data() for r in res]
        finally:
            driver.close()

    try:
        records = await anyio.to_thread.run_sync(_run)
        return {"status": "success", "records": records}
    except Exception as e:
        logger.error(f"Traverse error: {e}")
        raise HTTPException(status_code=500, detail=f"Traverse failed: {str(e)}")


@app.get("/graph/test")
async def graph_test(backend: Optional[str] = None, auth=Depends(verify_jwt)):
    try:
        settings = SettingsStore().read()
        be = select_backend(settings, prefer=backend)
        ok = await anyio.to_thread.run_sync(be.test_connection)
        # Persist last tested
        try:
            store = SettingsStore()
            cfg = store.read()
            admin = cfg.get("admin", {})
            last_test = admin.get("last_test", {})
            now = datetime.utcnow().isoformat() + "Z"
            key = (backend or settings.get("graph_backends", {}).get("default", "neo4j")).lower()
            last_test[key] = {"ok": bool(ok), "ts": now}
            admin["last_test"] = last_test
            cfg["admin"] = admin
            store.write(cfg)
        except Exception:
            pass
        audit("graph_test", backend=backend, ok=ok)
        try:
            metric_graph_tests.labels(backend=(backend or settings.get("graph_backends", {}).get("default", "neo4j")), ok=str(bool(ok)).lower()).inc()
        except Exception:
            pass
        return {"status": "success", "backend": backend or settings.get("graph_backends", {}).get("default", "neo4j"), "ok": ok}
    except Exception as e:
        logger.error(f"Graph test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/sample")
async def graph_sample(backend: Optional[str] = None, cls: Optional[str] = None, limit: int = 100, auth=Depends(verify_jwt)):
    """Return a small node/edge set for visualization for the selected backend.
    Neo4j and NebulaGraph supported. TerminusDB returns empty set.
    """
    try:
        settings = SettingsStore().read()
        be = select_backend(settings, prefer=backend)

        def _neo4j_sample():
            driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD") or ""))
            try:
                with driver.session() as sess:
                    ns = sess.run("MATCH (n) RETURN id(n) as id, labels(n) as labels, coalesce(n.id, toString(id(n))) as pid LIMIT 100").data()
                    es = sess.run("MATCH (a)-[r]->(b) RETURN id(r) as id, type(r) as type, id(a) as source, id(b) as target LIMIT 200").data()
                nodes = [{"id": str(n['id']), "label": (n['labels'][0] if n['labels'] else 'Node'), "pid": n['pid']} for n in ns]
                edges = [{"id": str(e['id']), "source": str(e['source']), "target": str(e['target']), "type": e['type']} for e in es]
                return {"nodes": nodes, "edges": edges}
            finally:
                driver.close()

        def _nebula_sample():
            from nebula3.gclient.net import ConnectionPool
            from nebula3.Config import Config
            nb = settings.get("nebulagraph", {})
            pool = ConnectionPool()
            pool.init([(nb.get("host", "127.0.0.1"), int(nb.get("port", 9669)))], Config())
            sess = pool.get_session(nb.get("user", "root"), nb.get("password", ""))
            try:
                space = nb.get("space", "")
                if space:
                    sess.execute(f"USE {space}")
                ns = sess.execute("MATCH (v) RETURN id(v) LIMIT 100")
                nodes = []
                if ns.is_succeeded():
                    for i in range(ns.rows_size()):
                        nodes.append({"id": ns.row_values(i)[0].cast_to_string(), "label": "V"})
                es = sess.execute("MATCH (a)-[e]->(b) RETURN id(a) as a, id(b) as b LIMIT 200")
                edges = []
                if es.is_succeeded():
                    for i in range(es.rows_size()):
                        a = es.row_values(i)[0].cast_to_string(); b = es.row_values(i)[1].cast_to_string()
                        edges.append({"id": f"{a}->{b}-{i}", "source": a, "target": b, "type": "edge"})
                return {"nodes": nodes, "edges": edges}
            finally:
                sess.release()

        # Dispatch
        if backend in ("nebula", "nebulagraph") or (backend is None and settings.get("graph_backends", {}).get("default") in ("nebula","nebulagraph")):
            data = await anyio.to_thread.run_sync(_nebula_sample)
        elif backend in ("terminus", "terminusdb") or (backend is None and settings.get("graph_backends", {}).get("default") in ("terminus","terminusdb")):
            # Build a small graph from triples, optionally filtered by class
            from terminusdb_client import WOQLQuery as WQ
            store = SettingsStore().read()
            tb = store.get("terminusdb", {})
            from terminusdb_client import WOQLClient
            def _terminus_sample():
                client = WOQLClient(tb.get("server_url","http://127.0.0.1:6363"))
                tok = tb.get("token")
                if tok:
                    client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), jwt_token=tok)
                else:
                    client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), key=tb.get("password",""))
                nodes = {}
                edges = []
                if cls:
                    q = (WQ().triple("v:s","rdf:type",cls).limit(limit)).to_dict()
                    res = client.query(q)
                    ids = [b.get('v:s') for b in (res.get('bindings') or [])]
                    for sid in ids:
                        nodes[sid] = {"id": sid, "label": cls}
                        # Fetch outgoing triples for s
                        qo = WQ().triple(sid, "v:p", "v:o").limit(20).to_dict()
                        ro = client.query(qo)
                        for bo in ro.get('bindings', []):
                            o = bo.get('v:o'); p = bo.get('v:p')
                            if o and isinstance(o, str):
                                nodes.setdefault(o, {"id": o, "label": "Value"})
                                edges.append({"id": f"{sid}->{o}-{p}", "source": sid, "target": o, "type": str(p)})
                else:
                    # Generic small triple sample
                    q = WQ().triple("v:s","v:p","v:o").limit(limit).to_dict()
                    res = client.query(q)
                    for b in res.get('bindings', []):
                        s = b.get('v:s'); p = b.get('v:p'); o = b.get('v:o')
                        if isinstance(s, str): nodes.setdefault(s, {"id": s, "label": "S"})
                        if isinstance(o, str): nodes.setdefault(o, {"id": o, "label": "O"})
                        if isinstance(s, str) and isinstance(o, str):
                            edges.append({"id": f"{s}->{o}-{p}", "source": s, "target": o, "type": str(p)})
                return {"nodes": list(nodes.values()), "edges": edges}
            data = await anyio.to_thread.run_sync(_terminus_sample)
        else:
            data = await anyio.to_thread.run_sync(_neo4j_sample)
        return {"status": "success", "graph": data}
    except Exception as e:
        logger.error(f"Graph sample error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/expand")
async def graph_expand(node_id: str, backend: Optional[str] = None, auth=Depends(verify_jwt)):
    """Expand neighbors around a node for visualization. Supports Neo4j and NebulaGraph."""
    try:
        def _neo4j_expand():
            driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD") or ""))
            try:
                nid = int(node_id)
                with driver.session() as sess:
                    ns = sess.run("MATCH (n) WHERE id(n)=$id MATCH (n)-[r]-(m) RETURN id(m) as id, labels(m) as labels, coalesce(m.id, toString(id(m))) as pid, id(r) as rid, type(r) as type, id(startNode(r)) as s, id(endNode(r)) as t LIMIT 100", {"id": nid}).data()
                nodes = [{"id": str(n['id']), "label": (n['labels'][0] if n['labels'] else 'Node'), "pid": n['pid']} for n in ns]
                edges = []
                for n in ns:
                    edges.append({"id": str(n['rid']), "source": str(n['s']), "target": str(n['t']), "type": n['type']})
                return {"nodes": nodes, "edges": edges}
            finally:
                driver.close()

        def _nebula_expand():
            from nebula3.gclient.net import ConnectionPool
            from nebula3.Config import Config
            settings = SettingsStore().read()
            nb = settings.get("nebulagraph", {})
            pool = ConnectionPool()
            pool.init([(nb.get("host", "127.0.0.1"), int(nb.get("port", 9669)))], Config())
            sess = pool.get_session(nb.get("user", "root"), nb.get("password", ""))
            try:
                space = nb.get("space", "")
                if space:
                    sess.execute(f"USE {space}")
                es = sess.execute(f"MATCH (v)-[e]-(m) WHERE id(v)==\"{node_id}\" RETURN id(m) as m LIMIT 100")
                nodes = []
                edges = []
                if es.is_succeeded():
                    for i in range(es.rows_size()):
                        m = es.row_values(i)[0].cast_to_string()
                        nodes.append({"id": m, "label": "V"})
                        edges.append({"id": f"{node_id}->{m}-{i}", "source": node_id, "target": m, "type": "edge"})
                return {"nodes": nodes, "edges": edges}
            finally:
                sess.release()

        if backend in ("nebula", "nebulagraph"):
            data = await anyio.to_thread.run_sync(_nebula_expand)
        elif backend in ("terminus", "terminusdb"):
            from terminusdb_client import WOQLQuery as WQ
            settings = SettingsStore().read(); tb = settings.get("terminusdb", {})
            from terminusdb_client import WOQLClient
            def _terminus_expand():
                client = WOQLClient(tb.get("server_url","http://127.0.0.1:6363"))
                tok = tb.get("token")
                if tok:
                    client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), jwt_token=tok)
                else:
                    client.connect(db=tb.get("db","admin"), team=tb.get("user","admin"), key=tb.get("password",""))
                nodes = { node_id: {"id": node_id, "label": "Node"} }
                edges = []
                # outgoing
                qo = WQ().triple(node_id, "v:p", "v:o").limit(100).to_dict()
                ro = client.query(qo)
                for bo in ro.get('bindings', []):
                    o = bo.get('v:o'); p = bo.get('v:p')
                    if isinstance(o, str):
                        nodes.setdefault(o, {"id": o, "label": "Value"})
                        edges.append({"id": f"{node_id}->{o}-{p}", "source": node_id, "target": o, "type": str(p)})
                # incoming
                qi = WQ().triple("v:s", "v:p", node_id).limit(100).to_dict()
                ri = client.query(qi)
                for bi in ri.get('bindings', []):
                    s = bi.get('v:s'); p = bi.get('v:p')
                    if isinstance(s, str):
                        nodes.setdefault(s, {"id": s, "label": "Subject"})
                        edges.append({"id": f"{s}->{node_id}-{p}", "source": s, "target": node_id, "type": str(p)})
                return {"nodes": list(nodes.values()), "edges": edges}
            data = await anyio.to_thread.run_sync(_terminus_expand)
        else:
            data = await anyio.to_thread.run_sync(_neo4j_expand)
        return {"status": "success", "graph": data}
    except Exception as e:
        logger.error(f"Graph expand error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/schema")
async def graph_schema(backend: Optional[str] = None, auth=Depends(verify_jwt)):
    try:
        settings = SettingsStore().read()
        be = select_backend(settings, prefer=backend)
        def _neo4j_schema():
            driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD") or ""))
            try:
                with driver.session() as sess:
                    labels = [r["label"] for r in sess.run("CALL db.labels() YIELD label RETURN label").data()]
                    rels = [r["relationshipType"] for r in sess.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").data()]
                return {"labels": labels, "relationships": rels}
            finally:
                driver.close()
        def _nebula_schema():
            from nebula3.gclient.net import ConnectionPool
            from nebula3.Config import Config
            nb = settings.get("nebulagraph", {})
            pool = ConnectionPool(); pool.init([(nb.get("host","127.0.0.1"), int(nb.get("port",9669)))], Config())
            sess = pool.get_session(nb.get("user","root"), nb.get("password",""))
            try:
                space = nb.get("space", "");
                if space: sess.execute(f"USE {space}")
                tags = sess.execute("SHOW TAGS"); edges = sess.execute("SHOW EDGES")
                tl = [tags.row_values(i)[0].cast_to_string() for i in range(tags.rows_size())] if tags.is_succeeded() else []
                el = [edges.row_values(i)[0].cast_to_string() for i in range(edges.rows_size())] if edges.is_succeeded() else []
                return {"tags": tl, "edges": el}
            finally:
                sess.release()
        def _terminus_schema():
            try:
                from terminusdb_client import WOQLQuery as WQ
                res = be.client.get_schema()
                return {"classes": list(res.get('@context', {}).keys())}
            except Exception:
                return {"message": "Schema not available"}
        if backend in ("nebula","nebulagraph"):
            data = await anyio.to_thread.run_sync(_nebula_schema)
        elif backend in ("terminus","terminusdb"):
            data = await anyio.to_thread.run_sync(_terminus_schema)
        else:
            data = await anyio.to_thread.run_sync(_neo4j_schema)
        return {"status": "success", "schema": data}
    except Exception as e:
        logger.error(f"Graph schema error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/settings")
async def get_settings(auth=Depends(verify_jwt)):
    try:
        store = SettingsStore()
        return {"status": "success", "settings": store.read()}
    except Exception as e:
        logger.error(f"Settings read error: {e}")
        raise HTTPException(status_code=500, detail=f"Settings read failed: {str(e)}")


@app.put("/admin/settings")
async def put_settings(payload: SettingsUpdate, auth=Depends(verify_jwt)):
    try:
        store = SettingsStore()
        merged = store.write(payload.data)
        logger.info("settings_updated")
        return {"status": "success", "settings": merged, "requires_restart": True}
    except Exception as e:
        logger.error(f"Settings write error: {e}")
        raise HTTPException(status_code=500, detail=f"Settings write failed: {str(e)}")


@app.post("/admin/services/status")
@limiter.limit("60/minute")
async def services_status(units: Dict[str, List[str]] = {"units": []}, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        store = SettingsStore().read()
        allowed = set(store.get("admin", {}).get("allowed_units", []))
        req = units.get("units", []) or list(allowed)
        out = {}
        for u in req:
            if u not in allowed:
                out[u] = {"error": "not allowed"}
                continue
            try:
                r = subprocess.run(["systemctl", "is-active", f"{u}.service"], capture_output=True, text=True, timeout=5)
                out[u] = {"active": r.stdout.strip()}
            except Exception as e:
                out[u] = {"error": str(e)}
        logger.info("services_status", units=req)
        return {"status": "success", "services": out}
    except Exception as e:
        logger.error(f"Services status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/services/action")
@limiter.limit("20/minute")
async def services_action(req: ServiceActionRequest, auth=Depends(verify_jwt)):
    require_admin(auth)
    try:
        store = SettingsStore().read()
        allowed = set(store.get("admin", {}).get("allowed_units", []))
        if req.unit not in allowed:
            raise HTTPException(status_code=403, detail="Unit not allowed")
        if req.action not in {"status", "start", "stop", "restart"}:
            raise HTTPException(status_code=400, detail="Unsupported action")
        cmd = ["systemctl", req.action, f"{req.unit}.service"] if req.action != "status" else ["systemctl", "is-active", f"{req.unit}.service"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        logger.info("services_action", unit=req.unit, action=req.action, code=r.returncode)
        try:
            metric_admin_actions.labels(unit=req.unit, action=req.action).inc()
        except Exception:
            pass
        return {"status": "success", "code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest, auth=Depends(verify_jwt)):
    """Simple RAG chat: retrieves top_k chunks from pgvector and feeds to an LLM (OpenAI/LocalAI)."""
    try:
        # Retrieve context
        vector_store = PGVectorStore.from_params(
            database_url=DATABASE_URL,
            schema_name="public",
            table_name=req.collection,
        )
        index = VectorStoreIndex.from_vector_store(vector_store)
        qe = index.as_query_engine(similarity_top_k=req.top_k)
        last_user = next((m.content for m in reversed(req.messages) if m.role == 'user'), '')
        res = qe.query(last_user or (req.messages[-1].content if req.messages else ''))
        contexts = []
        try:
            for ns in getattr(res, "source_nodes", [])[: req.top_k]:
                contexts.append(ns.node.get_content())
        except Exception:
            pass

        # Compose prompt
        system = (
            "You are the MCP platform assistant. Answer succinctly using the provided context. "
            "Cite facts from context when possible."
        )
        content = "\n\n".join(["Context:"] + contexts + ["\n\nUser:\n" + (last_user or '')])

        # LLM call
        client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"))
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                *[{"role": m.role, "content": m.content} for m in req.messages],
                {"role": "user", "content": content},
            ],
            temperature=0.2,
        )
        answer = completion.choices[0].message.content
        return {"status": "success", "answer": answer, "contexts": contexts}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/admin/settings")
async def get_settings(auth=Depends(verify_jwt)):
    try:
        store = SettingsStore()
        return {"status": "success", "settings": store.read()}
    except Exception as e:
        logger.error(f"Settings read error: {e}")
        raise HTTPException(status_code=500, detail=f"Settings read failed: {str(e)}")


@app.put("/admin/settings")
async def put_settings(payload: SettingsUpdate, auth=Depends(verify_jwt)):
    try:
        store = SettingsStore()
        merged = store.write(payload.data)
        return {"status": "success", "settings": merged, "requires_restart": True}
    except Exception as e:
        logger.error(f"Settings write error: {e}")
        raise HTTPException(status_code=500, detail=f"Settings write failed: {str(e)}")

# Background task functions
def simulate_crawler_work():
    """Simulate crawler work for demo purposes"""
    import time
    global crawler_status

    try:
        # Simulate crawling progress
        for i in range(10):
            time.sleep(1)
            crawler_status["progress"] = (i + 1) * 10

            # Add some fake repositories to actual database
            if i < 5:
                fake_repo = {
                    "name": f"fake-repo-{i+1}",
                    "owner": "testuser",
                    "url": f"https://github.com/testuser/fake-repo-{i+1}",
                    "language": "Python",
                    "stars": 100 + i * 10,
                    "description": f"A fake repository #{i+1} for testing"
                }
                try:
                    db.add_repository(fake_repo)
                except Exception as e:
                    logger.warning(f"Failed to add fake repo {i+1}: {e}")

        crawler_status.update({
            "status": "completed",
            "progress": 100,
            "repositories_found": 5
        })

    except Exception as e:
        logger.error(f"Crawler simulation error: {e}")
        crawler_status["status"] = "error"

def simulate_embeddings_generation(request: EmbeddingsRequest):
    """Simulate embeddings generation for demo purposes"""
    import time
    global embeddings_status

    try:
        time.sleep(3)  # Simulate processing time

        embeddings_status.update({
            "status": "completed",
            "generated": request.batch_size,
            "content_type": request.content_type
        })

    except Exception as e:
        logger.error(f"Embeddings simulation error: {e}")
        embeddings_status["status"] = "error"

if __name__ == "__main__":
    # Get port from environment or default to 3000
    port = int(os.getenv("MCP_SERVER_PORT", "3000"))
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")

    logger.info(f"Starting MCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
# Rate limiter (in-memory)
limiter = Limiter(key_func=get_remote_address, default_limits=["600/hour"])
app.state.limiter = limiter
from slowapi import _rate_limit_exceeded_handler

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    try:
        logger.warn("rate_limited", path=str(request.url), remote=get_remote_address(request), detail=str(exc.detail))
    except Exception:
        pass
    return await _rate_limit_exceeded_handler(request, exc)
# Metrics
registry = CollectorRegistry()
metric_graph_tests = Counter('graph_tests_total', 'Graph backend test calls', ['backend', 'ok'], registry=registry)
metric_migration_runs = Counter('migration_runs_total', 'Migration v2 runs', ['dry_run', 'ok'], registry=registry)
metric_admin_actions = Counter('admin_actions_total', 'Admin service actions', ['unit', 'action'], registry=registry)

# Simple in-process audit ring buffer
_audit_buffer = deque(maxlen=1000)
_audit_seq = 0
def audit(event: str, **data):
    try:
        global _audit_seq
        _audit_seq += 1
        rec = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'seq': _audit_seq,
            'request_id': request_id_ctx.get(),
            'user_id': user_ctx.get(),
            'role': role_ctx.get(),
            'event': event,
            'data': data,
        }
        _audit_buffer.append(rec)
        logger.info(event, **data)
    except Exception:
        try:
            logger.info(event, **data)
        except Exception:
            pass
