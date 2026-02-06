"""Pydantic v2 request/response schemas for WP3 knowledge endpoints.

All schemas match API_CONTRACTS.md §2.2 and §3.5-3.7.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yourai.core.enums import (
    DocumentProcessingState,
    KnowledgeBaseCategory,
    KnowledgeBaseSourceType,
)

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------


class CreateKnowledgeBase(BaseModel):
    name: str
    category: KnowledgeBaseCategory
    source_type: KnowledgeBaseSourceType


class UpdateKnowledgeBase(BaseModel):
    name: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    category: KnowledgeBaseCategory
    source_type: KnowledgeBaseSourceType
    document_count: int = 0
    ready_document_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    name: str
    document_uri: str
    source_uri: str | None
    mime_type: str | None
    byte_size: int | None
    hash: str | None
    processing_state: DocumentProcessingState
    version_number: int
    previous_version_id: UUID | None
    metadata: dict[str, object]
    chunk_count: int = 0
    retry_count: int
    last_error_message: str | None
    dead_letter: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version_number: int
    processing_state: DocumentProcessingState
    byte_size: int | None
    created_at: datetime | None = None


class DocumentFilters(BaseModel):
    processing_state: DocumentProcessingState | None = None
    dead_letter: bool | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str
    categories: list[KnowledgeBaseCategory] | None = None
    knowledge_base_ids: list[UUID] | None = None
    limit: int = 10
    similarity_threshold: float = 0.4


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    document_uri: str
    knowledge_base_category: KnowledgeBaseCategory
    chunk_index: int
    content: str
    contextual_prefix: str | None
    score: float
    source_uri: str | None
    metadata: dict[str, object]


class VectorResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str


class KeywordResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
