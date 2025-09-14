import pytest
from fastapi.testclient import TestClient
from mcp_ingest.main import app
from mcp_ingest.db import MCPDatabase
from pytest_benchmark.fixture import BenchmarkFixture

@pytest.mark.benchmark
class TestPerformance:
    def test_health_check_benchmark(self, client: TestClient, benchmark: BenchmarkFixture):
        """Benchmark health check endpoint response time."""
        def call_health():
            response = client.get("/health")
            assert response.status_code == 200
            return response
        result = benchmark(call_health)
        print(f"Health check mean time: {result.stats.mean:.4f}s")

    def test_status_endpoint_benchmark(self, client: TestClient, benchmark: BenchmarkFixture):
        """Benchmark all status endpoint."""
        def call_status():
            response = client.get("/status")
            assert response.status_code == 200
            return response
        result = benchmark(call_status)
        print(f"Status endpoint mean time: {result.stats.mean:.4f}s")

    def test_add_repository_benchmark(self, client: TestClient, benchmark: BenchmarkFixture, in_memory_db):
        """Benchmark adding a repository (with DB insert)."""
        repo_data = {
            "name": "bench-repo",
            "owner": "benchuser",
            "url": "https://github.com/benchuser/bench-repo",
            "language": "Python",
            "stars": 100,
            "description": "Benchmark repository"
        }
        def call_add():
            response = client.post("/repositories", json=repo_data)
            assert response.status_code == 200
            return response
        result = benchmark(call_add)
        print(f"Add repository mean time: {result.stats.mean:.4f}s")

    def test_query_repositories_benchmark(self, client: TestClient, benchmark: BenchmarkFixture, in_memory_db):
        """Benchmark querying repositories with 100 items."""
        # Pre-populate 100 repos
        for i in range(100):
            in_memory_db.add_repository({
                "name": f"bench-repo-{i}",
                "owner": "benchuser",
                "url": f"https://github.com/benchuser/bench-repo-{i}",
                "language": "Python"
            })
        def call_query():
            response = client.post("/db/query", json={"table": "repositories", "limit": 50})
            assert response.status_code == 200
            data = response.json()
            assert data["count"] > 0
            return data
        result = benchmark(call_query)
        print(f"Query repositories mean time: {result.stats.mean:.4f}s")

    def test_list_repositories_benchmark(self, client: TestClient, benchmark: BenchmarkFixture, in_memory_db):
        """Benchmark list repositories endpoint with data."""
        # Pre-populate
        for i in range(50):
            in_memory_db.add_repository({
                "name": f"list-bench-{i}",
                "owner": "listuser",
                "url": f"https://github.com/listuser/list-bench-{i}"
            })
        def call_list():
            response = client.get("/repositories?limit=25")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 25
            return data
        result = benchmark(call_list)
        print(f"List repositories mean time: {result.stats.mean:.4f}s")

    def test_crawler_control_benchmark(self, client: TestClient, benchmark: BenchmarkFixture, mock_crawler_simulation):
        """Benchmark crawler control start."""
        def call_start():
            response = client.post("/crawler/control", json={"action": "start", "target": "bench-target"})
            assert response.status_code == 200
            return response
        result = benchmark(call_start)
        print(f"Crawler start mean time: {result.stats.mean:.4f}s")