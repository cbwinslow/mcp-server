from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID


class RepositoryModel(BaseModel):
    id: Optional[UUID] = None
    name: str
    owner: str
    url: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_at: Optional[datetime] = None
    processed: bool = False
    crawled_at: Optional[datetime] = None
    extracted_at: Optional[datetime] = None
    embedded_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrawlerJobModel(BaseModel):
    id: Optional[UUID] = None
    job_id: str
    status: str = "pending"
    target: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    repositories_found: int = 0
    error_message: Optional[str] = None


class EmbeddingModel(BaseModel):
    id: Optional[UUID] = None
    repository_id: Optional[UUID] = None
    content_type: Optional[str] = None
    content_path: Optional[str] = None
    embedding_vector: Optional[str] = None
    model_name: Optional[str] = None
    generated_at: Optional[datetime] = None

