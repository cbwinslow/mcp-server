#!/usr/bin/env python3
"""
Custom CrewAI Tools for MCP Server Integration
Provides specialized tools for AI agents to interact with MCP server components
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import subprocess
import shutil
from pathlib import Path

from crewai_tools import BaseTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPServerStatusTool(BaseTool):
    """Tool to check MCP server and component status"""

    name: str = "MCP Server Status Checker"
    description: str = "Check the status of MCP server components including crawler, extractor, embeddings, and database"

    def _run(self, component: str = "all") -> str:
        """
        Check the status of MCP server components

        Args:
            component: Component to check (all, crawler, extractor, embeddings, database)

        Returns:
            Status information as JSON string
        """
        logger.info(f"Checking MCP server status for component: {component}")

        server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        api_key = os.getenv('MCP_API_KEY')

        session = requests.Session()
        if api_key:
            session.headers.update({'Authorization': f'Bearer {api_key}'})

        try:
            if component == "all":
                # Check all components
                response = session.get(f"{server_url}/status", timeout=30)
                response.raise_for_status()
                result = response.json()
                return json.dumps(result, indent=2)
            else:
                # Check specific component
                response = session.get(f"{server_url}/status/{component}", timeout=30)
                response.raise_for_status()
                result = response.json()
                return json.dumps(result, indent=2)
        except requests.exceptions.RequestException as e:
            error_result = {"error": str(e), "status": "failed", "component": component}
            return json.dumps(error_result, indent=2)

class MCPDatabaseQueryTool(BaseTool):
    """Tool to execute queries against MCP database"""

    name: str = "MCP Database Query Tool"
    description: str = "Execute database queries against MCP server repositories and statistics"

    def _run(self, query_type: str = "select", table: str = "repositories",
            filters: str = "{}", limit: int = 100) -> str:
        """
        Execute database queries against MCP server

        Args:
            query_type: Type of query (select, count, etc.)
            table: Database table to query
            filters: Query filters as JSON string
            limit: Maximum number of results

        Returns:
            Query results as JSON string
        """
        logger.info(f"Executing {query_type} query on table: {table}")

        server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        api_key = os.getenv('MCP_API_KEY')

        session = requests.Session()
        if api_key:
            session.headers.update({'Authorization': f'Bearer {api_key}'})

        try:
            # Parse filters from JSON string
            parsed_filters = json.loads(filters) if filters else {}

            payload = {
                "query_type": query_type,
                "table": table,
                "filters": parsed_filters,
                "limit": limit
            }

            response = session.post(f"{server_url}/db/query", json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return json.dumps(result, indent=2)

        except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
            error_result = {"error": str(e), "status": "failed", "table": table}
            return json.dumps(error_result, indent=2)

class MCPGitHubCrawlerTool(BaseTool):
    """Tool to control GitHub repository crawling operations"""

    name: str = "MCP GitHub Crawler Control"
    description: str = "Control GitHub crawler operations including start, stop, status, and configuration"

    def _run(self, action: str = "status", target: str = "all",
            config: str = "{}") -> str:
        """
        Control GitHub crawler operations

        Args:
            action: Action to perform (start, stop, status, config)
            target: Target repositories or "all"
            config: Configuration parameters as JSON string

        Returns:
            Operation result as JSON string
        """
        logger.info(f"GitHub crawler action: {action} on target: {target}")

        server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        api_key = os.getenv('MCP_API_KEY')

        session = requests.Session()
        if api_key:
            session.headers.update({'Authorization': f'Bearer {api_key}'})

        try:
            # Parse config from JSON string
            parsed_config = json.loads(config) if config else {}

            payload = {
                "action": action,
                "target": target,
                "config": parsed_config
            }

            response = session.post(f"{server_url}/crawler/control", json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return json.dumps(result, indent=2)

        except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
            error_result = {"error": str(e), "status": "failed", "action": action}
            return json.dumps(error_result, indent=2)

class MCPEmbeddingsGeneratorTool(BaseTool):
    """Tool to generate embeddings for harvested content"""

    name: str = "MCP Embeddings Generator"
    description: str = "Generate embeddings for harvested content including code, docs, and metadata"

    def _run(self, content_type: str = "code", batch_size: int = 100,
            source: str = "") -> str:
        """
        Generate embeddings for content

        Args:
            content_type: Type of content (code, docs, metadata)
            batch_size: Number of items to process in batch
            source: Specific source to process or empty for all pending

        Returns:
            Embedding generation results as JSON string
        """
        logger.info(f"Generating embeddings for content type: {content_type}")

        server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        api_key = os.getenv('MCP_API_KEY')

        session = requests.Session()
        if api_key:
            session.headers.update({'Authorization': f'Bearer {api_key}'})

        try:
            payload = {
                "content_type": content_type,
                "batch_size": batch_size,
                "source": source or None
            }

            response = session.post(f"{server_url}/embeddings/generate", json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return json.dumps(result, indent=2)

        except requests.exceptions.RequestException as e:
            error_result = {"error": str(e), "status": "failed", "content_type": content_type}
            return json.dumps(error_result, indent=2)

class GitHubRepoSearchTool(BaseTool):
    """Tool for searching GitHub repositories"""

    name: str = "GitHub Repository Search"
    description: str = "Search GitHub repositories by query, language, stars, and other criteria"

    def _run(self, query: str = "", language: str = "", min_stars: str = "0",
            sort: str = "stars", limit: str = "30") -> str:
        """
        Search GitHub repositories

        Args:
            query: Search query string
            language: Programming language filter
            min_stars: Minimum star count as string
            sort: Sort criteria (stars, forks, updated)
            limit: Maximum results as string

        Returns:
            Search results as JSON string
        """
        logger.info(f"Searching GitHub repos with query: {query}")

        token = os.getenv('GITHUB_TOKEN')
        base_url = "https://api.github.com"
        session = requests.Session()
        if token:
            session.headers.update({'Authorization': f'token {token}'})

        try:
            search_query = query
            if language:
                search_query += f" language:{language}"
            min_stars_int = int(min_stars) if min_stars.isdigit() else 0
            if min_stars_int > 0:
                search_query += f" stars:>={min_stars_int}"

            params = {
                "q": search_query,
                "sort": sort,
                "order": "desc",
                "per_page": min(int(limit) if limit.isdigit() else 30, 100)
            }

            response = session.get(f"{base_url}/search/repositories", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            result = {
                "status": "success",
                "total_count": data.get("total_count", 0),
                "repositories": data.get("items", [])
            }
            return json.dumps(result, indent=2)

        except (ValueError, requests.exceptions.RequestException) as e:
            error_result = {"error": str(e), "status": "failed", "query": query}
            return json.dumps(error_result, indent=2)

# Tool registry for easy access
TOOL_REGISTRY = {
    "mcp_server_status": MCPServerStatusTool,
    "mcp_database_query": MCPDatabaseQueryTool,
    "mcp_github_crawler": MCPGitHubCrawlerTool,
    "mcp_embeddings_generator": MCPEmbeddingsGeneratorTool,
    "github_repo_search": GitHubRepoSearchTool,
}

def get_tool(tool_name: str, **kwargs) -> Any:
    """Factory function to get tool instances"""
    tool_class = TOOL_REGISTRY.get(tool_name)
    if tool_class:
        return tool_class(**kwargs)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

if __name__ == "__main__":
    # Example usage
    status_tool = get_tool("mcp_server_status")
    result = status_tool.run()
    print(json.dumps(result, indent=2))