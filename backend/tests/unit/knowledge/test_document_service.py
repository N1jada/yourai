"""Tests for DocumentService: upload, versioning, filters, retry."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
import uuid_utils
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import DocumentProcessingState
from yourai.core.exceptions import NotFoundError, ValidationError
from yourai.core.models import Tenant
from yourai.knowledge.documents import DocumentService
from yourai.knowledge.models import Document, KnowledgeBase
from yourai.knowledge.schemas import DocumentFilters


class TestDocumentService:
    """Tests for DocumentService operations."""

    @patch("yourai.knowledge.documents.process_document_task")
    @patch("yourai.knowledge.documents.LocalFileStorage")
    @patch("yourai.knowledge.documents.validate_upload")
    async def test_upload_document(
        self,
        mock_validate,
        mock_storage_cls,
        mock_task,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        mock_validate.return_value = "application/pdf"
        mock_storage = AsyncMock()
        mock_storage.file_hash.return_value = "abc123hash"
        mock_storage.save.return_value = "/uploads/test/doc.pdf"
        mock_storage_cls.return_value = mock_storage

        file = UploadFile(
            filename="test_doc.pdf",
            file=BytesIO(b"%PDF-1.4 content"),
        )

        service = DocumentService(test_session)
        result = await service.upload(file, sample_knowledge_base.id, sample_tenant.id)

        assert result.name == "test_doc.pdf"
        assert result.processing_state == DocumentProcessingState.UPLOADED
        assert result.version_number == 1
        mock_task.delay.assert_called_once()

    @patch("yourai.knowledge.documents.process_document_task")
    @patch("yourai.knowledge.documents.LocalFileStorage")
    @patch("yourai.knowledge.documents.validate_upload")
    async def test_upload_versioning(
        self,
        mock_validate,
        mock_storage_cls,
        mock_task,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
        sample_document: Document,
    ):
        """Test that uploading a file with the same name creates a new version."""
        mock_validate.return_value = "application/pdf"
        mock_storage = AsyncMock()
        mock_storage.file_hash.return_value = "newhash"
        mock_storage.save.return_value = "/uploads/test/v2.pdf"
        mock_storage_cls.return_value = mock_storage

        file = UploadFile(
            filename=sample_document.name,  # Same name as existing document
            file=BytesIO(b"%PDF-1.4 new content"),
        )

        service = DocumentService(test_session)
        result = await service.upload(file, sample_knowledge_base.id, sample_tenant.id)

        assert result.version_number == 2
        assert str(result.previous_version_id) == str(sample_document.id)

    async def test_get_document(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_document: Document,
    ):
        service = DocumentService(test_session)
        result = await service.get_document(sample_document.id, sample_tenant.id)
        assert str(result.id) == str(sample_document.id)
        assert result.chunk_count == 0

    async def test_get_document_not_found(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
    ):
        service = DocumentService(test_session)
        with pytest.raises(NotFoundError):
            await service.get_document(uuid_utils.uuid7(), sample_tenant.id)

    async def test_list_documents(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
        sample_document: Document,
    ):
        service = DocumentService(test_session)
        filters = DocumentFilters()
        result = await service.list_documents(sample_knowledge_base.id, sample_tenant.id, filters)
        assert result.total >= 1
        assert len(result.items) >= 1

    async def test_list_documents_with_state_filter(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
        sample_document: Document,
    ):
        service = DocumentService(test_session)
        filters = DocumentFilters(processing_state=DocumentProcessingState.READY)
        result = await service.list_documents(sample_knowledge_base.id, sample_tenant.id, filters)
        # sample_document is UPLOADED, not READY
        assert result.total == 0

    @patch("yourai.knowledge.documents.delete_document_vectors_task")
    @patch("yourai.knowledge.documents.LocalFileStorage")
    async def test_delete_document(
        self,
        mock_storage_cls,
        mock_task,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_document: Document,
    ):
        mock_storage = AsyncMock()
        mock_storage_cls.return_value = mock_storage

        service = DocumentService(test_session)
        await service.delete_document(sample_document.id, sample_tenant.id)
        await test_session.flush()

        with pytest.raises(NotFoundError):
            await service.get_document(sample_document.id, sample_tenant.id)

    async def test_get_versions(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test version chain retrieval."""
        doc_v1 = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="versioned.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/v1.pdf",
            version_number=1,
            processing_state=DocumentProcessingState.READY,
        )
        test_session.add(doc_v1)
        await test_session.flush()

        doc_v2 = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="versioned.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/v2.pdf",
            version_number=2,
            previous_version_id=doc_v1.id,
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc_v2)
        await test_session.flush()

        service = DocumentService(test_session)
        versions = await service.get_versions(doc_v2.id, sample_tenant.id)
        assert len(versions) == 2
        assert versions[0].version_number == 2  # Newest first
        assert versions[1].version_number == 1

    @patch("yourai.knowledge.documents.process_document_task")
    async def test_retry_failed(
        self,
        mock_task,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        doc = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="failed.pdf",
            document_uri=f"/uploads/{sample_tenant.id}/failed.pdf",
            processing_state=DocumentProcessingState.FAILED,
            retry_count=2,
            dead_letter=True,
            last_error_message="extraction failed",
        )
        test_session.add(doc)
        await test_session.flush()

        service = DocumentService(test_session)
        result = await service.retry_failed(doc.id, sample_tenant.id)

        assert result.processing_state == DocumentProcessingState.UPLOADED
        assert result.retry_count == 0
        assert result.dead_letter is False
        assert result.last_error_message is None
        mock_task.delay.assert_called_once()

    async def test_retry_non_failed_raises(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_document: Document,
    ):
        """Cannot retry a document that isn't in FAILED state."""
        service = DocumentService(test_session)
        with pytest.raises(ValidationError, match="Only failed"):
            await service.retry_failed(sample_document.id, sample_tenant.id)
