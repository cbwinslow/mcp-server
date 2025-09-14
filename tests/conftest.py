
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
from contextlib import contextmanager

from fastapi.testclient import TestClient
from mcp_ingest.main import app, crawler_status, extractor_status, embeddings_status, simulate_crawler_work, simulate_embeddings_generation
from mcp_ingest.db import MCPDatabase, get_database

@contextmanager
def temp_db():
    """Context manager for temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        yield db_path
    finally:
        Path(db_path).unlink(missing_ok=True)

@pytest.fixture(scope="function")
def db_instance():
    """Fixture for MCPDatabase with temporary file for integration tests."""
    db_path = None
    with temp_db() as tmp_path:
        db_path = tmp_path
        db = MCPDatabase(db_path)
        yield db

@pytest.fixture(scope="function")
def in_memory_db():
    """In-memory MCPDatabase for unit tests."""
    db = MCPDatabase(":memory:")
    yield db

@pytest.fixture
def client(in_memory_db):
    """TestClient with database override."""
    original_get_db = get_database

    def override_get_database():
        return in_memory_db

    app.dependency_overrides[get_database] = override_get_database
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_globals():
    """Mock global status variables to prevent state leakage."""
    original_crawler = crawler_status.copy()
    original_extractor = extractor_status.copy()
    original_embeddings = embeddings_status.copy()

    crawler_status.update({"status": "idle", "last_run": None, "progress": 0})
    extractor_status.update({"status": "idle", "last_run": None, "processed": 0})
    embeddings_status.update({"status": "idle", "last_run": None, "generated": 0})

    yield

    crawler_status.clear()
    crawler_status.update(original_crawler)
    extractor_status.clear()
    extractor_status.update(original_extractor)
    embeddings_status.clear()
    embeddings_status.update(original_embeddings)

@pytest.fixture
def mock_crawler_simulation():
    """Mock simulate_crawler_work to avoid actual execution."""
    with patch('mcp_ingest.main.simulate_crawler_work') as mock:
        mock.return_value = None
        yield mock

@pytest.fixture
def mock_embeddings_simulation():
    """Mock simulate_embeddings_generation to avoid actual execution."""
    with patch('mcp_ingest.main.simulate_embeddings_generation') as mock:
        mock.return_value = None
        yield mock