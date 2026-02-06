"""Integration tests for the document processing pipeline.

Uses mocked external services (Qdrant, Anthropic, Voyage) but tests the full
pipeline flow including DB state transitions, chunking, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import uuid_utils
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import (
    DocumentProcessingState,
)
from yourai.core.models import Tenant
from yourai.knowledge.models import Document, DocumentChunk, KnowledgeBase
from yourai.knowledge.pipeline import process_document


def _make_pdf_bytes() -> bytes:
    """Create a simple PDF with real content for extraction testing."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Housing Act 2004", fontsize=18)
    page.insert_text((72, 110), "Section 1: Purpose", fontsize=14)
    page.insert_text((72, 140), "This Act makes provision about housing conditions.", fontsize=11)
    page.insert_text(
        (72, 160), "It covers licensing of houses in multiple occupation.", fontsize=11
    )
    page.insert_text((72, 200), "Section 2: Definitions", fontsize=14)
    page.insert_text((72, 230), "In this Act, the following definitions apply.", fontsize=11)
    page.insert_text((72, 250), "A dwelling means a building used as a residence.", fontsize=11)
    pdf_bytes = doc.write()
    doc.close()
    return bytes(pdf_bytes)


class TestDocumentPipeline:
    """Integration tests for the full document processing pipeline."""

    @patch("yourai.knowledge.pipeline.VectorStore")
    @patch("yourai.knowledge.pipeline.create_embedder")
    @patch("yourai.knowledge.pipeline.contextualise_chunks")
    async def test_full_pipeline_success(
        self,
        mock_contextualise,
        mock_create_embedder,
        mock_vector_store_cls,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test the full pipeline from upload to ready state."""
        pdf_bytes = _make_pdf_bytes()

        # Create document
        doc = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="housing_act.pdf",
            document_uri="",
            mime_type="application/pdf",
            byte_size=len(pdf_bytes),
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc)
        await test_session.flush()

        # Write PDF to a temp file and set the URI
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            doc.document_uri = f.name
        test_session.add(doc)
        await test_session.flush()

        # Mock external services
        mock_contextualise.return_value = [
            "Context for chunk"
        ] * 20  # Enough for any number of chunks

        mock_embedder = AsyncMock()
        mock_embedder.model_name = "voyage-3-large"
        mock_embedder.dimensions = 1024
        mock_embedder.embed_documents.return_value = [[0.1] * 1024 for _ in range(20)]
        mock_create_embedder.return_value = mock_embedder

        mock_store = AsyncMock()
        mock_vector_store_cls.return_value = mock_store

        # Run pipeline
        await process_document(test_session, doc.id, sample_tenant.id)
        await test_session.flush()

        # Verify final state
        result = await test_session.execute(select(Document).where(Document.id == doc.id))
        updated_doc = result.scalar_one()
        assert updated_doc.processing_state == DocumentProcessingState.READY
        assert updated_doc.extracted_text is not None
        assert "Housing Act" in updated_doc.extracted_text
        assert updated_doc.text_extraction_strategy == "pdf_pymupdf"

        # Verify chunks were created
        chunk_result = await test_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        chunks = chunk_result.scalars().all()
        assert len(chunks) > 0

        # Verify Qdrant was called
        mock_store.ensure_collection.assert_called_once()
        mock_store.upsert_chunks.assert_called_once()

        # Clean up temp file
        Path(doc.document_uri).unlink(missing_ok=True)

    @patch("yourai.knowledge.pipeline.LocalFileStorage")
    async def test_pipeline_failure_increments_retry(
        self,
        mock_storage_cls,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test that pipeline failure increments retry_count and sets error."""
        doc = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="bad_file.pdf",
            document_uri="/nonexistent/path.pdf",
            mime_type="application/pdf",
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc)
        await test_session.flush()

        # Mock storage to raise an error
        mock_storage = AsyncMock()
        mock_storage.read.side_effect = FileNotFoundError("File not found")
        mock_storage_cls.return_value = mock_storage

        await process_document(test_session, doc.id, sample_tenant.id)
        await test_session.flush()

        result = await test_session.execute(select(Document).where(Document.id == doc.id))
        updated_doc = result.scalar_one()
        assert updated_doc.processing_state == DocumentProcessingState.FAILED
        assert updated_doc.retry_count == 1
        assert updated_doc.last_error_message is not None

    @patch("yourai.knowledge.pipeline.LocalFileStorage")
    async def test_pipeline_dead_letter_after_max_retries(
        self,
        mock_storage_cls,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test that document is dead-lettered after 3 failures."""
        doc = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="repeatedly_bad.pdf",
            document_uri="/nonexistent/path.pdf",
            mime_type="application/pdf",
            processing_state=DocumentProcessingState.UPLOADED,
            retry_count=2,  # Already failed twice
        )
        test_session.add(doc)
        await test_session.flush()

        mock_storage = AsyncMock()
        mock_storage.read.side_effect = FileNotFoundError("File not found")
        mock_storage_cls.return_value = mock_storage

        await process_document(test_session, doc.id, sample_tenant.id)
        await test_session.flush()

        result = await test_session.execute(select(Document).where(Document.id == doc.id))
        updated_doc = result.scalar_one()
        assert updated_doc.dead_letter is True
        assert updated_doc.retry_count == 3

    async def test_pipeline_nonexistent_document(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
    ):
        """Test that pipeline gracefully handles non-existent document."""
        fake_id = uuid_utils.uuid7()
        # Should not raise — just logs and returns
        await process_document(test_session, fake_id, sample_tenant.id)

    async def test_tenant_isolation_in_pipeline(
        self,
        test_session: AsyncSession,
        sample_tenant: Tenant,
        sample_knowledge_base: KnowledgeBase,
    ):
        """Test that pipeline only processes documents for the correct tenant."""
        other_tenant = Tenant(
            id=uuid_utils.uuid7(),
            name="Other Tenant",
            slug="other-tenant-pipeline",
            branding_config={},
            ai_config={},
            is_active=True,
        )
        test_session.add(other_tenant)
        await test_session.flush()

        doc = Document(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            knowledge_base_id=sample_knowledge_base.id,
            name="tenant_test.pdf",
            document_uri="/uploads/tenant_test.pdf",
            processing_state=DocumentProcessingState.UPLOADED,
        )
        test_session.add(doc)
        await test_session.flush()

        # Process with wrong tenant — should not find the document
        await process_document(test_session, doc.id, other_tenant.id)

        # Document should remain unchanged
        result = await test_session.execute(select(Document).where(Document.id == doc.id))
        unchanged_doc = result.scalar_one()
        assert unchanged_doc.processing_state == DocumentProcessingState.UPLOADED
