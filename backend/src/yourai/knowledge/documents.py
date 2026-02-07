"""Document service: upload, list, get, delete, versioning, retry."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select

if TYPE_CHECKING:
    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import DocumentProcessingState
from yourai.core.exceptions import NotFoundError, ValidationError
from yourai.core.schemas import Page
from yourai.knowledge.models import Document, DocumentChunk, KnowledgeBase
from yourai.knowledge.schemas import DocumentFilters, DocumentResponse, DocumentVersion
from yourai.knowledge.storage import LocalFileStorage
from yourai.knowledge.tasks import delete_document_vectors_task, process_document_task
from yourai.knowledge.validation import validate_upload

logger = structlog.get_logger()


class DocumentService:
    """Service for document CRUD and pipeline management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upload(
        self,
        file: UploadFile,
        knowledge_base_id: UUID,
        tenant_id: UUID,
    ) -> DocumentResponse:
        """Validate file, store, create DB record, handle versioning, enqueue processing."""
        # Verify knowledge base exists
        result = await self._session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise NotFoundError("Knowledge base not found.")

        # Read and validate file
        data = await file.read()
        filename = file.filename or "unnamed"
        mime_type = validate_upload(data, filename, str(tenant_id))

        # Store file
        storage = LocalFileStorage()
        file_hash = await storage.file_hash(data)

        # Handle versioning: check for existing document with same name
        previous_version_id: UUID | None = None
        version_number = 1
        existing_result = await self._session.execute(
            select(Document)
            .where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.tenant_id == tenant_id,
                Document.name == filename,
            )
            .order_by(Document.version_number.desc())
            .limit(1)
        )
        existing_doc = existing_result.scalar_one_or_none()
        if existing_doc is not None:
            previous_version_id = existing_doc.id
            version_number = existing_doc.version_number + 1

        # Create document record
        document = Document(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            name=filename,
            document_uri="",  # Will be set after save
            mime_type=mime_type,
            byte_size=len(data),
            hash=file_hash,
            processing_state=DocumentProcessingState.UPLOADED,
            version_number=version_number,
            previous_version_id=previous_version_id,
        )
        self._session.add(document)
        await self._session.flush()

        # Save file with document ID in path
        file_path = await storage.save(tenant_id, document.id, filename, data)
        document.document_uri = file_path
        self._session.add(document)
        await self._session.flush()

        logger.info(
            "document_uploaded",
            tenant_id=str(tenant_id),
            document_id=str(document.id),
            filename=filename,
            version=version_number,
        )

        # Enqueue processing pipeline
        process_document_task.delay(str(document.id), str(tenant_id))

        return self._to_response(document, chunk_count=0)

    async def get_document(self, document_id: UUID, tenant_id: UUID) -> DocumentResponse:
        """Get a document by ID with chunk count."""
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError("Document not found.")

        chunk_count = await self._get_chunk_count(document_id, tenant_id)
        return self._to_response(doc, chunk_count=chunk_count)

    async def list_documents(
        self, knowledge_base_id: UUID, tenant_id: UUID, filters: DocumentFilters
    ) -> Page[DocumentResponse]:
        """List documents with pagination and filtering."""
        query = select(Document).where(
            Document.knowledge_base_id == knowledge_base_id,
            Document.tenant_id == tenant_id,
        )

        if filters.processing_state is not None:
            query = query.where(Document.processing_state == filters.processing_state)
        if filters.dead_letter is not None:
            query = query.where(Document.dead_letter == filters.dead_letter)
        if filters.search:
            query = query.where(Document.name.ilike(f"%{filters.search}%"))

        # Count total
        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(filters.page_size)

        result = await self._session.execute(query)
        docs = list(result.scalars().all())

        # Get chunk counts for all documents
        items = []
        for doc in docs:
            chunk_count = await self._get_chunk_count(doc.id, tenant_id)
            items.append(self._to_response(doc, chunk_count=chunk_count))

        return Page(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            has_next=(offset + filters.page_size) < total,
        )

    async def delete_document(self, document_id: UUID, tenant_id: UUID) -> None:
        """Delete document: DB records, file, and Qdrant vectors."""
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError("Document not found.")

        # Delete file
        storage = LocalFileStorage()
        if doc.document_uri:
            with contextlib.suppress(FileNotFoundError):
                await storage.delete(doc.document_uri)

        # Enqueue Qdrant vector deletion
        delete_document_vectors_task.delay(str(document_id), str(tenant_id))

        # Delete from DB (cascade deletes chunks and annotations)
        await self._session.delete(doc)
        await self._session.flush()

        logger.info(
            "document_deleted",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
        )

    async def get_versions(self, document_id: UUID, tenant_id: UUID) -> list[DocumentVersion]:
        """Get version history for a document by following the version chain."""
        # First get the document to verify access
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError("Document not found.")

        # Get all documents with the same name in the same knowledge base
        result = await self._session.execute(
            select(Document)
            .where(
                Document.knowledge_base_id == doc.knowledge_base_id,
                Document.tenant_id == tenant_id,
                Document.name == doc.name,
            )
            .order_by(Document.version_number.desc())
        )
        versions = result.scalars().all()

        return [
            DocumentVersion(
                id=v.id,
                name=v.name,
                version_number=v.version_number,
                processing_state=v.processing_state,
                byte_size=v.byte_size,
                created_at=v.created_at,
            )
            for v in versions
        ]

    async def retry_failed(self, document_id: UUID, tenant_id: UUID) -> DocumentResponse:
        """Reset a failed/dead-lettered document and re-enqueue processing."""
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError("Document not found.")

        if doc.processing_state != DocumentProcessingState.FAILED:
            raise ValidationError("Only failed documents can be retried.")

        doc.processing_state = DocumentProcessingState.UPLOADED
        doc.retry_count = 0
        doc.dead_letter = False
        doc.last_error_message = None
        self._session.add(doc)
        await self._session.flush()

        # Re-enqueue
        process_document_task.delay(str(document_id), str(tenant_id))

        logger.info(
            "document_retry",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
        )

        chunk_count = await self._get_chunk_count(document_id, tenant_id)
        return self._to_response(doc, chunk_count=chunk_count)

    async def get_status(self, document_id: UUID, tenant_id: UUID) -> DocumentProcessingState:
        """Get the current processing state of a document."""
        result = await self._session.execute(
            select(Document.processing_state).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        state = result.scalar_one_or_none()
        if state is None:
            raise NotFoundError("Document not found.")
        return state

    async def _get_chunk_count(self, document_id: UUID, tenant_id: UUID) -> int:
        """Get the number of chunks for a document."""
        result = await self._session.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.tenant_id == tenant_id,
            )
        )
        return result.scalar() or 0

    @staticmethod
    def _to_response(doc: Document, chunk_count: int) -> DocumentResponse:
        """Convert a Document model to a DocumentResponse.

        Uses str() conversion for UUID fields to handle uuid_utils.UUID vs stdlib UUID.
        """
        return DocumentResponse(
            id=UUID(str(doc.id)),
            tenant_id=UUID(str(doc.tenant_id)),
            knowledge_base_id=UUID(str(doc.knowledge_base_id)),
            name=doc.name,
            document_uri=doc.document_uri,
            source_uri=doc.source_uri,
            mime_type=doc.mime_type,
            byte_size=doc.byte_size,
            hash=doc.hash,
            processing_state=doc.processing_state,
            version_number=doc.version_number,
            previous_version_id=(
                UUID(str(doc.previous_version_id)) if doc.previous_version_id else None
            ),
            metadata=doc.metadata_,
            chunk_count=chunk_count,
            retry_count=doc.retry_count,
            last_error_message=doc.last_error_message,
            dead_letter=doc.dead_letter,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
