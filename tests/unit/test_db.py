import pytest
import json
from datetime import datetime
from mcp_ingest.db import MCPDatabase

class TestMCPDatabase:
    def test_init_database(self, in_memory_db):
        """Test database initialization creates tables correctly."""
        # Verify tables exist by counting rows or schema
        with in_memory_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['repositories', 'crawler_jobs', 'embeddings', 'system_status']
            assert all(table in tables for table in expected_tables)
        
        # Check system_status has default entries
        status = in_memory_db.get_system_status()
        assert len(status) == 4
        assert set(status.keys()) == {'crawler', 'extractor', 'embeddings', 'database'}

    def test_add_repository(self, in_memory_db):
        """Test adding a repository."""
        repo_data = {
            "name": "test-repo",
            "owner": "testuser",
            "url": "https://github.com/testuser/test-repo",
            "description": "Test repo",
            "language": "Python",
            "stars": 42,
            "forks": 10,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00",
            "metadata": {"key": "value"}
        }
        
        repo_id = in_memory_db.add_repository(repo_data)
        assert isinstance(repo_id, int)
        assert repo_id > 0
        
        # Verify added
        repos = in_memory_db.get_repositories()
        assert len(repos) == 1
        repo = repos[0]
        assert repo['name'] == "test-repo"
        assert repo['owner'] == "testuser"
        assert repo['url'] == "https://github.com/testuser/test-repo"
        assert repo['stars'] == 42
        assert repo['metadata'] == {"key": "value"}
        assert repo['processed'] == 0  # Default false as int in SQLite

    def test_get_repositories_with_filters(self, in_memory_db):
        """Test getting repositories with filters."""
        # Add two repos
        repo1 = in_memory_db.add_repository({
            "name": "python-repo", "owner": "testuser", "url": "https://github.com/testuser/python-repo",
            "language": "Python", "stars": 100, "metadata": {"type": "code"}
        })
        repo2 = in_memory_db.add_repository({
            "name": "js-repo", "owner": "testuser", "url": "https://github.com/testuser/js-repo",
            "language": "JavaScript", "stars": 50, "metadata": {"type": "code"}
        })
        
        # Filter by language
        repos = in_memory_db.get_repositories(filters={"language": "Python"})
        assert len(repos) == 1
        assert repos[0]['name'] == "python-repo"
        
        # Filter by min_stars
        repos = in_memory_db.get_repositories(filters={"min_stars": 75})
        assert len(repos) == 1
        assert repos[0]['name'] == "python-repo"
        
        # Limit and offset
        repos = in_memory_db.get_repositories(limit=1, offset=0)
        assert len(repos) == 1
        assert repos[0]['name'] == "js-repo"  # Ordered by added_at DESC, so js-repo first

    def test_update_repository_status(self, in_memory_db):
        """Test updating repository status fields."""
        repo_id = in_memory_db.add_repository({
            "name": "status-repo", "owner": "testuser", "url": "https://github.com/testuser/status-repo"
        })
        
        # Update processed
        success = in_memory_db.update_repository_status(repo_id, "processed", True)
        assert success
        
        # Verify
        repo = in_memory_db.get_repositories(filters={"name": "status-repo"})[0]
        assert repo['processed'] == 1  # True as int
        
        # Update timestamp
        now = datetime.now()
        success = in_memory_db.update_repository_status(repo_id, "crawled_at", now)
        assert success
        
        repo = in_memory_db.get_repositories(filters={"name": "status-repo"})[0]
        assert repo['crawled_at'] == now.isoformat()

    def test_add_and_update_crawler_job(self, in_memory_db):
        """Test crawler job operations."""
        job_id = "test-job-1"
        config = {"depth": 2, "rate_limit": 10}
        
        db_job_id = in_memory_db.add_crawler_job(job_id, "github-org", config)
        assert isinstance(db_job_id, int)
        
        # Verify added
        with in_memory_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawler_jobs WHERE job_id = ?", (job_id,))
            job = cursor.fetchone()
            assert job['target'] == "github-org"
            assert json.loads(job['config']) == config
            assert job['status'] == "pending"
        
        # Update to completed
        repos_found = 5
        success = in_memory_db.update_crawler_job(job_id, "completed", repositories_found=repos_found)
        assert success
        
        # Verify update
        jobs = in_memory_db.get_repositories()  # Wait, wrong; but for test, direct query
        with in_memory_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, repositories_found, completed_at FROM crawler_jobs WHERE job_id = ?", (job_id,))
            updated_job = cursor.fetchone()
            assert updated_job['status'] == "completed"
            assert updated_job['repositories_found'] == 5
            assert updated_job['completed_at'] is not None

    def test_add_embedding(self, in_memory_db):
        """Test adding an embedding."""
        repo_id = in_memory_db.add_repository({
            "name": "embed-repo", "owner": "testuser", "url": "https://github.com/testuser/embed-repo"
        })
        
        embedding_vector = [0.1, 0.2, 0.3]  # Sample vector
        embed_id = in_memory_db.add_embedding(
            repo_id, "code", "file.py", embedding_vector, "sentence-transformers/all-MiniLM-L6-v2"
        )
        assert isinstance(embed_id, int)
        
        # Verify
        with in_memory_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM embeddings WHERE id = ?", (embed_id,))
            embed = cursor.fetchone()
            assert embed['repository_id'] == repo_id
            assert embed['content_type'] == "code"
            assert json.loads(embed['embedding_vector']) == embedding_vector

    def test_update_and_get_system_status(self, in_memory_db):
        """Test system status operations."""
        details = {"progress": 50, "error": None}
        success = in_memory_db.update_system_status("crawler", "running", details)
        assert success
        
        # Get specific
        status = in_memory_db.get_system_status("crawler")
        assert status['status'] == "running"
        assert status['details'] == details
        assert 'last_updated' in status
        
        # Get all
        all_status = in_memory_db.get_system_status()
        assert "crawler" in all_status
        assert all_status['crawler']['status'] == "running"

    def test_get_stats(self, in_memory_db):
        """Test database statistics."""
        # Initial empty stats
        stats = in_memory_db.get_stats()
        assert stats['repositories']['total'] == 0
        assert stats['embeddings']['total'] == 0
        assert stats['crawler_jobs']['total'] == 0
        
        # Add data
        in_memory_db.add_repository({"name": "stat-repo1", "owner": "user", "url": "url1"})
        in_memory_db.add_repository({"name": "stat-repo2", "owner": "user", "url": "url2", "processed": True})
        in_memory_db.add_embedding(1, "code", "file1", [0.1], "model")
        
        in_memory_db.add_crawler_job("stat-job", "target", {})
        
        stats = in_memory_db.get_stats()
        assert stats['repositories']['total'] == 2
        assert stats['repositories']['processed'] == 1
        assert stats['embeddings']['total'] == 1
        assert stats['crawler_jobs']['total'] == 1
        assert stats['crawler_jobs']['completed'] == 0

    def test_db_path_default(self):
        """Test default database path."""
        db = MCPDatabase()
        default_path = Path(__file__).parent.parent.parent / "mcp_database.db"  # Adjust based on structure
        assert db.db_path == default_path
        # Note: Actual path verification depends on run location, but init succeeds

    def test_json_metadata_parsing(self, in_memory_db):
        """Test metadata JSON parsing in get_repositories."""
        repo_data = {"name": "json-repo", "owner": "user", "url": "url", "metadata": {"nested": {"key": "value"}}}
        in_memory_db.add_repository(repo_data)
        
        repos = in_memory_db.get_repositories()
        assert repos[0]['metadata'] == {"nested": {"key": "value"}}  # Parsed correctly

    def test_invalid_metadata(self, in_memory_db):
        """Test handling invalid JSON metadata."""
        # Add with invalid JSON (but since add uses dumps, test parsing fail)
        repo_id = in_memory_db.add_repository({"name": "invalid-repo", "owner": "user", "url": "url", "metadata": "invalid json"})
        # Note: add_repository json.dumps dict, so to test, direct insert or modify
        # For unit, assume dumps succeeds, parsing has try/except to {}
        with in_memory_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE repositories SET metadata = 'invalid' WHERE id = ?", (repo_id,))
            conn.commit()
        
        repos = in_memory_db.get_repositories()
        assert repos[0]['metadata'] == {}  # Fallback to {}

    @pytest.mark.parametrize("status_field, value, expected_type", [
        ("processed", True, 1),
        ("stars", 100, 100),
        ("crawled_at", datetime.now(), str)  # ISO string
    ])
    def test_update_status_types(self, in_memory_db, status_field, value, expected_type):
        """Test various status field updates."""
        repo_id = in_memory_db.add_repository({"name": "type-repo", "owner": "user", "url": "url"})
        if isinstance(value, datetime):
            value_str = value.isoformat()
        else:
            value_str = value
        
        success = in_memory_db.update_repository_status(repo_id, status_field, value)
        assert success
        
        repo = in_memory_db.get_repositories(filters={"name": "type-repo"})[0]
        updated_value = repo[status_field]
        if expected_type == str:
            assert isinstance(updated_value, str)
        else:
            assert updated_value == value_str