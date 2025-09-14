# MCP Server Test Suite Documentation

## Overview
The test suite for the MCP Server is comprehensive, covering functionality, performance, security, integration, and edge cases. It uses pytest as the framework, with subdirectories for different test types. Tests aim for 100% coverage on core modules (main.py, db.py) and verify stubs for others.

## Setup Instructions
1. Create and activate virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Linux/Mac
   # or .venv\Scripts\activate on Windows
   ```

2. Install dependencies:
   ```
   pip install -e ".[dev]"
   ```

3. Run tests:
   - All tests: `pytest -v`
   - With coverage: `pytest -v --cov=mcp_ingest --cov-report=html --cov-report=term-missing`
   - Unit only: `pytest tests/unit -v -m unit`
   - Integration: `pytest tests/integration -v -m integration`
   - E2E: `pytest tests/e2e -v -m e2e`
   - Performance: `pytest tests/performance -v --benchmark-only`
   - Security: `pytest tests/security -v -m security`
   - Edge cases: `pytest tests/edge_cases -v -m edge_cases`

4. Generate coverage report:
   - HTML report in `htmlcov/` directory.
   - Terminal summary with missing lines.

## Test Categories
- **Unit Tests** (`tests/unit/`): Test individual functions/classes in isolation (e.g., DB CRUD, endpoint logic with mocks). Uses in-memory DB and mocks for globals/background tasks.
- **Integration Tests** (`tests/integration/`): Test API-DB interactions with temporary file DB for persistence. Verifies end-to-end data flow without mocks.
- **End-to-End Tests** (`tests/e2e/`): Simulate full pipeline (crawler start, embeddings, query). Uses sleep for background tasks; assumes simulation completes.
- **Performance Tests** (`tests/performance/`): Benchmark endpoint response times using pytest-benchmark. Pre-populates data for realistic loads; reports mean/std dev times.
- **Security Tests** (`tests/security/`): Check for vulnerabilities like SQL injection (parameterized queries protect), large payloads (no limit, recommend middleware), CORS (wildcard, insecure for prod), no auth (open endpoints).
- **Edge Cases** (`tests/edge_cases/`): Test failures (DB connection error, invalid inputs), boundaries (negative limits, high offset), duplicates (unique constraint errors).

## Test Reports
- **Coverage**: Aim for 90%+ on mcp_ingest. Run `pytest --cov` to see missing lines (focus on main.py, db.py).
- **Performance**: Benchmark reports times (e.g., health check <1ms, query with 100 items <50ms). Thresholds can be added in future.
- **Failures**: If failures occur, check logs for DB constraints, mock mismatches. E2E may fail if simulation time changes; adjust sleep.
- **Security**: Tests highlight vulnerabilities (no auth, no encryption); implement fixes like FastAPI Users for auth, SQLCipher for DB.

## Ongoing Maintenance
- **Add Tests**: For new features (e.g., real crawler), add unit/integration tests first.
- **CI/CD**: .github/workflows/ci.yml runs on push/PR: lint, type check, tests, coverage upload to Codecov. Fail if coverage <90%.
- **Updates**: Update deps in pyproject.toml, run `pre-commit install` for linting. Use `pytest --collect-only` to list tests.
- **Performance**: Run benchmarks regularly; monitor for regressions.
- **Security**: Scan with Bandit/Safety; add OWASP checks. Enable HTTPS in prod.
- **Coverage**: Use `pytest-cov` for reports; aim 100% by covering stubs as implemented.

For questions, see README.md or run `pytest --help`.