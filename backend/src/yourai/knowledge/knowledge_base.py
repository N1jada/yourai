"""Knowledge base service: CRUD operations with computed document counts."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import DocumentProcessingState
from yourai.core.exceptions import NotFoundError
from yourai.knowledge.models import Document, KnowledgeBase
from yourai.knowledge.schemas import (
    CreateKnowledgeBase,
    KnowledgeBaseResponse,
    UpdateKnowledgeBase,
)
from yourai.knowledge.vector_store import VectorStore

logger = structlog.get_logger()


class KnowledgeBaseService:
    """Service for knowledge base CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_knowledge_bases(self, tenant_id: UUID) -> list[KnowledgeBaseResponse]:
        """List all knowledge bases for a tenant with computed document counts."""
        # Subquery for document counts
        doc_count_sq = (
            select(
                Document.knowledge_base_id,
                func.count(Document.id).label("document_count"),
                func.count(Document.id)
                .filter(Document.processing_state == DocumentProcessingState.READY)
                .label("ready_document_count"),
            )
            .where(Document.tenant_id == tenant_id)
            .group_by(Document.knowledge_base_id)
            .subquery()
        )

        query = (
            select(
                KnowledgeBase,
                func.coalesce(doc_count_sq.c.document_count, 0).label("document_count"),
                func.coalesce(doc_count_sq.c.ready_document_count, 0).label("ready_document_count"),
            )
            .outerjoin(doc_count_sq, KnowledgeBase.id == doc_count_sq.c.knowledge_base_id)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .order_by(KnowledgeBase.created_at)
        )

        result = await self._session.execute(query)
        rows = result.all()

        responses = []
        for row in rows:
            kb = row[0]
            resp = self._to_response(kb, document_count=row[1], ready_document_count=row[2])
            responses.append(resp)
        return responses

    async def create_knowledge_base(
        self, tenant_id: UUID, data: CreateKnowledgeBase
    ) -> KnowledgeBaseResponse:
        """Create a new knowledge base and ensure Qdrant collection exists."""
        kb = KnowledgeBase(
            tenant_id=tenant_id,
            name=data.name,
            category=data.category,
            source_type=data.source_type,
        )
        self._session.add(kb)
        await self._session.flush()

        # Ensure Qdrant collection exists
        vector_store = VectorStore()
        await vector_store.ensure_collection(tenant_id)

        logger.info(
            "knowledge_base_created",
            tenant_id=str(tenant_id),
            knowledge_base_id=str(kb.id),
        )
        return self._to_response(kb)

    async def get_knowledge_base(
        self, knowledge_base_id: UUID, tenant_id: UUID
    ) -> KnowledgeBaseResponse:
        """Get a knowledge base by ID with computed document counts."""
        doc_count_sq = (
            select(
                Document.knowledge_base_id,
                func.count(Document.id).label("document_count"),
                func.count(Document.id)
                .filter(Document.processing_state == DocumentProcessingState.READY)
                .label("ready_document_count"),
            )
            .where(Document.tenant_id == tenant_id)
            .group_by(Document.knowledge_base_id)
            .subquery()
        )

        query = (
            select(
                KnowledgeBase,
                func.coalesce(doc_count_sq.c.document_count, 0).label("document_count"),
                func.coalesce(doc_count_sq.c.ready_document_count, 0).label("ready_document_count"),
            )
            .outerjoin(doc_count_sq, KnowledgeBase.id == doc_count_sq.c.knowledge_base_id)
            .where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )

        result = await self._session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise NotFoundError("Knowledge base not found.")

        kb = row[0]
        return self._to_response(kb, document_count=row[1], ready_document_count=row[2])

    async def update_knowledge_base(
        self, knowledge_base_id: UUID, tenant_id: UUID, data: UpdateKnowledgeBase
    ) -> KnowledgeBaseResponse:
        """Update a knowledge base name."""
        result = await self._session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise NotFoundError("Knowledge base not found.")

        if data.name is not None:
            kb.name = data.name
        self._session.add(kb)
        await self._session.flush()

        logger.info(
            "knowledge_base_updated",
            tenant_id=str(tenant_id),
            knowledge_base_id=str(kb.id),
        )
        return self._to_response(kb)

    async def delete_knowledge_base(self, knowledge_base_id: UUID, tenant_id: UUID) -> None:
        """Delete a knowledge base, cascade deletes documents, and clean up Qdrant."""
        result = await self._session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise NotFoundError("Knowledge base not found.")

        # Delete all document vectors from Qdrant
        doc_result = await self._session.execute(
            select(Document.id).where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc_ids = [row[0] for row in doc_result.all()]

        vector_store = VectorStore()
        for doc_id in doc_ids:
            await vector_store.delete_by_document(tenant_id, doc_id)

        await self._session.delete(kb)
        await self._session.flush()

        logger.info(
            "knowledge_base_deleted",
            tenant_id=str(tenant_id),
            knowledge_base_id=str(knowledge_base_id),
        )

    async def sync_knowledge_base(self, knowledge_base_id: UUID, tenant_id: UUID) -> None:
        """Trigger async sync for catalog-type knowledge bases."""
        result = await self._session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise NotFoundError("Knowledge base not found.")

        logger.info(
            "knowledge_base_sync_triggered",
            tenant_id=str(tenant_id),
            knowledge_base_id=str(knowledge_base_id),
        )

    @staticmethod
    def _to_response(
        kb: KnowledgeBase,
        document_count: int = 0,
        ready_document_count: int = 0,
    ) -> KnowledgeBaseResponse:
        """Convert a KnowledgeBase model to a KnowledgeBaseResponse.

        Uses str() conversion for UUID fields to handle uuid_utils.UUID vs stdlib UUID.
        """
        return KnowledgeBaseResponse(
            id=UUID(str(kb.id)),
            tenant_id=UUID(str(kb.tenant_id)),
            name=kb.name,
            category=kb.category,
            source_type=kb.source_type,
            document_count=document_count,
            ready_document_count=ready_document_count,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
