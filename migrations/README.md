# Alembic migrations (skeleton)

This project will migrate from SQLite to Postgres (async SQLAlchemy + `asyncpg`).

Steps to initialize once the async ORM models are in place:

```
# Install deps in your venv
pip install alembic sqlalchemy[asyncio] asyncpg

# Initialize Alembic
alembic init migrations

# Configure alembic.ini to use env var
# sqlalchemy.url = %(DATABASE_URL)s

# Create an initial revision (edit models first)
alembic revision -m "init" --autogenerate

# Apply
alembic upgrade head
```

> Tip: Move the current `src/mcp_ingest/db.py` into SQLAlchemy models and sessions; keep FastAPI endpoints unchanged.

