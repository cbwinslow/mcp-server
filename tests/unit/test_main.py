import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from mcp_ingest.main import app, crawler_status, simulate_crawler_work, simulate_embeddings_generation
from mcp_ingest.db import MCPDatabase

class TestMainEndpoints:
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "MCP Server is running"
        assert data["version"] == "1.0.0"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_get_component_status(self, client):
        """Test component status endpoint."""
        # Test valid component
        response = client.get("/status/crawler")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["progress"] == 0

        # Test invalid component
        response = client.get("/status/invalid")
        assert response.status_code == 404

    def test_get_all_status(self, client):
        """Test all status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "crawler" in data
        assert data["crawler"]["status"] == "idle"
        assert "database" in data
        assert data["overall"] == "healthy"

    @pytest.mark.parametrize("table, expected_count", [
        ("repositories", 0),
        ("stats", {}),  # Will return stats dict
    ])
    def test_execute_query(self, client, table, expected_count):
        """Test database query endpoint."""
        if table == "stats":
            response = client.post("/db/query", json={"table": "stats"})
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], dict)
        else:
            response = client.post("/db/query", json={"table": table})
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == expected_count
            assert "results" in data

        # Test invalid table
        response = client.post("/db/query", json={"table": "invalid"})
        assert response.status_code == 200  # Returns error status but 200
        data = response.json()
        assert data["status"] == "error"

    def test_control_crawler_status(self, client):
        """Test crawler control - status action."""
        response = client.post("/crawler/control", json={"action": "status"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    def test_control_crawler_start(self, client, mock_crawler_simulation):
        """Test crawler start (mock simulation)."""
        response = client.post("/crawler/control", json={"action": "start", "target": "test-target"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "job_id" in data

        # Verify global status updated
        assert crawler_status["status"] == "running"
        assert crawler_status["target"] == "test-target"

    def test_control_crawler_already_running(self, client):
        """Test start when already running."""
        crawler_status["status"] = "running"
        response = client.post("/crawler/control", json={"action": "start"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Crawler already running"

    def test_control_crawler_stop(self, client):
        """Test crawler stop."""
        crawler_status["status"] = "running"
        response = client.post("/crawler/control", json={"action": "stop"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify updated
        assert crawler_status["status"] == "stopped"

    def test_control_crawler_invalid_action(self, client):
        """Test invalid action."""
        response = client.post("/crawler/control", json={"action": "invalid"})
        assert response.status_code == 400

    def test_generate_embeddings(self, client, mock_embeddings_simulation):
        """Test embeddings generation start."""
        response = client.post("/embeddings/generate", json={"content_type": "code", "batch_size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "job_id" in data

        # Verify global status
        assert embeddings_status["status"] == "running"
        assert embeddings_status["content_type"] == "code"
        assert embeddings_status["batch_size"] == 10

    def test_add_repository(self, client, in_memory_db):
        """Test add repository endpoint."""
        repo_data = {
            "name": "api-repo",
            "owner": "apiuser",
            "url": "https://github.com/apiuser/api-repo",
            "description": "API test repo",
            "language": "Python",
            "stars": 100,
            "metadata": {"test": True}
        }
        
        response = client.post("/repositories", json=repo_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        repo_id = data["repo_id"]
        assert isinstance(repo_id, int)

        # Verify in DB
        repos = in_memory_db.get_repositories()
        assert len(repos) == 1
        assert repos[0]["name"] == "api-repo"

    def test_list_repositories(self, client, in_memory_db):
        """Test list repositories endpoint."""
        # Add repos via DB
        in_memory_db.add_repository({"name": "list1", "owner": "user", "url": "url1"})
        in_memory_db.add_repository({"name": "list2", "owner": "user", "url": "url2"})
        
        response = client.get("/repositories?limit=1&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert data["total"] == 2
        assert len(data["repositories"]) == 1

    def test_error_handling_add_repo(self, client):
        """Test error in add repository."""
        invalid_data = {"name": "invalid", "owner": "user"}  # Missing url
        response = client.post("/repositories", json=invalid_data)
        # Assuming DB add handles missing fields, but test expects 500 if constraint violated
        # For now, since url is NOT NULL, should fail
        assert response.status_code == 500  # Or adjust based on actual

# Minimal tests for empty modules
def test_crawler_import():
    """Test crawler module can be imported (stub)."""
    from mcp_ingest import crawler
    assert crawler is not None  # Empty but importable

def test_extractor_import():
    """Test extractor module can be imported (stub)."""
    from mcp_ingest import extractor
    assert extractor is not None

def test_embeddings_import():
    """Test embeddings module can be imported (stub)."""
    from mcp_ingest import embeddings
    assert embeddings is not None

def test_tasks_import():
    """Test tasks module can be imported (stub)."""
    from mcp_ingest import tasks
    assert tasks is not None