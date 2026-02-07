"""Celery task wrappers for the document processing pipeline.

Each task creates an event loop to run the async pipeline functions.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from yourai.core.celery_app import celery_app

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


def _run_async(coro: Coroutine[Any, Any, None]) -> None:
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_session_and_run(
    step_fn: Callable[[AsyncSession, UUID, UUID], Coroutine[Any, Any, None]],
    document_id: str,
    tenant_id: str,
) -> None:
    """Create an async session and run a pipeline step function."""

    async def _run() -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from yourai.core.config import settings

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await step_fn(session, UUID(document_id), UUID(tenant_id))
            await session.commit()
        await engine.dispose()

    _run_async(_run())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.process_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def process_document_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task wrapper for the document processing pipeline."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("process_document_task_started")

    async def _run() -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from yourai.core.config import settings
        from yourai.knowledge.pipeline import process_document

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await process_document(session, UUID(document_id), UUID(tenant_id))
            await session.commit()
        await engine.dispose()

    try:
        _run_async(_run())
    except Exception as exc:
        log.error("process_document_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.delete_document_vectors",
    queue="knowledge_ingest",
)
def delete_document_vectors_task(document_id: str, tenant_id: str) -> None:
    """Celery task to remove all vectors for a document from Qdrant."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("delete_document_vectors_task_started")

    async def _run() -> None:
        from yourai.knowledge.vector_store import VectorStore

        store = VectorStore()
        await store.delete_by_document(UUID(tenant_id), UUID(document_id))

    _run_async(_run())
    log.info("delete_document_vectors_task_complete")


# ---------------------------------------------------------------------------
# Discrete pipeline step tasks
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.validate_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def validate_document_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the validation pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("validate_document_task_started")
    try:
        from yourai.knowledge.pipeline import validate_step

        _make_session_and_run(validate_step, document_id, tenant_id)
    except Exception as exc:
        log.error("validate_document_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.extract_text",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def extract_text_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the text extraction pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("extract_text_task_started")
    try:
        from yourai.knowledge.pipeline import extract_text_step

        _make_session_and_run(extract_text_step, document_id, tenant_id)
    except Exception as exc:
        log.error("extract_text_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.chunk_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def chunk_document_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the chunking pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("chunk_document_task_started")
    try:
        from yourai.knowledge.pipeline import chunk_step

        _make_session_and_run(chunk_step, document_id, tenant_id)
    except Exception as exc:
        log.error("chunk_document_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.contextualise_chunks",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def contextualise_chunks_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the contextualisation pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("contextualise_chunks_task_started")
    try:
        from yourai.knowledge.pipeline import contextualise_step

        _make_session_and_run(contextualise_step, document_id, tenant_id)
    except Exception as exc:
        log.error("contextualise_chunks_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.embed_chunks",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def embed_chunks_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the embedding pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("embed_chunks_task_started")
    try:
        from yourai.knowledge.pipeline import embed_step

        _make_session_and_run(embed_step, document_id, tenant_id)
    except Exception as exc:
        log.error("embed_chunks_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.index_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def index_document_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task for the Qdrant indexing pipeline step."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("index_document_task_started")
    try:
        from yourai.knowledge.pipeline import index_step

        _make_session_and_run(index_step, document_id, tenant_id)
    except Exception as exc:
        log.error("index_document_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.sync_knowledge_base",
    queue="knowledge_ingest",
)
def sync_knowledge_base_task(knowledge_base_id: str, tenant_id: str) -> None:
    """Celery task stub for syncing a knowledge base from its source."""
    log = logger.bind(tenant_id=tenant_id, knowledge_base_id=knowledge_base_id)
    log.info("sync_knowledge_base_task_started")
    # Stub — actual sync logic will be implemented when Lex/Parliament sources are connected
    log.info("sync_knowledge_base_task_complete", status="stub")
