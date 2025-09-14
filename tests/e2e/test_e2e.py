import pytest
from fastapi.testclient import TestClient
from time import sleep
from unittest.mock import patch
from mcp_ingest.main import app, get_database, simulate_crawler_work, simulate_embeddings_generation
from mcp_ingest.db import MCPDatabase

@pytest.mark.e2e
class TestEndToEndPipeline:
    def test_full_ingestion_pipeline(self, client):
        """Test complete ingestion pipeline from crawler to query."""
        db = get_database()

        # Clear any existing data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM repositories")
            cursor.execute("DELETE FROM embeddings")
            cursor.execute("DELETE FROM crawler_jobs")
            conn.commit()

        # Step 1: Start crawler - this will trigger background simulation adding fake repos
        crawler_response = client.post("/crawler/control", json={
            "action": "start",
            "target": "e2e-org",
            "config": {"max_repos": 3}
        })
        assert crawler_response.status_code == 200
        assert crawler_response.json()["status"] == "success"

        # Wait for background task to complete (simulation takes ~10s, but for test, wait 12s)
        sleep(12)

        # Verify crawler completed and repos added
        status_response = client.get("/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["crawler"]["status"] == "completed"
        assert status_data["crawler"]["progress"] == 100
        assert status_data["crawler"]["repositories_found"] == 5  # From simulation

        # Verify repos in DB via API
        repos_response = client.get("/repositories")
        assert repos_response.status_code == 200
        repos_data = repos_response.json()
        assert repos_data["count"] == 5
        assert repos_data["total"] == 5
        assert len(repos_data["repositories"]) == 5
        assert all("fake-repo" in repo["name"] for repo in repos_data["repositories"])

        # Step 2: Generate embeddings for content
        embeddings_response = client.post("/embeddings/generate", json={
            "content_type": "code",
            "batch_size": 5,
            "source": "repositories"
        })
        assert embeddings_response.status_code == 200
        assert embeddings_response.json()["status"] == "success"

        # Wait for embeddings simulation (~3s)
        sleep(4)

        # Verify embeddings completed
        embeddings_status = client.get("/status/embeddings").json()
        assert embeddings_status["status"] == "completed"
        assert embeddings_status["generated"] == 5

        # Since simulation doesn't add to DB, mock add one embedding for test
        # In full impl, it would; here verify pipeline flow
        repo_id = repos_data["repositories"][0]["id"]
        db.add_embedding(repo_id, "code", "test/file.py", [0.1, 0.2, 0.3], "test-model")

        # Step 3: Query with filters
        query_response = client.post("/db/query", json={
            "table": "repositories",
            "filters": {"owner": "testuser"},
            "limit": 10
        })
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert query_data["count"] == 5  # All fake repos have testuser

        # Stats
        stats_response = client.post("/db/query", json={"table": "stats"})
        assert stats_response.status_code == 200
        stats_data = stats_response.json()["results"]
        assert stats_data["repositories"]["total"] == 5
        assert stats_data["embeddings"]["total"] == 1  # The one we added

        # Overall status healthy
        assert status_data["overall"] == "healthy"

    def test_pipeline_with_stop_and_resume(self, client):
        """Test stopping crawler mid-pipeline and resuming."""
        # Start crawler
        start_response = client.post("/crawler/control", json={"action": "start", "target": "resume-target"})
        assert start_response.status_code == 200

        # Wait partial
        sleep(5)  # Half way, progress ~50

        # Stop
        stop_response = client.post("/crawler/control", json={"action": "stop"})
        assert stop_response.status_code == 200
        status = client.get("/status/crawler").json()
        assert status["status"] == "stopped"
        assert status["progress"] < 100

        # Resume (start again)
        resume_response = client.post("/crawler/control", json={"action": "start", "target": "resume-target"})
        assert resume_response.status_code == 200

        sleep(8)  # Complete

        final_status = client.get("/status/crawler").json()
        assert final_status["status"] == "completed"
        assert final_status["progress"] == 100

        # Check repos added despite stop/resume (simulation restarts)
        repos = client.get("/repositories").json()
        assert len(repos["repositories"]) > 0

    def test_e2e_error_in_pipeline(self, client):
        """Test error handling in full pipeline."""
        with patch('mcp_ingest.main.simulate_crawler_work', side_effect=Exception("E2E Pipeline Failure")):
            # Start crawler - background will fail
            response = client.post("/crawler/control", json={"action": "start"})
            assert response.status_code == 200  # Starts successfully

            sleep(2)

            # Status should show error (in code, simulation sets error, but main.py doesn't catch, assume degraded)
            status = client.get("/status").json()
            assert status["overall"] == "degraded"  # From try/except in get_all_status

            # Subsequent embeddings still work
            embeddings_response = client.post("/embeddings/generate", json={"content_type": "code"})
            assert embeddings_response.status_code == 200

            sleep(4)

            # Query still works (no repos added due to error)
            query = client.post("/db/query", json={"table": "repositories"}).json()
            assert query["count"] == 0  # No repos due to failed simulation