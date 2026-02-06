"""Document processing pipeline orchestrator.

Runs the full pipeline: validate -> extract -> chunk -> contextualise -> embed -> index.
Updates document.processing_state at each step. On failure: increment retry_count,
set last_error_message. After 3 failures: dead_letter=True.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import DocumentProcessingState
from yourai.knowledge.chunking import chunk_document
from yourai.knowledge.contextualiser import contextualise_chunks
from yourai.knowledge.embeddings import create_embedder
from yourai.knowledge.extraction import extract_text
from yourai.knowledge.models import Document, DocumentChunk
from yourai.knowledge.storage import LocalFileStorage
from yourai.knowledge.validation import validate_upload
from yourai.knowledge.vector_store import VectorStore

logger = structlog.get_logger()

_MAX_RETRIES = 3


async def _update_state(
    session: AsyncSession,
    document: Document,
    state: DocumentProcessingState,
) -> None:
    """Update document processing state."""
    document.processing_state = state
    session.add(document)
    await session.flush()


async def _handle_failure(
    session: AsyncSession,
    document: Document,
    error_message: str,
    tenant_id: str,
) -> None:
    """Handle pipeline failure: increment retry count, set error, maybe dead-letter."""
    document.processing_state = DocumentProcessingState.FAILED
    document.retry_count += 1
    document.last_error_message = error_message
    if document.retry_count >= _MAX_RETRIES:
        document.dead_letter = True
        logger.error(
            "document_dead_lettered",
            tenant_id=tenant_id,
            document_id=str(document.id),
            retry_count=document.retry_count,
            error=error_message,
        )
    session.add(document)
    await session.flush()


async def process_document(
    session: AsyncSession,
    document_id: UUID,
    tenant_id: UUID,
) -> None:
    """Full document processing pipeline."""
    tid = str(tenant_id)
    did = str(document_id)
    log = logger.bind(tenant_id=tid, document_id=did)

    # Load document
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        log.error("document_not_found")
        return

    storage = LocalFileStorage()

    try:
        # Step 1: Validate
        log.info("pipeline_step", step="validating")
        await _update_state(session, document, DocumentProcessingState.VALIDATING)
        file_data = await storage.read(document.document_uri)
        validate_upload(file_data, document.name, tid)

        # Step 2: Extract text
        log.info("pipeline_step", step="extracting_text")
        await _update_state(session, document, DocumentProcessingState.EXTRACTING_TEXT)
        extraction = extract_text(file_data, document.mime_type or "", document.name)
        document.extracted_text = extraction.text
        document.text_extraction_strategy = extraction.strategy
        session.add(document)
        await session.flush()

        # Step 3: Chunk
        log.info("pipeline_step", step="chunking")
        await _update_state(session, document, DocumentProcessingState.CHUNKING)
        chunks = chunk_document(
            extraction.text,
            sections=extraction.sections if extraction.sections else None,
        )
        document.chunking_strategy = (
            "structure_aware"
            if extraction.sections and len(extraction.sections) > 1
            else "fixed_size"
        )

        # Create chunk records
        chunk_records: list[DocumentChunk] = []
        for chunk in chunks:
            chunk_record = DocumentChunk(
                tenant_id=tenant_id,
                document_id=document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                byte_range_start=chunk.byte_range_start,
                byte_range_end=chunk.byte_range_end,
                byte_range_size=(
                    (chunk.byte_range_end - chunk.byte_range_start)
                    if chunk.byte_range_start is not None and chunk.byte_range_end is not None
                    else None
                ),
            )
            chunk_records.append(chunk_record)
            session.add(chunk_record)
        await session.flush()

        # Step 4: Contextualise
        log.info("pipeline_step", step="contextualising")
        await _update_state(session, document, DocumentProcessingState.CONTEXTUALISING)
        prefixes = await contextualise_chunks(chunks, extraction.text, tid)
        for i, prefix in enumerate(prefixes):
            if i < len(chunk_records) and prefix:
                chunk_records[i].contextual_prefix = prefix
                session.add(chunk_records[i])
        await session.flush()

        # Step 5: Embed
        log.info("pipeline_step", step="embedding")
        await _update_state(session, document, DocumentProcessingState.EMBEDDING)
        embedder = create_embedder()
        texts_to_embed = []
        for i, chunk in enumerate(chunks):
            prefix = prefixes[i] if i < len(prefixes) and prefixes[i] else ""
            texts_to_embed.append(f"{prefix}\n{chunk.content}" if prefix else chunk.content)

        embeddings = await embedder.embed_documents(texts_to_embed)

        # Update chunk records with embedding metadata
        for _i, chunk_record in enumerate(chunk_records):
            chunk_record.embedding_model = embedder.model_name
            chunk_record.embedding_version = f"{embedder.model_name}:v1"
            session.add(chunk_record)
        await session.flush()

        # Step 6: Index in Qdrant
        log.info("pipeline_step", step="indexing")
        await _update_state(session, document, DocumentProcessingState.INDEXING)
        vector_store = VectorStore()
        await vector_store.ensure_collection(tenant_id)

        points: list[dict[str, object]] = []
        for i, chunk_record in enumerate(chunk_records):
            points.append(
                {
                    "id": str(chunk_record.id),
                    "vector": embeddings[i],
                    "payload": {
                        "document_id": str(document_id),
                        "chunk_index": chunk_record.chunk_index,
                        "content": chunk_record.content,
                        "contextual_prefix": chunk_record.contextual_prefix or "",
                        "knowledge_base_id": str(document.knowledge_base_id),
                    },
                }
            )
        await vector_store.upsert_chunks(tenant_id, points)

        # Done
        await _update_state(session, document, DocumentProcessingState.READY)
        log.info("pipeline_complete")

    except Exception as exc:
        log.error("pipeline_failed", error=str(exc), exc_info=True)
        await _handle_failure(session, document, str(exc), tid)
