#!/usr/bin/env python3
"""
Async Postgres database layer using SQLAlchemy 2.0
Never uses SQLite. Reads DATABASE_URL from env.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    select,
    func,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    embedded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class CrawlerJob(Base):
    __tablename__ = "crawler_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    target: Mapped[Optional[str]] = mapped_column(String)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    repositories_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"))
    content_type: Mapped[Optional[str]] = mapped_column(String)
    content_path: Mapped[Optional[str]] = mapped_column(String)
    # Store vectors in pgvector via LlamaIndex pipeline; here we keep metadata
    embedding_vector: Mapped[Optional[str]] = mapped_column(Text)
    model_name: Mapped[Optional[str]] = mapped_column(String)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"))
    path: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id"))
    index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SystemStatus(Base):
    __tablename__ = "system_status"

    component: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="idle")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class AsyncDatabase:
    """Async Postgres database wrapper."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required and SQLite is not supported")

        if self.database_url.startswith("sqlite"):
            raise RuntimeError("SQLite is not supported. Please set a Postgres DATABASE_URL.")

        self.engine: AsyncEngine = create_async_engine(self.database_url, echo=False, future=True)
        self.SessionLocal = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def init_models(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_repository(self, repo_data: Dict[str, Any]) -> str:
        async with self.SessionLocal() as session:
            repo = Repository(
                name=repo_data.get("name"),
                owner=repo_data.get("owner"),
                url=repo_data.get("url"),
                description=repo_data.get("description"),
                language=repo_data.get("language"),
                stars=repo_data.get("stars", 0),
                forks=repo_data.get("forks", 0),
                created_at=repo_data.get("created_at"),
                updated_at=repo_data.get("updated_at"),
                metadata=repo_data.get("metadata", {}),
            )
            session.add(repo)
            await session.commit()
            await session.refresh(repo)
            return str(repo.id)

    async def get_repositories(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        async with self.SessionLocal() as session:
            stmt = select(Repository)
            if filters:
                if (name := filters.get("name")):
                    stmt = stmt.where(Repository.name == name)
                if (owner := filters.get("owner")):
                    stmt = stmt.where(Repository.owner == owner)
                if (language := filters.get("language")):
                    stmt = stmt.where(Repository.language == language)
                if (processed := filters.get("processed")) is not None:
                    stmt = stmt.where(Repository.processed == bool(processed))
                if (min_stars := filters.get("min_stars")) is not None:
                    stmt = stmt.where(Repository.stars >= int(min_stars))
                if (max_stars := filters.get("max_stars")) is not None:
                    stmt = stmt.where(Repository.stars <= int(max_stars))

            stmt = stmt.order_by(Repository.added_at.desc()).limit(limit).offset(offset)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._repo_to_dict(r) for r in rows]

    async def get_repository_count(self) -> int:
        async with self.SessionLocal() as session:
            result = await session.execute(select(func.count()).select_from(Repository))
            return int(result.scalar_one())

    async def get_stats(self) -> Dict[str, Any]:
        async with self.SessionLocal() as session:
            total_repos = int((await session.execute(select(func.count()).select_from(Repository))).scalar_one())
            processed_repos = int(
                (
                    await session.execute(
                        select(func.count()).select_from(Repository).where(Repository.processed.is_(True))
                    )
                ).scalar_one()
            )
            total_embeddings = int((await session.execute(select(func.count()).select_from(Embedding))).scalar_one())
            total_jobs = int((await session.execute(select(func.count()).select_from(CrawlerJob))).scalar_one())
            completed_jobs = int(
                (
                    await session.execute(
                        select(func.count()).select_from(CrawlerJob).where(CrawlerJob.status == "completed")
                    )
                ).scalar_one()
            )

            return {
                "repositories": {
                    "total": total_repos,
                    "processed": processed_repos,
                    "unprocessed": total_repos - processed_repos,
                },
                "embeddings": {"total": total_embeddings},
                "crawler_jobs": {
                    "total": total_jobs,
                    "completed": completed_jobs,
                    "pending": total_jobs - completed_jobs,
                },
            }

    @staticmethod
    def _repo_to_dict(r: Repository) -> Dict[str, Any]:
        return {
            "id": str(r.id),
            "name": r.name,
            "owner": r.owner,
            "url": r.url,
            "description": r.description,
            "language": r.language,
            "stars": r.stars,
            "forks": r.forks,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "added_at": r.added_at.isoformat() if r.added_at else None,
            "processed": r.processed,
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "extracted_at": r.extracted_at.isoformat() if r.extracted_at else None,
            "embedded_at": r.embedded_at.isoformat() if r.embedded_at else None,
            "metadata": r.metadata or {},
        }
