import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from mcp_ingest.main import app, get_database
from mcp_ingest.db import MCPDatabase
from requests.exceptions import ConnectionError

@pytest.mark.edge_cases
class TestEdgeCases:
    def test_db_connection_failure(self, client):
        """Test when DB connection fails."""
        with patch('mcp_ingest.db.sqlite3.connect', side_effect=ConnectionError("DB Connection Failed")):
            response = client.get("/status")
            assert response.status_code == 200  # Status returns degraded
            data = response.json()
            assert data["database"]["status"] == "error"

    def test_invalid_action_in_crawler_control(self, client):
        """Test invalid action in crawler control."""
        response = client.post("/crawler/control", json={"action": "invalid_action"})
        assert response.status_code == 400
        data = response.json()
        assert "Unknown action" in data["detail"]

    def test_empty_filters_in_query(self, client):
        """Test query with empty filters."""
        response = client.post("/db/query", json={"table": "repositories", "filters": {}})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_negative_limit_in_query(self, client):
        """Test invalid (negative) limit in query."""
        response = client.post("/db/query", json={"table": "repositories", "limit": -1})
        assert response.status_code == 200  # Limit clamped to 0 or default
        data = response.json()
        assert data["limit"] == 100  # Default limit applied

    def test_network_failure_in_background_task(self, client):
        """Test background task failure (e.g., network error in simulation)."""
        with patch('mcp_ingest.main.simulate_crawler_work', side_effect=ConnectionError("Network Failure")):
            response = client.post("/crawler/control", json={"action": "start"})
            assert response.status_code == 200  # Starts successfully
            # Status should reflect error after task
            # Since background, test status shows running, but in full, log error

    def test_zero_batch_size_in_embeddings(self, client):
        """Test zero batch size in embeddings generate."""
        response = client.post("/embeddings/generate", json={"batch_size": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Batch size default or clamped

    def test_duplicate_url_in_add_repo(self, client, in_memory_db):
        """Test adding repo with duplicate URL (unique constraint)."""
        repo_data = {
            "name": "dup1",
            "owner": "dupuser",
            "url": "https://github.com/dupuser/dup-repo",
            "language": "Python"
        }
        in_memory_db.add_repository(repo_data)
        response = client.post("/repositories", json=repo_data)
        assert response.status_code == 500  # Integrity error
        assert "unique" in str(response.json()["detail"]).lower()

    def test_nonexistent_table_in_query(self, client):
        """Test query on nonexistent table."""
        response = client.post("/db/query", json={"table": "nonexistent"})
        assert response.status_code == 200  # Returns error status
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"]

    def test_high_offset_in_list_repositories(self, client, in_memory_db):
        """Test high offset beyond data."""
        for i in range(5):
            in_memory_db.add_repository({"name": f"offset-{i}", "owner": "user", "url": f"url-{i}"})
        response = client.get("/repositories?limit=1&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0  # No more data

    def test_empty_request_body_in_post_endpoints(self, client):
        """Test empty body in POST endpoints."""
        response = client.post("/repositories", json={})
        assert response.status_code == 500  # Missing fields

        response2 = client.post("/crawler/control", json={})
        assert response2.status_code == 200  # Action default "status"

    def test_max_limit_in_query(self, client, in_memory_db):
        """Test large limit, but capped."""
        for i in range(10):
            in_memory_db.add_repository({"name": f"max-{i}", "owner": "user", "url": f"url-{i}"})
        response = client.post("/db/query", json={"table": "repositories", "limit": 1000})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 10  # All data, not limited by 1000

    def test_timestamp_parsing_in_status_update(self, in_memory_db):
        """Test invalid timestamp in update."""
        repo_id = in_memory_db.add_repository({"name": "time-repo", "owner": "user", "url": "url"})
        success = in_memory_db.update_repository_status(repo_id, "crawled_at", "invalid-time")
        assert success
        repo = in_memory_db.get_repositories()[0]
        assert repo["crawled_at"] == "invalid-time"  # No parsing error, stored as is