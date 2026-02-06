"""Tests for KnowledgeBaseService: CRUD, document counts, cascade delete."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import uuid_utils
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import (
    DocumentProcessingState,
    KnowledgeBaseCategory,
    KnowledgeBaseSourceType,
)
from yourai.core.exceptions import NotFoundError
from yourai.core.models import Tenant
from yourai.knowledge.knowledge_base import KnowledgeBaseService
from yourai.knowledge.models import Document, KnowledgeBase
from yourai.knowledge.schemas import CreateKnowledgeBase, UpdateKnowledgeBase


class TestKnowledgeBaseService:
    """Tests for KnowledgeBaseService CRUD operations."""

    @patch("yourai.knowledge.knowledge_base.VectorStore")
    async def test_create_knowledge_base(
        self,
        mock_vector_store_cls,
        test_session: AsyncSession,
        sample_tenant: Tenant,
    ):
        mock_store = AsyncMock()
        mock_vector_store_cls.return_value = mock_store

        service = KnowledgeBaseService(test_session)
        data = CreateKnowledgeBase(
            name="Test KB",
            category=KnowledgeBaseCategory.LEGISLATION,
            source_type=KnowledgeBaseSourceType.UPLOADED,
        )
        result = await service.create_knowledge_base(sample_tenant.id, data)

        assert result.name == "Test KB"
        assert result.category == KnowledgeBaseCategory.LEGISLATION
        assert str(result.tenant_id) == str(sample_tenant.id)
        mock_store.ensure_collection.assert_called_once_with(sample_tenant.id)

    async def test_list_knowledge_bases(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        service = KnowledgeBaseService(test_session)
        results = await service.list_knowledge_bases(sample_tenant.id)
        assert len(results) >= 1
        assert any(str(r.id) == str(sample_knowledge_base.id) for r in results)

    async def test_get_knowledge_base(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        service = KnowledgeBaseService(test_session)
        result = await service.get_knowledge_base(sample_knowledge_base.id, sample_tenant.id)
        assert str(result.id) == str(sample_knowledge_base.id)
        assert result.document_count == 0

    async def test_get_knowledge_base_not_found(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
    ):
        service = KnowledgeBaseService(test_session)
        with pytest.raises(NotFoundError):
            await service.get_knowledge_base(uuid_utils.uuid7(), sample_tenant.id)

    async def test_update_knowledge_base(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        service = KnowledgeBaseService(test_session)
        data = UpdateKnowledgeBase(name="Updated Name")
        result = await service.update_knowledge_base(
            sample_knowledge_base.id, sample_tenant.id, data
        )
        assert result.name == "Updated Name"

    async def test_document_count_computed(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test that document_count and ready_document_count are computed correctly."""
        # Add documents with different states
        doc1 = Document(
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="doc1.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/doc1.pdf",
            processing_state=DocumentProcessingState.READY,
        )
        doc2 = Document(
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="doc2.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/doc2.pdf",
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add_all([doc1, doc2])
        await test_session.flush()

        service = KnowledgeBaseService(test_session)
        result = await service.get_knowledge_base(sample_knowledge_base.id, sample_tenant.id)
        assert result.document_count == 2
        assert result.ready_document_count == 1

    @patch("yourai.knowledge.knowledge_base.VectorStore")
    async def test_delete_knowledge_base(
        self,
        mock_vector_store_cls,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        mock_store = AsyncMock()
        mock_vector_store_cls.return_value = mock_store

        service = KnowledgeBaseService(test_session)
        await service.delete_knowledge_base(sample_knowledge_base.id, sample_tenant.id)
        await test_session.flush()

        with pytest.raises(NotFoundError):
            await service.get_knowledge_base(sample_knowledge_base.id, sample_tenant.id)

    async def test_delete_not_found(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
    ):
        service = KnowledgeBaseService(test_session)
        with pytest.raises(NotFoundError):
            await service.delete_knowledge_base(uuid_utils.uuid7(), sample_tenant.id)

    async def test_tenant_isolation(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Verify that a different tenant cannot see the knowledge base."""
        other_tenant = Tenant(
            id=uuid_utils.uuid7(),
            name="Other Tenant",
            slug="other-tenant",
            branding_config={},
            ai_config={},
            is_active=True,
        )
        test_session.add(other_tenant)
        await test_session.flush()

        service = KnowledgeBaseService(test_session)
        results = await service.list_knowledge_bases(other_tenant.id)
        assert len(results) == 0
