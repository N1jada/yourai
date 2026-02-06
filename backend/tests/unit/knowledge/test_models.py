"""Tests for knowledge models: creation, relationships, versioning chain."""

from __future__ import annotations

import uuid_utils
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import (
    DocumentProcessingState,
    KnowledgeBaseCategory,
    KnowledgeBaseSourceType,
)
from yourai.core.models import Tenant
from yourai.knowledge.models import Document, DocumentAnnotation, DocumentChunk, KnowledgeBase


class TestKnowledgeBaseModel:
    """Tests for the KnowledgeBase model."""

    async def test_create_knowledge_base(self, test_session: AsyncSession, sample_tenant: Tenant):
        kb = KnowledgeBase(
            tenant_id=sample_tenant.id,
            name="Test KB",
            category=KnowledgeBaseCategory.LEGISLATION,
            source_type=KnowledgeBaseSourceType.UPLOADED,
        )
        test_session.add(kb)
        await test_session.flush()

        result = await test_session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb.id))
        loaded = result.scalar_one()
        assert loaded.name == "Test KB"
        assert str(loaded.tenant_id) == str(sample_tenant.id)


class TestDocumentModel:
    """Tests for the Document model."""

    async def test_create_document(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        doc = Document(
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="test.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/test.pdf",
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc)
        await test_session.flush()

        result = await test_session.execute(select(Document).where(Document.id == doc.id))
        loaded = result.scalar_one()
        assert loaded.name == "test.pdf"
        assert loaded.processing_state == DocumentProcessingState.UPLOADED
        assert loaded.version_number == 1
        assert loaded.dead_letter is False
        assert loaded.retry_count == 0

    async def test_document_versioning_chain(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test that documents can form a version chain."""
        doc_v1 = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="policy.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/v1/policy.pdf",
            version_number=1,
            processing_state=DocumentProcessingState.READY,
        )
        test_session.add(doc_v1)
        await test_session.flush()

        doc_v2 = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="policy.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/v2/policy.pdf",
            version_number=2,
            previous_version_id=doc_v1.id,
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc_v2)
        await test_session.flush()

        result = await test_session.execute(select(Document).where(Document.id == doc_v2.id))
        loaded = result.scalar_one()
        assert loaded.version_number == 2
        assert str(loaded.previous_version_id) == str(doc_v1.id)

    async def test_document_relationships(
        self,
        test_session: AsyncSession,
        sample_document: Document,
        sample_tenant: Tenant,
    ):
        """Test that document has relationship to knowledge base."""
        result = await test_session.execute(
            select(Document).where(Document.id == sample_document.id)
        )
        doc = result.scalar_one()
        assert str(doc.knowledge_base_id) == str(sample_document.knowledge_base_id)


class TestDocumentChunkModel:
    """Tests for the DocumentChunk model."""

    async def test_create_chunk(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_document: Document,
    ):
        chunk = DocumentChunk(
            tenant_id=sample_tenant.id,
            document_id=sample_document.id,
            chunk_index=0,
            content="This is chunk content.",
        )
        test_session.add(chunk)
        await test_session.flush()

        result = await test_session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk.id)
        )
        loaded = result.scalar_one()
        assert loaded.content == "This is chunk content."
        assert loaded.chunk_index == 0
        assert loaded.contextual_prefix is None


class TestDocumentAnnotationModel:
    """Tests for the DocumentAnnotation model."""

    async def test_create_annotation(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_document: Document,
    ):
        annotation = DocumentAnnotation(
            tenant_id=sample_tenant.id,
            document_id=sample_document.id,
            annotation_type="expert_commentary",
            content="This section is particularly relevant to...",
            contributor="Dr Smith",
        )
        test_session.add(annotation)
        await test_session.flush()

        result = await test_session.execute(
            select(DocumentAnnotation).where(DocumentAnnotation.id == annotation.id)
        )
        loaded = result.scalar_one()
        assert loaded.annotation_type == "expert_commentary"
        assert loaded.contributor == "Dr Smith"
