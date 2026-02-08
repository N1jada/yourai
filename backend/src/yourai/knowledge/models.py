"""SQLAlchemy 2.0 models for WP3 knowledge tables.

Models match the canonical schema in docs/architecture/DATABASE_SCHEMA.sql.
All tables are tenant-scoped with TenantScopedMixin.

Uses dialect-agnostic types (JSON, DateTime, Uuid) for SQLite test compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import uuid_utils
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,  # noqa: F401 — used in __table_args__
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yourai.core.database import Base, TenantScopedMixin
from yourai.core.enums import (
    DocumentProcessingState,
    KnowledgeBaseCategory,
    KnowledgeBaseSourceType,
)


class KnowledgeBase(TenantScopedMixin, Base):
    """Tenant-scoped knowledge base container."""

    __tablename__ = "knowledge_bases"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[KnowledgeBaseCategory] = mapped_column(
        Enum(
            KnowledgeBaseCategory,
            name="knowledge_base_category",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    source_type: Mapped[KnowledgeBaseSourceType] = mapped_column(
        Enum(
            KnowledgeBaseSourceType,
            name="knowledge_base_source_type",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    documents: Mapped[list[Document]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class Document(TenantScopedMixin, Base):
    """Tenant-scoped document within a knowledge base."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    knowledge_base_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    document_uri: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_state: Mapped[DocumentProcessingState] = mapped_column(
        Enum(
            DocumentProcessingState,
            name="document_processing_state",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=DocumentProcessingState.UPLOADED,
    )
    text_extraction_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunking_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSON, nullable=False, default=dict
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dead_letter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    annotations: Mapped[list[DocumentAnnotation]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(TenantScopedMixin, Base):
    """A chunk of text from a document, with optional contextual prefix and embedding metadata."""

    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True
    )
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_range_start: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    byte_range_end: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    byte_range_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    contextual_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    document: Mapped[Document] = relationship(back_populates="chunks")


class DocumentAnnotation(TenantScopedMixin, Base):
    """An annotation on a document (expert commentary, etc.)."""

    __tablename__ = "document_annotations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    document_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotation_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    contributor: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    document: Mapped[Document] = relationship(back_populates="annotations")


# ---------------------------------------------------------------------------
# Lex Ingestion
# ---------------------------------------------------------------------------


class IngestionMode(StrEnum):
    """Mode of Lex ingestion run."""

    DAILY = "daily"
    FULL = "full"
    AMENDMENTS_LED = "amendments_led"
    TARGETED = "targeted"


class IngestionJobStatus(StrEnum):
    """Status of a Lex ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LexIngestionJob(TenantScopedMixin, Base):
    """Tracks a Lex ingestion run triggered from the admin UI."""

    __tablename__ = "lex_ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=IngestionJobStatus.PENDING,
    )
    triggered_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    parameters: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    result: Mapped[dict | None] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)


# ---------------------------------------------------------------------------
# Lex Legislation Index
# ---------------------------------------------------------------------------


class LexLegislationStatus(StrEnum):
    """Status of a legislation item in the local index."""

    INDEXED = "indexed"
    REMOVING = "removing"
    REMOVED = "removed"
    FAILED = "failed"


class LexLegislationIndex(TenantScopedMixin, Base):
    """Tracks which legislation items are indexed in the self-hosted Qdrant."""

    __tablename__ = "lex_legislation_index"
    __table_args__ = (
        UniqueConstraint("tenant_id", "legislation_id", name="uq_lex_legislation_index_tenant_leg"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    legislation_id: Mapped[str] = mapped_column(Text, nullable=False)
    legislation_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=LexLegislationStatus.INDEXED,
    )
    section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingestion_job_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("lex_ingestion_jobs.id", ondelete="SET NULL"), nullable=True
    )
    qdrant_point_ids: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
