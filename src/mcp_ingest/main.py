#!/usr/bin/env python3
"""
MCP Server - Model Context Protocol Server for GitHub Repository Ingestion
Provides REST API endpoints for CrewAI agents to interact with MCP components
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .db import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server for GitHub Repository Ingestion",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = get_database()

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

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MCP Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status/{component}")
async def get_component_status(component: str):
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
async def get_all_status():
    """Get status of all MCP server components"""
    try:
        # Get actual database status
        db_stats = db.get_stats()

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
async def execute_query(request: QueryRequest):
    """
    Execute database queries

    Args:
        request: Query parameters
    """
    try:
        if request.table == "repositories":
            # Get repositories from database
            results = db.get_repositories(
                filters=request.filters,
                limit=request.limit,
                offset=0
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
            stats = db.get_stats()
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
async def control_crawler(request: CrawlerRequest, background_tasks: BackgroundTasks):
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
async def generate_embeddings(request: EmbeddingsRequest, background_tasks: BackgroundTasks):
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
async def add_repository(repo_data: Dict[str, Any]):
    """
    Add a repository to the database

    Args:
        repo_data: Repository information
    """
    try:
        # Add repository using database module
        repo_id = db.add_repository(repo_data)

        return {
            "status": "success",
            "message": "Repository added successfully",
            "repo_id": repo_id
        }

    except Exception as e:
        logger.error(f"Add repository error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add repository: {str(e)}")

@app.get("/repositories")
async def list_repositories(limit: int = 50, offset: int = 0):
    """
    List repositories in the database

    Args:
        limit: Maximum number of results
        offset: Offset for pagination
    """
    try:
        # Get repositories from database
        results = db.get_repositories(limit=limit, offset=offset)
        total_count = db.get_repository_count()

        return {
            "status": "success",
            "count": len(results),
            "total": total_count,
            "repositories": results
        }

    except Exception as e:
        logger.error(f"List repositories error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")

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
