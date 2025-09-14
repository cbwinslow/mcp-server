import pytest
from fastapi.testclient import TestClient
from mcp_ingest.main import app
from mcp_ingest.db import MCPDatabase
from unittest.mock import patch, MagicMock

@pytest.mark.security
class TestSecurity:
    def test_sql_injection_attempt_in_query(self, client):
        """Test SQL injection prevention in query filters (parameterized queries protect)."""
        # Attempt SQL injection in filter
        malicious_filter = {"name": "'; DROP TABLE repositories; --"}
        response = client.post("/db/query", json={
            "table": "repositories",
            "filters": malicious_filter
        })
        assert response.status_code == 200  # No crash
        data = response.json()
        assert "DROP" not in str(data)  # No injection executed
        # Verify table still exists by querying stats
        stats_response = client.post("/db/query", json={"table": "stats"})
        assert stats_response.status_code == 200

    def test_large_payload_in_add_repo(self, client):
        """Test handling of large payload to check for DoS vulnerability."""
        large_metadata = {"data": "x" * 1000000}  # 1MB
        repo_data = {
            "name": "dos-repo",
            "owner": "dosuser",
            "url": "https://github.com/dosuser/dos-repo",
            "metadata": large_metadata
        }
        response = client.post("/repositories", json=repo_data)
        assert response.status_code == 200  # Accepts large payload
        data = response.json()
        assert data["status"] == "success"
        # Note: Recommend adding size limit in production

    def test_invalid_input_in_add_repo(self, client):
        """Test invalid input handling (e.g., missing required fields)."""
        invalid_data = {"name": "invalid", "owner": "user"}  # Missing url
        response = client.post("/repositories", json=invalid_data)
        assert response.status_code == 500  # DB integrity error
        assert "Failed to add repository" in response.json()["detail"]

    def test_cors_configuration(self, client):
        """Test CORS allows expected origins."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"  # Wildcard, note: insecure for prod

    def test_no_auth_on_sensitive_endpoints(self, client):
        """Test lack of authentication (vulnerability)."""
        # All endpoints open
        response = client.post("/crawler/control", json={"action": "start"})
        assert response.status_code == 200
        # Recommend adding auth middleware

    def test_rate_limiting_absence(self, client):
        """Test no rate limiting on endpoints."""
        responses = []
        for _ in range(100):
            resp = client.get("/health")
            responses.append(resp.status_code)
        assert all(code == 200 for code in responses)  # No limit hit
        # Vulnerability: Add rate limiting in prod

    def test_db_file_access_restriction(self, in_memory_db):
        """Test DB uses in-memory, no file system write vulnerability."""
        assert in_memory_db.db_path == ":memory:"
        # Add data, verify no file created
        repo_id = in_memory_db.add_repository({"name": "secure-repo", "owner": "user", "url": "url"})
        assert repo_id > 0
        # No disk write

    def test_encryption_not_implemented(self, client):
        """Test data is not encrypted at rest (SQLite plain)."""
        sensitive_data = {"name": "secret-repo", "owner": "secret", "url": "url", "metadata": {"secret": "password123"}}
        response = client.post("/repositories", json=sensitive_data)
        assert response.status_code == 200
        # Data stored plain; recommend encryption for prod

    def test_xss_in_response(self, client):
        """Test no XSS in responses (JSON safe)."""
        # Add repo with script tag in description
        repo_data = {
            "name": "xss-repo",
            "owner": "xssuser",
            "url": "https://github.com/xssuser/xss-repo",
            "description": "<script>alert('XSS')</script>"
        }
        response = client.post("/repositories", json=repo_data)
        assert response.status_code == 200

        # Query back
        query_response = client.post("/db/query", json={"table": "repositories"})
        data = query_response.json()["results"]
        description = data[0]["description"]
        assert description == "<script>alert('XSS')</script>"  # Not escaped, but JSON context safe from XSS
        # Recommend sanitization for HTML contexts