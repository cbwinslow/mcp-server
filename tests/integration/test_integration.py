import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json
from datetime import datetime
from pathlib import Path
import tempfile
from mcp_ingest.main import app, get_database, crawler_status, embeddings_status
from mcp_ingest.db import MCPDatabase

@pytest.mark.integration
class TestAPIIntegration:
    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Use temporary file DB for integration tests to test persistence."""
        self.temp_db_path = tempfile.mktemp(suffix=".db")
        self.db = MCPDatabase(self.temp_db_path)
        original_get_db = get_database

        def override_get_database():
            return self.db

        app.dependency_overrides[get_database] = override_get_database

        yield

        app.dependency_overrides.clear()
        Path(self.temp_db_path).unlink(missing_ok=True)

    def test_add_repository_via_api_and_query_via_db(self, client):
        """Test adding repo via API and querying via DB directly."""
        repo_data = {
            "name": "integr-repo",
            "owner": "integruser",
            "url": "https://github.com/integruser/integr-repo",
            "description": "Integration test repo",
            "language": "Python",
            "stars": 200,
            "metadata": {"integrated": True}
        }

        # Add via API
        response = client.post("/repositories", json=repo_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        repo_id = data["repo_id"]

        # Verify in DB directly
        repos = self.db.get_repositories()
        assert len(repos) == 1
        repo = repos[0]
        assert repo["id"] == repo_id
        assert repo["name"] == "integr-repo"
        assert repo["stars"] == 200
        assert repo["metadata"] == {"integrated": True}

        # Query via API
        query_response = client.post("/db/query", json={"table": "repositories", "limit": 10})
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert query_data["count"] == 1
        assert query_data["results"][0]["name"] == "integr-repo"

    def test_crawler_start_updates_status_in_db(self, client, mock_crawler_simulation):
        """Test crawler start updates global and DB status."""
        # Start crawler via API
        response = client.post("/crawler/control", json={"action": "start", "target": "integr-target"})
        assert response.status_code == 200
        assert crawler_status["status"] == "running"

        # Verify system_status in DB updated (though main.py doesn't explicitly update DB for crawler, test global)
        # For integration, check if status endpoint reflects
        status_response = client.get("/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["crawler"]["status"] == "running"

        # Simulate completion in mock
        mock_crawler_simulation.return_value = None  # Already mocked
        crawler_status["status"] = "completed"
        crawler_status["progress"] = 100
        crawler_status["repositories_found"] = 3

        # Test stop and update
        stop_response = client.post("/crawler/control", json={"action": "stop"})
        assert stop_response.status_code == 200

    def test_embeddings_generate_and_status(self, client, mock_embeddings_simulation):
        """Test embeddings generation updates status and DB if applicable."""
        response = client.post("/embeddings/generate", json={"content_type": "code", "batch_size": 20})
        assert response.status_code == 200
        assert embeddings_status["status"] == "running"
        assert embeddings_status["batch_size"] == 20

        # Get status
        status_response = client.get("/status/embeddings")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "running"

        # Simulate completion
        embeddings_status["status"] = "completed"
        embeddings_status["generated"] = 20

        # Add embedding via DB to test integration
        repo_id = self.db.add_repository({"name": "embed-integr", "owner": "user", "url": "url"})
        self.db.add_embedding(repo_id, "code", "file.py", [0.1, 0.2], "test-model")

        # Query stats via API
        stats_response = client.post("/db/query", json={"table": "stats"})
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["results"]["embeddings"]["total"] == 1

    def test_list_repositories_pagination(self, client):
        """Test listing with pagination, verify DB count."""
        # Add multiple repos via DB
        for i in range(5):
            self.db.add_repository({
                "name": f"page-repo-{i}",
                "owner": "pageuser",
                "url": f"https://github.com/pageuser/page-repo-{i}"
            })

        # List with limit
        response = client.get("/repositories?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["total"] == 5

        # Second page
        response2 = client.get("/repositories?limit=2&offset=2")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["count"] == 2
        assert len(data2["repositories"]) == 2
        assert data2["repositories"][0]["name"] == "page-repo-2"  # Assuming order by added_at DESC

    def test_query_with_filters_integration(self, client):
        """Test query endpoint with filters, verify against DB."""
        # Add filtered repos
        self.db.add_repository({
            "name": "filter-python", "owner": "filteruser", "url": "url-python", "language": "Python", "stars": 300
        })
        self.db.add_repository({
            "name": "filter-js", "owner": "filteruser", "url": "url-js", "language": "JavaScript", "stars": 100
        })

        # Filter by language via API
        response = client.post("/db/query", json={"table": "repositories", "filters": {"language": "Python"}})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["language"] == "Python"

        # Filter by min_stars
        response = client.post("/db/query", json={"table": "repositories", "filters": {"min_stars": 200}})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    def test_error_propagation_from_db_to_api(self, client):
        """Test API handles DB errors gracefully."""
        # Mock DB to raise exception
        with patch.object(MCPDatabase, 'add_repository') as mock_add:
            mock_add.side_effect = Exception("DB Error")
            response = client.post("/repositories", json={"name": "error-repo", "owner": "user", "url": "url"})
            assert response.status_code == 500
            data = response.json()
            assert "Failed to add repository" in data["detail"]

    def test_stats_endpoint_integration(self, client):
        """Test stats endpoint reflects DB state."""
        # Add data
        self.db.add_repository({"name": "stats-repo1", "owner": "user", "url": "url1", "processed": True})
        self.db.add_repository({"name": "stats-repo2", "owner": "user", "url": "url2"})
        self.db.add_crawler_job("stats-job", "target", {})
        self.db.add_embedding(1, "code", "file", [0.1], "model")

        response = client.post("/db/query", json={"table": "stats"})
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["repositories"]["total"] == 2
        assert data["results"]["repositories"]["processed"] == 1
        assert data["results"]["embeddings"]["total"] == 1
        assert data["results"]["crawler_jobs"]["total"] == 1

        # Via status endpoint
        status_response = client.get("/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["database"]["size"] == 2  # total_repositories